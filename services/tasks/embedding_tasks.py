"""嵌入向量生成相关的Celery任务"""
import os
import logging
from typing import List, Dict, Any
import uuid

from celery import current_task
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from services.celery_app import celery_app
from core.config import settings
from models.database import DocumentChunk, Document
from services.embedding_service import EmbeddingService
from services.vector_service import VectorService
from services.document_service import DocumentService

logger = logging.getLogger(__name__)

# 创建数据库会话
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(bind=True, name="generate_embedding")
def generate_embedding_task(self, chunk_id: int):
    """为文档分块生成嵌入向量的异步任务"""
    import asyncio
    
    async def _async_generate_embedding():
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
                embedding = await embedding_service.generate_embedding(
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
                
                # 准备元数据，添加doc_id和user_id
                metadata = {
                    "chunk_id": chunk_id,
                    "document_id": chunk.document_id,
                    "doc_id": chunk.document_id,  # 添加doc_id作为元数据
                    "user_id": settings.default_user_id,  # 使用默认用户ID
                    "chunk_index": chunk.chunk_index,
                    "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    "embedding_model": chunk.embedding_model or settings.embedding_model
                }
                
                # 存储到Milvus
                success = await vector_service.insert_vector(
                    collection_name=settings.MILVUS_COLLECTION_NAME,
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
    
    # 运行异步函数
    return asyncio.run(_async_generate_embedding())

@celery_app.task(bind=True, name="process_and_embed_document")
def process_and_embed_document_task(self, file_path: str, filename: str, user_id: str = None):
    """处理文档并生成嵌入向量的完整任务"""
    import asyncio
    
    async def _async_process_document():
        db = SessionLocal()
        document_service = DocumentService()
        embedding_service = EmbeddingService()
        vector_service = VectorService()
        
        try:
            # 使用默认用户ID如果未提供
            if not user_id:
                user_id = settings.default_user_id
                
            # 更新任务状态
            self.update_state(
                state="PROCESSING",
                meta={"progress": 0, "status": "开始处理文档"}
            )
            
            # 步骤1: 解析文档内容
            self.update_state(
                state="PROCESSING",
                meta={"progress": 10, "status": "解析文档内容"}
            )
            
            try:
                content = document_service.extract_text_from_file(file_path)
                if not content or not content.strip():
                    raise Exception("文档内容为空或无法解析")
            except Exception as e:
                logger.error(f"文档解析失败: {e}")
                raise Exception(f"文档解析失败: {str(e)}")
            
            # 步骤2: 创建文档记录
            self.update_state(
                state="PROCESSING",
                meta={"progress": 20, "status": "创建文档记录"}
            )
            
            document = Document(
                original_filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                content=content,
                status="processing",
                user_id=user_id
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # 步骤3: 文档分块
            self.update_state(
                state="PROCESSING",
                meta={"progress": 30, "status": "文档分块处理"}
            )
            
            # 根据配置的chunk_size进行分块
            chunk_size = settings.chunk_size
            chunk_overlap = 50  # 重叠字符数
            
            chunks = []
            content_length = len(content)
            
            for i in range(0, content_length, chunk_size - chunk_overlap):
                chunk_content = content[i:i + chunk_size]
                if chunk_content.strip():  # 只保存非空分块
                    chunks.append(chunk_content)
            
            if not chunks:
                raise Exception("文档分块后无有效内容")
            
            # 步骤4: 创建分块记录并生成嵌入
            total_chunks = len(chunks)
            embedded_chunks = 0
            
            for chunk_index, chunk_content in enumerate(chunks):
                try:
                    # 创建分块记录
                    chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=chunk_index,
                        content=chunk_content,
                        embedding_model=settings.embedding_model
                    )
                    db.add(chunk)
                    db.commit()
                    db.refresh(chunk)
                    
                    # 生成嵌入向量
                    embedding = await embedding_service.generate_embedding(
                        text=chunk_content,
                        model=settings.embedding_model
                    )
                    
                    # 生成唯一的向量ID
                    vector_id = f"chunk_{chunk.id}_{uuid.uuid4().hex[:8]}"
                    
                    # 准备元数据
                    metadata = {
                        "chunk_id": chunk.id,
                        "document_id": document.id,
                        "doc_id": document.id,  # 添加doc_id作为元数据
                        "user_id": user_id,
                        "chunk_index": chunk_index,
                        "content_preview": chunk_content[:200] + "..." if len(chunk_content) > 200 else chunk_content,
                        "embedding_model": settings.embedding_model,
                        "filename": filename
                    }
                    
                    # 存储到Milvus
                    success = await vector_service.insert_vector(
                        collection_name=settings.MILVUS_COLLECTION_NAME,
                        vector_id=vector_id,
                        embedding=embedding,
                        metadata=metadata
                    )
                    
                    if success:
                        chunk.vector_id = vector_id
                        db.commit()
                        embedded_chunks += 1
                        
                        # 更新进度
                        progress = 40 + int((embedded_chunks / total_chunks) * 50)
                        self.update_state(
                            state="PROCESSING",
                            meta={
                                "progress": progress, 
                                "status": f"已处理 {embedded_chunks}/{total_chunks} 个分块"
                            }
                        )
                    else:
                        logger.warning(f"分块 {chunk.id} 向量存储失败")
                        
                except Exception as e:
                    logger.error(f"处理分块 {chunk_index} 失败: {e}")
                    continue
            
            # 步骤5: 更新文档状态
            self.update_state(
                state="PROCESSING",
                meta={"progress": 95, "status": "更新文档状态"}
            )
            
            if embedded_chunks > 0:
                document.status = "completed"
                document.chunk_count = embedded_chunks
            else:
                document.status = "failed"
                raise Exception("所有分块处理失败")
            
            db.commit()
            
            # 完成
            self.update_state(
                state="SUCCESS",
                meta={"progress": 100, "status": "文档处理完成"}
            )
            
            logger.info(f"文档 {filename} 处理完成，共生成 {embedded_chunks} 个嵌入向量")
            
            return {
                "document_id": document.id,
                "filename": filename,
                "total_chunks": total_chunks,
                "embedded_chunks": embedded_chunks,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"文档处理失败: {e}", exc_info=True)
            
            # 更新文档状态为失败
            if 'document' in locals():
                document.status = "failed"
                db.commit()
            
            # 更新任务状态
            self.update_state(
                state="FAILURE",
                meta={"error": str(e), "filename": filename}
            )
            
            raise
        
        finally:
            db.close()
    
    # 运行异步函数
    return asyncio.run(_async_process_document())

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