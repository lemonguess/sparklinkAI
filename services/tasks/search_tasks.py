"""搜索相关的Celery任务"""
import logging
from typing import List, Dict, Any

from celery import current_task
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from services.celery_app import celery_app
from core.config import settings
from models.database import SearchLog
from services.search_service import SearchService
from services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

# 创建数据库会话
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(bind=True, name="web_search")
def web_search_task(self, query: str, max_results: int = 5):
    """联网搜索的异步任务"""
    search_service = SearchService()
    
    try:
        # 更新任务状态
        self.update_state(
            state="PROCESSING",
            meta={"progress": 0, "status": "开始联网搜索"}
        )
        
        logger.info(f"开始联网搜索: {query}")
        
        # 执行搜索
        self.update_state(
            state="PROCESSING",
            meta={"progress": 50, "status": "调用搜索API"}
        )
        
        try:
            results = search_service.web_search_sync(
                query=query,
                max_results=max_results
            )
        except Exception as e:
            logger.error(f"联网搜索失败: {e}")
            raise Exception(f"搜索API调用失败: {str(e)}")
        
        # 完成搜索
        self.update_state(
            state="SUCCESS",
            meta={"progress": 100, "status": "搜索完成"}
        )
        
        logger.info(f"联网搜索完成: {query}, 找到 {len(results)} 个结果")
        
        return {
            "query": query,
            "results": results,
            "total_count": len(results),
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"联网搜索任务失败: {e}", exc_info=True)
        
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "query": query}
        )
        
        raise

@celery_app.task(bind=True, name="knowledge_search")
def knowledge_search_task(self, query: str, top_k: int = 10, similarity_threshold: float = 0.7):
    """知识库搜索的异步任务"""
    knowledge_service = KnowledgeService()
    
    try:
        # 更新任务状态
        self.update_state(
            state="PROCESSING",
            meta={"progress": 0, "status": "开始知识库搜索"}
        )
        
        logger.info(f"开始知识库搜索: {query}")
        
        # 执行搜索
        self.update_state(
            state="PROCESSING",
            meta={"progress": 50, "status": "查询向量数据库"}
        )
        
        try:
            results = knowledge_service.search_sync(
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            raise Exception(f"向量搜索失败: {str(e)}")
        
        # 完成搜索
        self.update_state(
            state="SUCCESS",
            meta={"progress": 100, "status": "知识库搜索完成"}
        )
        
        logger.info(f"知识库搜索完成: {query}, 找到 {len(results)} 个结果")
        
        return {
            "query": query,
            "results": results,
            "total_count": len(results),
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"知识库搜索任务失败: {e}", exc_info=True)
        
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "query": query}
        )
        
        raise

@celery_app.task(bind=True, name="hybrid_search")
def hybrid_search_task(
    self, 
    query: str, 
    use_knowledge_base: bool = True,
    use_web_search: bool = True,
    knowledge_threshold: float = 0.8
):
    """混合搜索的异步任务（智能判断策略）"""
    db = SessionLocal()
    
    try:
        # 更新任务状态
        self.update_state(
            state="PROCESSING",
            meta={"progress": 0, "status": "开始混合搜索"}
        )
        
        logger.info(f"开始混合搜索: {query}")
        
        knowledge_results = []
        web_results = []
        search_strategy = "none"
        
        # 步骤1: 知识库搜索
        if use_knowledge_base:
            self.update_state(
                state="PROCESSING",
                meta={"progress": 25, "status": "搜索知识库"}
            )
            
            try:
                kb_task_result = knowledge_search_task.apply(args=[query, 10, 0.7])
                if kb_task_result.successful():
                    knowledge_results = kb_task_result.result.get("results", [])
                    search_strategy = "knowledge_base"
            except Exception as e:
                logger.warning(f"知识库搜索失败: {e}")
        
        # 步骤2: 智能判断是否需要联网搜索
        should_web_search = False
        
        if use_web_search:
            if not knowledge_results:
                # 没有知识库结果，进行联网搜索
                should_web_search = True
                logger.info("知识库无结果，启用联网搜索")
            else:
                # 检查知识库结果的置信度
                max_score = max([r.get('score', 0) for r in knowledge_results])
                if max_score < knowledge_threshold:
                    should_web_search = True
                    logger.info(f"知识库最高置信度 {max_score} 低于阈值 {knowledge_threshold}，启用联网搜索")
        
        # 步骤3: 联网搜索（如果需要）
        if should_web_search:
            self.update_state(
                state="PROCESSING",
                meta={"progress": 60, "status": "联网搜索"}
            )
            
            try:
                web_task_result = web_search_task.apply(args=[query, 5])
                if web_task_result.successful():
                    web_results = web_task_result.result.get("results", [])
                    search_strategy = "hybrid" if knowledge_results else "web_search"
            except Exception as e:
                logger.warning(f"联网搜索失败: {e}")
        
        # 步骤4: 记录搜索日志
        self.update_state(
            state="PROCESSING",
            meta={"progress": 90, "status": "记录搜索日志"}
        )
        
        try:
            search_log = SearchLog(
                query=query,
                search_type=search_strategy,
                knowledge_results_count=len(knowledge_results),
                web_results_count=len(web_results),
                total_results_count=len(knowledge_results) + len(web_results),
                knowledge_confidence=max([r.get('score', 0) for r in knowledge_results]) if knowledge_results else 0.0
            )
            db.add(search_log)
            db.commit()
        except Exception as e:
            logger.warning(f"记录搜索日志失败: {e}")
        
        # 完成搜索
        self.update_state(
            state="SUCCESS",
            meta={"progress": 100, "status": "混合搜索完成"}
        )
        
        total_results = len(knowledge_results) + len(web_results)
        logger.info(f"混合搜索完成: {query}, 策略: {search_strategy}, 总结果: {total_results}")
        
        return {
            "query": query,
            "search_strategy": search_strategy,
            "knowledge_results": knowledge_results,
            "web_results": web_results,
            "total_results": total_results,
            "knowledge_confidence": max([r.get('score', 0) for r in knowledge_results]) if knowledge_results else 0.0,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"混合搜索任务失败: {e}", exc_info=True)
        
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "query": query}
        )
        
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="batch_search")
def batch_search_task(self, queries: List[str], search_type: str = "hybrid"):
    """批量搜索的异步任务"""
    try:
        total_queries = len(queries)
        results = []
        failed_queries = []
        
        for i, query in enumerate(queries):
            try:
                # 更新批量搜索进度
                progress = int((i / total_queries) * 100)
                self.update_state(
                    state="PROCESSING",
                    meta={
                        "progress": progress,
                        "status": f"搜索查询 {i+1}/{total_queries}",
                        "current_query": query
                    }
                )
                
                # 根据搜索类型调用相应任务
                if search_type == "knowledge_base":
                    result = knowledge_search_task.apply(args=[query])
                elif search_type == "web_search":
                    result = web_search_task.apply(args=[query])
                else:  # hybrid
                    result = hybrid_search_task.apply(args=[query])
                
                if result.successful():
                    results.append({
                        "query": query,
                        "result": result.result
                    })
                else:
                    failed_queries.append({
                        "query": query,
                        "error": str(result.result)
                    })
                    
            except Exception as e:
                logger.error(f"批量搜索，查询 '{query}' 失败: {e}")
                failed_queries.append({
                    "query": query,
                    "error": str(e)
                })
        
        # 完成批量搜索
        self.update_state(
            state="SUCCESS",
            meta={
                "progress": 100,
                "status": "批量搜索完成",
                "total_queries": total_queries,
                "successful_queries": len(results),
                "failed_queries": len(failed_queries)
            }
        )
        
        return {
            "total_queries": total_queries,
            "successful_queries": len(results),
            "failed_queries": len(failed_queries),
            "results": results,
            "failed_details": failed_queries,
            "search_type": search_type
        }
        
    except Exception as e:
        logger.error(f"批量搜索失败: {e}", exc_info=True)
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise