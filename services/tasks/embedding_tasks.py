"""嵌入向量生成相关的Celery任务"""
import logging
from typing import List, Dict, Any
import uuid

from celery import current_task
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from services.celery_app import celery_app
from core.config import settings
from models.database import DocumentChunk
from services.embedding_service import EmbeddingService
from services.vector_service import VectorService

logger = logging.getLogger(__name__)

# 创建数据库会话
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(bind=True, name="generate_embedding")
def generate_embedding_task(self, chunk_id: int):
    """为文档分块生成嵌入向量的异步任务"""
    db = SessionLocal()
    embedding_service = EmbeddingService()
    vector_service = VectorService()
    
    try:
        # 更新任务状态
        self.update_state(
            state="PROCESSING",
            meta={"progress": 0, "status": "开始生成嵌入向量"}
        )
        
        # 获取文档分块
        chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
        if not chunk:
            raise Exception(f"文档分块不存在: {chunk_id}")
        
        logger.info(f"开始为分块 {chunk_id} 生成嵌入向量")
        
        # 步骤1: 生成嵌入向量
        self.update_state(
            state="PROCESSING",
            meta={"progress": 30, "status": "调用嵌入模型"}
        )
        
        try:
            embedding = embedding_service.generate_embedding_sync(
                text=chunk.content,
                model=chunk.embedding_model or settings.embedding_model
            )
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            raise Exception(f"嵌入向量生成失败: {str(e)}")
        
        # 步骤2: 存储到向量数据库
        self.update_state(
            state="PROCESSING",
            meta={"progress": 70, "status": "存储向量数据"}
        )
        
        try:
            # 生成唯一的向量ID
            vector_id = f"chunk_{chunk_id}_{uuid.uuid4().hex[:8]}"
            
            # 准备元数据
            metadata = {
                "chunk_id": chunk_id,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "embedding_model": chunk.embedding_model or settings.embedding_model
            }
            
            # 存储到Milvus
            success = vector_service.insert_vector_sync(
                collection_name=settings.milvus_collection_name or "sparklinkai_knowledge",
                vector_id=vector_id,
                embedding=embedding,
                metadata=metadata
            )
            
            if not success:
                raise Exception("向量存储失败")
            
        except Exception as e:
            logger.error(f"向量存储失败: {e}")
            raise Exception(f"向量存储失败: {str(e)}")
        
        # 步骤3: 更新数据库记录
        self.update_state(
            state="PROCESSING",
            meta={"progress": 90, "status": "更新数据库记录"}
        )
        
        chunk.vector_id = vector_id
        db.commit()
        
        # 完成
        self.update_state(
            state="SUCCESS",
            meta={"progress": 100, "status": "嵌入向量生成完成"}
        )
        
        logger.info(f"分块 {chunk_id} 嵌入向量生成完成，向量ID: {vector_id}")
        
        return {
            "chunk_id": chunk_id,
            "vector_id": vector_id,
            "embedding_dimension": len(embedding),
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"嵌入向量生成失败: {e}", exc_info=True)
        
        # 更新任务状态
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "chunk_id": chunk_id}
        )
        
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="batch_generate_embeddings")
def batch_generate_embeddings_task(self, chunk_ids: List[int]):
    """批量生成嵌入向量的异步任务"""
    try:
        total_chunks = len(chunk_ids)
        processed_chunks = 0
        failed_chunks = []
        
        for i, chunk_id in enumerate(chunk_ids):
            try:
                # 更新批量处理进度
                progress = int((i / total_chunks) * 100)
                self.update_state(
                    state="PROCESSING",
                    meta={
                        "progress": progress,
                        "status": f"处理分块 {i+1}/{total_chunks}",
                        "current_chunk_id": chunk_id
                    }
                )
                
                # 调用单个嵌入生成任务
                result = generate_embedding_task.apply(args=[chunk_id])
                if result.successful():
                    processed_chunks += 1
                else:
                    failed_chunks.append({"chunk_id": chunk_id, "error": str(result.result)})
                    
            except Exception as e:
                logger.error(f"批量生成嵌入向量，分块 {chunk_id} 失败: {e}")
                failed_chunks.append({"chunk_id": chunk_id, "error": str(e)})
        
        # 完成批量处理
        self.update_state(
            state="SUCCESS",
            meta={
                "progress": 100,
                "status": "批量嵌入向量生成完成",
                "total_chunks": total_chunks,
                "processed_chunks": processed_chunks,
                "failed_chunks": len(failed_chunks),
                "failed_details": failed_chunks
            }
        )
        
        return {
            "total_chunks": total_chunks,
            "processed_chunks": processed_chunks,
            "failed_chunks": len(failed_chunks),
            "failed_details": failed_chunks
        }
        
    except Exception as e:
        logger.error(f"批量生成嵌入向量失败: {e}", exc_info=True)
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise

@celery_app.task(bind=True, name="rebuild_embeddings")
def rebuild_embeddings_task(self, document_id: int = None, embedding_model: str = None):
    """重建嵌入向量的异步任务"""
    db = SessionLocal()
    
    try:
        # 查询需要重建的分块
        query = db.query(DocumentChunk)
        
        if document_id:
            query = query.filter(DocumentChunk.document_id == document_id)
        
        chunks = query.all()
        
        if not chunks:
            return {"message": "没有找到需要重建的分块", "status": "completed"}
        
        # 更新嵌入模型（如果提供）
        if embedding_model:
            for chunk in chunks:
                chunk.embedding_model = embedding_model
                chunk.vector_id = None  # 清空旧的向量ID
            db.commit()
        
        # 批量生成新的嵌入向量
        chunk_ids = [chunk.id for chunk in chunks]
        
        self.update_state(
            state="PROCESSING",
            meta={
                "progress": 0,
                "status": f"开始重建 {len(chunk_ids)} 个分块的嵌入向量",
                "total_chunks": len(chunk_ids)
            }
        )
        
        # 调用批量生成任务
        result = batch_generate_embeddings_task.apply(args=[chunk_ids])
        
        return {
            "document_id": document_id,
            "embedding_model": embedding_model,
            "total_chunks": len(chunk_ids),
            "rebuild_result": result.result,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"重建嵌入向量失败: {e}", exc_info=True)
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="update_embedding_model")
def update_embedding_model_task(self, old_model: str, new_model: str):
    """更新嵌入模型的异步任务"""
    db = SessionLocal()
    
    try:
        # 查找使用旧模型的分块
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.embedding_model == old_model
        ).all()
        
        if not chunks:
            return {
                "message": f"没有找到使用模型 {old_model} 的分块",
                "status": "completed"
            }
        
        logger.info(f"找到 {len(chunks)} 个使用旧模型 {old_model} 的分块，将更新为 {new_model}")
        
        # 更新模型并清空向量ID
        for chunk in chunks:
            chunk.embedding_model = new_model
            chunk.vector_id = None
        
        db.commit()
        
        # 重新生成嵌入向量
        chunk_ids = [chunk.id for chunk in chunks]
        result = batch_generate_embeddings_task.apply(args=[chunk_ids])
        
        return {
            "old_model": old_model,
            "new_model": new_model,
            "updated_chunks": len(chunk_ids),
            "regeneration_result": result.result,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"更新嵌入模型失败: {e}", exc_info=True)
        db.rollback()
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise
    
    finally:
        db.close()