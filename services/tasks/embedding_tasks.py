"""嵌入任务模块"""
import asyncio
from contextlib import contextmanager
from typing import Dict, Any, List
import os
import json
import asyncio
import requests
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
import mimetypes
import logging
from models.enums import DocType
from core.config import settings
from core.database import get_db
from models.database import DocumentEmbeddingTask, TaskStatus
from models.schemas import DocumentEmbeddingTaskRequest
from services.document_service import DocumentService
from services.embedding_service import EmbeddingService
from services.vector_service import VectorService
from services.celery_app import celery_app

# 配置日志
logger = logging.getLogger(__name__)

# 初始化服务
document_service = DocumentService()
embedding_service = EmbeddingService()
vector_service = VectorService()


@contextmanager
def get_db_session():
    """数据库会话上下文管理器"""
    db = next(get_db())
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"数据库操作失败，已回滚: {e}")
        raise
    finally:
        db.close()


def update_task_status(doc_id: str, **kwargs):
    """更新任务状态的辅助函数"""
    if not doc_id:
        raise ValueError("doc_id不能为空")
    
    try:
        with get_db_session() as db:
            task_record = db.query(DocumentEmbeddingTask).filter(
                DocumentEmbeddingTask.doc_id == doc_id
            ).first()
            if task_record:
                for key, value in kwargs.items():
                    if hasattr(task_record, key):
                        setattr(task_record, key, value)
                db.commit()
                logger.debug(f"任务状态更新成功: {kwargs}")
    except Exception as e:
        logger.error(f"更新任务状态失败: {e}")


@celery_app.task(bind=True)
def process_and_embed_document_task(self, request_data: dict) -> Dict[str, Any]:
    """
    处理文档并生成嵌入向量
    
    Args:
        request_data: 文档嵌入任务请求数据字典
    
    Returns:
        处理结果
    """
    # 将字典转换为DocumentEmbeddingTaskRequest对象
    request = DocumentEmbeddingTaskRequest(**request_data)
    try:
        logger.info(f"开始处理文档: {request.file_path}, 类型: {request.doc_type}")
        # 更新任务状态为处理中
        update_task_status(
            request.doc_id,
            status=TaskStatus.PROCESSING,
            started_at=datetime.now(timezone(timedelta(hours=8)))
        )
        if request.doc_type == DocType.POST:
            # 帖子类型的文档，直接使用内容
            actual_file_path = None
            doc_content = request.doc_content
        else:
            # 判断是URL还是本地文件路径
            is_url = False
            actual_file_path = request.file_path
            temp_file_path = None
            parsed_url = urlparse(request.file_path)
            if parsed_url.scheme in ('http', 'https'):
                is_url = True
                logger.info(f"检测到URL，开始下载: {request.file_path}")
                # 下载文件到临时目录
                response = requests.get(request.file_path, timeout=30)
                response.raise_for_status()
                # 从URL或Content-Disposition头获取文件名
                _, ext = os.path.splitext(request.file_path)
                filename = request.doc_id + ext
                if not filename or '.' not in filename:
                    raise ValueError(f"无法从URL提取文件名: {request.file_path}")
                # 保存到上传目录
                upload_dir = settings.upload_dir
                os.makedirs(upload_dir, exist_ok=True)
                temp_file_path = os.path.join(upload_dir, filename)
                with open(temp_file_path, 'wb') as f:
                    f.write(response.content)
                actual_file_path = temp_file_path
                logger.info(f"文件下载完成: {actual_file_path}")
                file_type, _ = mimetypes.guess_type(actual_file_path)
                if not file_type:
                    file_type = "text/plain"  # 默认类型
                doc_content = document_service.extract_text_from_file(actual_file_path, file_type)
                if not doc_content or not doc_content.strip():
                    error_msg = f"文件内容为空: {actual_file_path}"
                    raise ValueError(error_msg)
            else:
                # 本地文件处理
                file_type, _ = mimetypes.guess_type(actual_file_path)
                if not file_type:
                    file_type = "text/plain"
                doc_content = document_service.extract_text_from_file(actual_file_path, file_type)
                if not doc_content or not doc_content.strip():
                    error_msg = f"文件内容为空: {actual_file_path}"
                    raise ValueError(error_msg)
        logger.info(f"文件内容提取成功，长度: {len(doc_content)} 字符")
        # 2. 根据配置文件进行文档分块
        chunks = document_service.split_content(
            content=doc_content,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap
        )
        if not chunks:
            error_msg = f"文档分块失败: {actual_file_path}"
            logger.warning(error_msg)
            return {"status": "error", "message": "文档分块失败，可能是内容格式不支持"}
        logger.info(f"文档分块成功，共生成 {len(chunks)} 个分块")
        # 更新总分块数
        update_task_status(
            request.doc_id,
            total_chunks=len(chunks),
            progress=10.0
        )
        # 3. 连接向量数据库
        async def connect_vector_db():
            return await vector_service.connect()
        try:
            if not asyncio.run(connect_vector_db()):
                error_msg = "向量数据库连接失败"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg}
            logger.info("向量数据库连接成功")
        except Exception as e:
            error_msg = f"向量数据库连接异常: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        # 4. 为每个分块生成嵌入向量并存储
        collection_name = settings.vector_db_collection_name
        processed_count = 0
        failed_count = 0
        logger.info(f"开始处理 {len(chunks)} 个分块，目标集合: {collection_name}")
        # 批量处理优化
        batch_size = 10  # 每批处理10个分块
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_vectors = []  
            # 批量生成嵌入向量
            try:
                batch_embeddings = embedding_service.generate_embeddings(batch_chunks)
                for j, (chunk, embedding) in enumerate(zip(batch_chunks, batch_embeddings)):
                    if embedding:
                        vector_id = f"{os.path.basename(actual_file_path)}_{i+j}_{request.doc_id or 'default'}"
                        
                        vector_data = {
                            "collection_name": collection_name,
                            "vector_id": vector_id,
                            "doc_id": request.doc_id or "default",
                            "doc_name": os.path.basename(actual_file_path),
                            "source_path": actual_file_path,
                            "create_at": datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
                            "update_at": datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
                            "chunk_content": chunk,
                            "vector": embedding,
                            "doc_type": request.doc_type,
                            "user_id": request.user_id,
                            "group_id": request.group_id
                        }
                        batch_vectors.append(vector_data)
                        processed_count += 1
                        logger.debug(f"分块 {i+j+1} 向量生成成功")
                    else:
                        failed_count += 1
                        logger.warning(f"分块 {i+j+1} 嵌入向量生成失败")
                
                # 批量插入向量
                if batch_vectors:
                    try:
                        async def batch_insert_vectors():
                            return await vector_service.batch_insert_vectors_async(batch_vectors)
                        
                        success = asyncio.run(batch_insert_vectors())
                        if success:
                            logger.debug(f"批次 {i//batch_size + 1} 向量插入成功，包含 {len(batch_vectors)} 个向量")
                        else:
                            failed_count += len(batch_vectors)
                            processed_count -= len(batch_vectors)
                            logger.warning(f"批次 {i//batch_size + 1} 向量插入失败")
                    except Exception as insert_error:
                        failed_count += len(batch_vectors)
                        processed_count -= len(batch_vectors)
                        logger.warning(f"批次 {i//batch_size + 1} 向量插入失败: {insert_error}")
                # 更新进度
                update_task_status(
                    request.doc_id,
                    processed_chunks=processed_count,
                    progress=10.0 + (min(i + batch_size, len(chunks)) / len(chunks)) * 80.0
                )
            except Exception as batch_error:
                failed_count += len(batch_chunks)
                logger.error(f"批次 {i//batch_size + 1} 处理失败: {batch_error}")
        
        logger.info(f"分块处理完成 - 总数: {len(chunks)}, 成功: {processed_count}, 失败: {failed_count}")
        # 5. 完成任务
        result = {
            "status": "success",
            "file_path": request.file_path,  # 保留原始路径用于记录
            "actual_file_path": actual_file_path,  # 实际处理的文件路径
            "total_chunks": len(chunks),
            "processed_chunks": processed_count,
            "failed_chunks": failed_count,
            "doc_type": request.doc_type,
            "is_url": is_url,
            "success_rate": round(processed_count / len(chunks) * 100, 2) if chunks else 0
        }
        # 更新任务完成状态
        update_task_status(
            request.doc_id,
            status=TaskStatus.COMPLETED,
            progress=100.0,
            completed_at=datetime.now(timezone(timedelta(hours=8))),
            result=json.dumps(result, ensure_ascii=False)
        )
        logger.info(f"文档处理完成: {result}")
        return result   
    except Exception as e:
        logger.error(f"处理文档时发生错误: {str(e)}")
        # 更新任务失败状态
        update_task_status(
            request.doc_id,
            status=TaskStatus.FAILED,
            error_message=str(e),
            completed_at=datetime.now(timezone(timedelta(hours=8)))
        )
        return {"status": "error", "message": str(e)}
    finally:
        # 清理临时文件
        if actual_file_path and os.path.exists(actual_file_path):
            try:
                os.unlink(actual_file_path)
                logger.info(f"临时文件已清理: {actual_file_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")