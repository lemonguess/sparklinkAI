"""文档处理相关的Celery任务"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

from celery import current_task
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from services.celery_app import celery_app
from core.config import settings
from models.database import Document, DocumentChunk
from services.document_service import DocumentService
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# 创建数据库会话
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(bind=True, name="process_document")
def process_document_task(self, document_id: int):
    """处理文档的异步任务"""
    db = SessionLocal()
    document_service = DocumentService()
    
    try:
        # 更新任务状态
        self.update_state(
            state="PROCESSING",
            meta={"progress": 0, "status": "开始处理文档"}
        )
        
        # 获取文档记录
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise Exception(f"文档不存在: {document_id}")
        
        # 更新文档状态
        document.status = "processing"
        db.commit()
        
        logger.info(f"开始处理文档: {document.original_filename}")
        
        # 步骤1: 解析文档内容
        self.update_state(
            state="PROCESSING",
            meta={"progress": 20, "status": "解析文档内容"}
        )
        
        try:
            content = document_service.extract_content(document.file_path, document.file_type)
        except Exception as e:
            logger.error(f"文档内容解析失败: {e}")
            document.status = "failed"
            document.error_message = f"内容解析失败: {str(e)}"
            db.commit()
            raise
        
        # 步骤2: 分块处理
        self.update_state(
            state="PROCESSING",
            meta={"progress": 40, "status": "分块处理"}
        )
        
        try:
            chunks = document_service.split_content(
                content=content,
                chunk_size=settings.chunk_size,
                chunk_overlap=50
            )
        except Exception as e:
            logger.error(f"文档分块失败: {e}")
            document.status = "failed"
            document.error_message = f"分块处理失败: {str(e)}"
            db.commit()
            raise
        
        # 步骤3: 保存分块到数据库
        self.update_state(
            state="PROCESSING",
            meta={"progress": 60, "status": "保存分块数据"}
        )
        
        chunk_records = []
        for i, chunk_content in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk_content,
                embedding_model=settings.embedding_model
            )
            chunk_records.append(chunk)
        
        db.add_all(chunk_records)
        db.commit()
        
        # 步骤4: 生成嵌入向量（异步调用）
        self.update_state(
            state="PROCESSING",
            meta={"progress": 80, "status": "生成嵌入向量"}
        )
        
        # 为每个分块生成嵌入向量
        chunk_ids = [chunk.id for chunk in chunk_records]
        for chunk_id in chunk_ids:
            # 异步调用嵌入任务
            from services.tasks.embedding_tasks import generate_embedding_task
            generate_embedding_task.delay(chunk_id)
        
        # 步骤5: 完成处理
        self.update_state(
            state="PROCESSING",
            meta={"progress": 100, "status": "处理完成"}
        )
        
        document.status = "completed"
        document.processed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"文档处理完成: {document.original_filename}, 生成 {len(chunks)} 个分块")
        
        return {
            "document_id": document_id,
            "status": "completed",
            "chunks_count": len(chunks),
            "processed_at": document.processed_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"文档处理失败: {e}", exc_info=True)
        
        # 更新文档状态为失败
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "failed"
            document.error_message = str(e)
            db.commit()
        
        # 更新任务状态
        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "document_id": document_id}
        )
        
        raise
    
    finally:
        db.close()

@celery_app.task(bind=True, name="batch_process_documents")
def batch_process_documents_task(self, document_ids: List[int]):
    """批量处理文档的异步任务"""
    try:
        total_docs = len(document_ids)
        processed_docs = 0
        failed_docs = []
        
        for i, doc_id in enumerate(document_ids):
            try:
                # 更新批量处理进度
                progress = int((i / total_docs) * 100)
                self.update_state(
                    state="PROCESSING",
                    meta={
                        "progress": progress,
                        "status": f"处理文档 {i+1}/{total_docs}",
                        "current_document_id": doc_id
                    }
                )
                
                # 调用单个文档处理任务
                result = process_document_task.apply(args=[doc_id])
                if result.successful():
                    processed_docs += 1
                else:
                    failed_docs.append({"document_id": doc_id, "error": str(result.result)})
                    
            except Exception as e:
                logger.error(f"批量处理文档 {doc_id} 失败: {e}")
                failed_docs.append({"document_id": doc_id, "error": str(e)})
        
        # 完成批量处理
        self.update_state(
            state="SUCCESS",
            meta={
                "progress": 100,
                "status": "批量处理完成",
                "total_documents": total_docs,
                "processed_documents": processed_docs,
                "failed_documents": len(failed_docs),
                "failed_details": failed_docs
            }
        )
        
        return {
            "total_documents": total_docs,
            "processed_documents": processed_docs,
            "failed_documents": len(failed_docs),
            "failed_details": failed_docs
        }
        
    except Exception as e:
        logger.error(f"批量处理文档失败: {e}", exc_info=True)
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise

@celery_app.task(bind=True, name="cleanup_failed_documents")
def cleanup_failed_documents_task(self):
    """清理失败的文档记录"""
    db = SessionLocal()
    
    try:
        # 查找失败的文档
        failed_docs = db.query(Document).filter(Document.status == "failed").all()
        
        cleaned_count = 0
        for doc in failed_docs:
            try:
                # 删除文件
                if os.path.exists(doc.file_path):
                    os.remove(doc.file_path)
                
                # 删除相关的分块记录
                db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
                
                # 删除文档记录
                db.delete(doc)
                
                cleaned_count += 1
                
            except Exception as e:
                logger.error(f"清理失败文档 {doc.id} 时出错: {e}")
        
        db.commit()
        
        logger.info(f"清理了 {cleaned_count} 个失败的文档记录")
        
        return {
            "cleaned_documents": cleaned_count,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"清理失败文档任务失败: {e}", exc_info=True)
        db.rollback()
        raise
    
    finally:
        db.close()