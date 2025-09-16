#!/usr/bin/env python3
"""知识库系统测试脚本"""

import asyncio
import logging
import time
import uuid

from services.vector_service import VectorService
from services.embedding_service import EmbeddingService
from services.knowledge_service import KnowledgeService
from services.rerank_service import RerankService
user_id = 'admin123456789abcdef0123456789abcdef'
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KnowledgeSystemTester:
    """知识库系统测试器"""
    
    def __init__(self):
        self.vector_service = VectorService()
        self.embedding_service = EmbeddingService()
        self.knowledge_service = KnowledgeService()
        self.rerank_service = RerankService()
        self.test_collection = "test_knowledge_collection"
        
    async def test_connection(self):
        """测试连接"""
        logger.info("=== 测试连接 ===")
        
        # 测试向量数据库连接
        vector_connected = await self.vector_service.connect()
        logger.info(f"向量数据库连接: {'成功' if vector_connected else '失败'}")
        
        # 测试嵌入服务
        embedding_available = self.embedding_service.is_available()
        logger.info(f"嵌入服务可用: {'是' if embedding_available else '否'}")
        
        # 测试重排序服务
        rerank_available = self.rerank_service.is_available()
        logger.info(f"重排序服务可用: {'是' if rerank_available else '否'}")
        
        return vector_connected and embedding_available
    
    async def test_collection_operations(self):
        """测试集合操作"""
        logger.info("=== 测试集合操作 ===")
        
        # 删除测试集合（如果存在）
        await self.vector_service.drop_collection(self.test_collection)
        
        # 创建测试集合
        success = await self.vector_service.create_collection(
            collection_name=self.test_collection,
            dimension=1024,
            description="测试知识库集合"
        )
        logger.info(f"创建集合: {'成功' if success else '失败'}")
        
        # 获取集合信息
        if success:
            info = await self.vector_service.get_collection_info(self.test_collection)
            logger.info(f"集合信息: {info}")
        
        return success
    
    async def test_embedding_and_insertion(self):
        """测试嵌入和插入"""
        logger.info("=== 测试嵌入和插入 ===")
        
        # 测试文档
        test_documents = [
            {
                "id": str(uuid.uuid4()),
                "title": "Python编程基础",
                "source_path": "/docs/python_basics.md",
                "chunk_id": 1,
                "content": "Python是一种高级编程语言，具有简洁的语法和强大的功能。它广泛应用于Web开发、数据科学、人工智能等领域。",
                "type_name": "document",
                "auther_name": "张三",
                "user_id": "1"
            },
            {
                "id": str(uuid.uuid4()),
                "title": "机器学习入门",
                "source_path": "/docs/ml_intro.md",
                "chunk_id": 2,
                "content": "机器学习是人工智能的一个分支，通过算法让计算机从数据中学习模式。常见的机器学习算法包括线性回归、决策树、神经网络等。",
                "type_name": "document",
                "auther_name": "李四",
                "user_id": "2"
            },
            {
                "id": str(uuid.uuid4()),
                "title": "深度学习讨论",
                "source_path": "/forum/deep_learning_discussion",
                "chunk_id": 3,
                "content": "深度学习是机器学习的一个子领域，使用多层神经网络来学习数据的复杂模式。在图像识别、自然语言处理等任务中表现出色。",
                "type_name": "forum_post",
                "auther_name": "王五",
                "user_id": "3"
            }
        ]
        
        success_count = 0
        
        for doc in test_documents:
            try:
                # 生成标题向量
                title_embedding = await self.embedding_service.generate_embedding(doc["title"])
                
                # 插入向量
                success = await self.vector_service.insert_vector(
                    collection_name=self.test_collection,
                    vector_id=doc["id"],
                    doc_id=f"doc_{test_documents.index(doc)}",
                    title=doc["title"],
                    source_path=doc["source_path"],
                    chunk_id=0,
                    create_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    update_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    content=doc["content"],
                    content_vector=title_embedding,
                    type_name=doc["type_name"],
                    auther_name=doc["auther_name"],
                    user_id=doc["user_id"]
                )
                
                if success:
                    success_count += 1
                    logger.info(f"插入文档成功: {doc['title']}")
                else:
                    logger.error(f"插入文档失败: {doc['title']}")
                    
            except Exception as e:
                logger.error(f"处理文档失败 {doc['title']}: {e}")
        
        logger.info(f"成功插入 {success_count}/{len(test_documents)} 个文档")
        return success_count > 0
    
    async def test_search_and_rerank(self):
        """测试搜索和重排序"""
        logger.info("=== 测试搜索和重排序 ===")
        
        test_queries = [
            "Python编程",
            "机器学习算法",
            "深度学习神经网络",
            "人工智能应用"
        ]
        
        for query in test_queries:
            logger.info(f"\n查询: '{query}'")
            
            # 测试不使用重排序的搜索
            start_time = time.time()
            results_no_rerank = await self.knowledge_service.search(
                query=query,
                top_k=5,
                collection_name=self.test_collection,
                similarity_threshold=0.3,
                use_rerank=False
            )
            no_rerank_time = time.time() - start_time
            
            logger.info(f"不使用重排序 - 结果数: {len(results_no_rerank)}, 耗时: {no_rerank_time:.3f}s")
            for i, result in enumerate(results_no_rerank[:3]):
                logger.info(f"  {i+1}. {result.get('title', 'N/A')} (相似度: {result.get('score', 0):.3f})")
            
            # 测试使用重排序的搜索
            start_time = time.time()
            results_with_rerank = await self.knowledge_service.search(
                query=query,
                top_k=5,
                collection_name=self.test_collection,
                similarity_threshold=0.3,
                use_rerank=True
            )
            rerank_time = time.time() - start_time
            
            logger.info(f"使用重排序 - 结果数: {len(results_with_rerank)}, 耗时: {rerank_time:.3f}s")
            for i, result in enumerate(results_with_rerank[:3]):
                rerank_score = result.get('rerank_score', 'N/A')
                logger.info(f"  {i+1}. {result.get('title', 'N/A')} (重排序分数: {rerank_score})")
    
    async def test_type_filtering(self):
        """测试类型过滤"""
        logger.info("=== 测试类型过滤 ===")
        
        # 这里可以扩展向量搜索以支持类型过滤
        # 目前先展示所有结果的类型分布
        results = await self.knowledge_service.search(
            query="学习",
            top_k=10,
            collection_name=self.test_collection
        )
        
        type_counts = {}
        for result in results:
            type_name = result.get('type_name', 'unknown')
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        logger.info(f"搜索结果类型分布: {type_counts}")
    
    async def cleanup(self):
        """清理测试数据"""
        logger.info("=== 清理测试数据 ===")
        success = await self.vector_service.drop_collection(self.test_collection)
        logger.info(f"删除测试集合: {'成功' if success else '失败'}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始知识库系统测试")
        
        try:
            # 测试连接
            if not await self.test_connection():
                logger.error("连接测试失败，终止测试")
                return
            
            # 测试集合操作
            if not await self.test_collection_operations():
                logger.error("集合操作测试失败，终止测试")
                return
            
            # 测试嵌入和插入
            if not await self.test_embedding_and_insertion():
                logger.error("嵌入和插入测试失败，终止测试")
                return
            
            # 等待数据索引完成
            logger.info("等待数据索引完成...")
            await asyncio.sleep(2)
            
            # 测试搜索和重排序
            await self.test_search_and_rerank()
            
            # 测试类型过滤
            await self.test_type_filtering()
            
            logger.info("所有测试完成")
            
        except Exception as e:
            logger.error(f"测试过程中出现错误: {e}")
        
        finally:
            # 清理测试数据
            await self.cleanup()

async def main():
    """主函数"""
    tester = KnowledgeSystemTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())