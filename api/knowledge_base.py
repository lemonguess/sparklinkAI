"""知识库API路由"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
import logging
import aiofiles
from urllib.parse import urlparse
from core.database import get_db
from core.config import settings
from models.schemas import BaseResponse, TaskStatus, DocumentProcessRequest, KbDocumentRequest, PostProcessRequest, DocumentQueryRequest, KnowledgeSearchRequest, DocumentGroupCreate, DocumentGroupResponse, DocumentGroupUpdate, GroupDetailRequest, DocumentDeleteRequest, DocumentGroupDeleteRequest, DocumentGroupListRequest, DocumentGroupUpdateRequest, SearchRequest
from models.database import KbDocument, KbGroup
from models.enums import DocType, TaskStatus
from services.document_service import DocumentService
from services.search_service import SearchService
from services.vector_service import VectorService
from services.tasks.embedding_tasks import process_and_embed_document_task
from services.embedding_service import EmbeddingService
router = APIRouter()
logger = logging.getLogger(__name__)

# 服务实例
document_service = DocumentService()
search_service = SearchService()
vector_service = VectorService()

# 允许的文件类型
# 文件类型映射
def get_allowed_file_types():
    """根据配置获取允许的文件类型映射"""
    type_mapping = {
        'pdf': ('application/pdf', '.pdf'),
        'doc': ('application/msword', '.doc'),
        'docx': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
        'ppt': ('application/vnd.ms-powerpoint', '.ppt'),
        'pptx': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx'),
        'txt': ('text/plain', '.txt'),
        'md': ('text/markdown', '.md'),
        'jpg': ('image/jpeg', '.jpg'),
        'png': ('image/png', '.png'),
        'gif': ('image/gif', '.gif')
    }
    
    allowed_types = {}
    for file_type in settings.allowed_file_types:
        if file_type in type_mapping:
            mime_type, extension = type_mapping[file_type]
            allowed_types[mime_type] = extension
    
    return allowed_types

# ===== 知识库分组管理接口 =====
# 知识库分组管理接口
@router.post("/group/create_group", response_model=BaseResponse)
async def create_document_group(
    request: DocumentGroupCreate,
    db: Session = Depends(get_db)
):
    """创建知识库分组"""
    try:
        # 检查同一用户下是否已存在相同名称的知识库
        existing_group = db.query(KbGroup).filter(
            KbGroup.user_id == request.user_id,
            KbGroup.group_name == request.group_name,
            KbGroup.is_active == True
        ).first()
        
        if existing_group:
            raise HTTPException(
                status_code=400,
                detail=f"知识库 '{request.group_name}' 已存在"
            )
        
        # 创建新的知识库分组
        new_group = KbGroup(
            user_id=request.user_id,
            group_name=request.group_name,
            description=request.description
        )
        
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        
        return BaseResponse(
            success=True,
            message="知识库创建成功",
            data={
                "group_id": str(new_group.id),  # 确保返回字符串类型
                "group_name": new_group.group_name,
                "description": new_group.description,
                "created_at": new_group.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建知识库分组失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="创建知识库分组失败")

@router.post("/group/get_groups", response_model=BaseResponse)
async def get_document_groups(
    request: DocumentGroupListRequest,
    db: Session = Depends(get_db)
):
    """获取用户的知识库分组列表"""
    try:
        # 如果没有提供user_id，使用默认用户ID
        user_id = request.user_id or settings.default_user_id
        
        groups = db.query(KbGroup).filter(
            KbGroup.user_id == user_id,
            KbGroup.is_active == True
        ).order_by(KbGroup.created_at.desc()).all()
        groups_data = []
        for group in groups:
            # 统计该分组下的任务数量
            task_count = db.query(KbDocument).filter(
                KbGroup.id == group.id,
                KbGroup.user_id == user_id
            ).count()
            groups_data.append({
                "id": str(group.id),  # 确保返回字符串类型
                "group_name": group.group_name,
                "description": group.description,
                "task_count": task_count,
                "created_at": group.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "updated_at": group.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return BaseResponse(
            success=True,
            message="获取知识库列表成功",
            data=groups_data
        )
        
    except Exception as e:
        logger.error(f"获取知识库分组列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取知识库分组列表失败")

@router.post("/group/update_group", response_model=BaseResponse)
async def update_document_group(
    request: DocumentGroupUpdateRequest,
    db: Session = Depends(get_db)
):
    """更新知识库分组信息"""
    try:
        # 如果没有提供user_id，使用默认用户ID
        user_id = request.user_id or settings.default_user_id
        
        # 查找指定的知识库分组
        group = db.query(KbGroup).filter(
            KbGroup.id == request.group_id,
            KbGroup.user_id == user_id,
            KbGroup.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="知识库分组不存在")
        
        # 更新字段
        if request.group_name is not None:
            # 检查新名称是否与其他知识库冲突
            existing_group = db.query(KbGroup).filter(
                KbGroup.user_id == user_id,
                KbGroup.group_name == request.group_name,
                KbGroup.id != request.group_id,
                KbGroup.is_active == True
            ).first()
            
            if existing_group:
                raise HTTPException(
                    status_code=400,
                    detail=f"知识库名称 '{request.group_name}' 已存在"
                )
            
            group.group_name = request.group_name
        
        if request.description is not None:
            group.description = request.description
        
        db.commit()
        db.refresh(group)
        
        return BaseResponse(
            success=True,
            message="知识库更新成功",
            data={
                "id": group.id,
                "group_name": group.group_name,
                "description": group.description,
                "updated_at": group.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新知识库分组失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="更新知识库分组失败")

@router.post("/group/delete_group", response_model=BaseResponse)
async def delete_document_group(
    request: DocumentGroupDeleteRequest,
    db: Session = Depends(get_db)
):
    """删除知识库分组（软删除）"""
    try:
        # 查找指定的知识库分组
        group = db.query(KbGroup).filter(
            KbGroup.id == request.group_id,
            KbGroup.user_id == request.user_id,
            KbGroup.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="知识库分组不存在")
        
        # 检查该分组下是否还有未删除的子文档
        active_documents = db.query(KbDocument).filter(
            KbGroup.id == request.group_id,
            KbGroup.user_id == request.user_id,
            KbGroup.is_active == True
        ).count()
        
        if active_documents > 0:
            return BaseResponse(
                success=False,
                message=f"无法删除知识库分组，该分组下还有 {active_documents} 个未删除的文档，请先删除所有文档后再删除分组",
                data={"active_documents_count": active_documents}
            )
        
        # 软删除
        group.is_active = False
        db.commit()
        
        return BaseResponse(
            success=True,
            message="知识库删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库分组失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="删除知识库分组失败")

@router.post("/group/detail", response_model=BaseResponse)
async def get_group_documents(
    request: GroupDetailRequest,
    db: Session = Depends(get_db)
):
    """获取指定分组内的知识列表"""
    try:
        # 如果没有提供user_id，使用默认用户ID
        user_id = request.user_id or settings.default_user_id
        
        # 验证分组是否存在且属于该用户
        group = db.query(KbGroup).filter(
            KbGroup.id == request.group_id,
            KbGroup.user_id == user_id,
            KbGroup.is_active == True
        ).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="知识库分组不存在")
        
        # 获取该分组下的所有文档任务（排除已删除的）
        documents = db.query(KbDocument).filter(
            KbDocument.group_id == request.group_id,
            KbDocument.user_id == user_id,
            KbDocument.is_active == True  # 排除已删除的文档
        ).order_by(KbDocument.created_at.desc()).all()
        
        documents_data = []
        for doc in documents:
            documents_data.append({
                "doc_id": doc.doc_id,  # 使用 doc_id 作为主要标识符
                "task_id": doc.task_id,
                "doc_name": doc.doc_name,
                "doc_path": doc.doc_path,
                "doc_type": doc.doc_type.value if doc.doc_type else None,
                "status": doc.status.value,
                "progress": doc.progress,
                "total_chunks": doc.total_chunks,
                "processed_chunks": doc.processed_chunks,
                "error_message": doc.error_message,
                "created_at": doc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "updated_at": doc.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "started_at": doc.started_at.strftime('%Y-%m-%d %H:%M:%S') if doc.started_at else None,
                "completed_at": doc.completed_at.strftime('%Y-%m-%d %H:%M:%S') if doc.completed_at else None
            })
        
        return BaseResponse(
            success=True,
            message="获取分组知识列表成功",
            data={
                "group_info": {
                    "id": str(group.id),  # 确保返回字符串类型
                    "group_name": group.group_name,
                    "description": group.description,
                    "created_at": group.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "updated_at": group.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                },
                "documents": documents_data,
                "total_count": len(documents_data)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分组知识列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取分组知识列表失败")

# ===== 任务管理接口 =====
@router.post("/tasks/file_process", response_model=BaseResponse)
async def process_document(
    file: Optional[UploadFile] = File(None),
    group_id: Optional[str] = Form(None),
    user_id_form: Optional[str] = Form(None),
    request: Optional[DocumentProcessRequest] = None,
    db: Session = Depends(get_db)
):
    """文档处理接口 - 支持二进制文件或文件链接"""
    try:
        # 验证输入参数
        file_url = request.file_url if request else None
        # 兼容 multipart/form-data 的 user_id 字段
        user_id = user_id_form or (request.user_id if request else None)
        
        if not file and not file_url:
            raise HTTPException(
                status_code=400, 
                detail="必须提供文件或文件链接"
            )
        
        if file and file_url:
            raise HTTPException(
                status_code=400, 
                detail="不能同时提供文件和文件链接"
            )
        
        # 处理任务参数
        actual_user_id = user_id if user_id else settings.default_user_id
        doc_type = ""
        file_path = ""
        doc_id = uuid.uuid4().hex
        filename = ""  # 任务显示名，避免未赋值导致异常
        if file:
            doc_type = DocType.FILE
            # 处理上传文件
            allowed_file_types = get_allowed_file_types()
            
            # 检查文件类型
            if file.content_type not in allowed_file_types:
                raise HTTPException(
                    status_code=400, 
                    detail=f"不支持的文件类型: {file.content_type}"
                )
            
            # 检查文件大小限制（部分部署环境 UploadFile 不带 size 属性，做保护）
            if hasattr(file, "size") and file.size and file.size > settings.max_file_size * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"文件大小不能超过{settings.max_file_size:.0f}MB")
            
            # 生成唯一文件名
            file_extension = allowed_file_types[file.content_type]
            unique_filename = f"{doc_id}{file_extension}"
            
            # 使用配置的上传目录
            upload_dir = settings.upload_dir
            file_path = os.path.join(upload_dir, unique_filename)
            
            # 保存文件
            async with aiofiles.open(file_path, "wb") as buffer:
                content = await file.read()
                await buffer.write(content)
            
            # 使用原始文件名作为展示名称，若缺失则退回唯一文件名
            original_filename = os.path.basename(file.filename) if getattr(file, "filename", None) else unique_filename
            filename = original_filename
        else:
            doc_type = DocType.URL
            # 验证URL格式
            parsed_url = urlparse(file_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise HTTPException(status_code=400, detail="无效的文件链接")
            # 获取文件名
            filename = os.path.basename(parsed_url.path)
            if not filename:
                filename = f"download_{doc_id}"
        # 先保存任务记录到数据库（使用 doc_id 作为主键）
        embedding_task = KbDocument(
            doc_id=doc_id,  # 使用 doc_id 作为主键
            user_id=actual_user_id,
            group_id=group_id,  # 修复：写入分组ID
            doc_name=filename,
            doc_path=file_path or file_url,
            doc_type=doc_type,
            status=TaskStatus.PENDING,
            progress=0,
            total_chunks=0,
            processed_chunks=0,
            error_message=None
        )
        db.add(embedding_task)
        db.commit()
        db.refresh(embedding_task)
        
        # 提交Celery任务处理嵌入
        task_request = KbDocumentRequest(
            file_path=file_path or file_url,
            doc_type=doc_type,
            doc_id=doc_id,
            doc_content="",  # 文件类型不需要预设内容
            doc_name=filename,
            user_id=actual_user_id,
            group_id=group_id  # 修复：写入分组ID
        )
        celery_task = process_and_embed_document_task.delay(task_request.dict())
        task_id = celery_task.id
        
        # 根据 doc_id 更新真实 task_id（避免并发下空字符串主键冲突）
        db.query(KbDocument).filter(
            KbDocument.doc_id == doc_id,
            KbDocument.user_id == actual_user_id
        ).update({"task_id": task_id}, synchronize_session=False)
        db.commit()
        
        return BaseResponse(
            success=True,
            message="文档处理任务已提交，正在后台处理",
            data={
                "task_id": task_id,
                "filename": embedding_task.doc_name,
                "status": embedding_task.status.value
            }
        )
        
    except Exception as e:
        logger.error(f"文档处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/post_process", response_model=BaseResponse)
async def process_post_content(
    request: PostProcessRequest,
    db: Session = Depends(get_db)
):
    """POST类型文档处理接口 - 处理纯文本内容（合并了原 upload_text_document 功能）"""
    try:
        # 验证输入参数
        if not request.content or not request.content.strip():
            raise HTTPException(
                status_code=400, 
                detail="文档内容不能为空"
            )
        
        # 如果提供了 group_id，验证知识库分组是否存在
        if request.group_id:
            group = db.query(KbGroup).filter(
                KbGroup.id == request.group_id,
                KbGroup.user_id == request.user_id,
                KbGroup.is_active == True
            ).first()
            
            if not group:
                raise HTTPException(status_code=404, detail="知识库分组不存在")
        
        # 处理任务参数
        doc_id = uuid.uuid4().hex
        doc_title = request.title if request.title else f"POST文档_{doc_id[:8]}"
        
        # 先保存任务记录到数据库（使用 doc_id 作为主键）
        embedding_task = KbDocument(
            doc_id=doc_id,  # 使用 doc_id 作为主键
            user_id=request.user_id,
            group_id=request.group_id,  # 修复：写入分组ID
            doc_name=doc_title,
            doc_path=request.source_url,
            doc_type=DocType.POST,
            status=TaskStatus.PENDING,
            progress=0,
            total_chunks=0,
            processed_chunks=0,
            error_message=None
        )
        db.add(embedding_task)
        db.commit()
        db.refresh(embedding_task)
        
        # 提交Celery任务处理嵌入
        task_request = KbDocumentRequest(
            file_path=request.source_url,
            doc_type=DocType.POST,
            doc_id=doc_id,
            doc_name=doc_title,
            doc_content=request.content,
            user_id=request.user_id,
            group_id=request.group_id
        )
        celery_task = process_and_embed_document_task.delay(task_request.dict())
        task_id = celery_task.id
        
        # 根据 doc_id 更新真实 task_id（避免并发下空字符串主键冲突）
        db.query(KbDocument).filter(
            KbGroup.id == doc_id,
            KbGroup.user_id == request.user_id
        ).update({"task_id": task_id}, synchronize_session=False)
        db.commit()
        
        return BaseResponse(
            success=True,
            message="文本处理任务已提交，正在后台处理",
            data={
                "task_id": task_id,
                "doc_title": doc_title,
                "doc_id": doc_id,
                "status": "pending"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本处理失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="文本处理失败")

@router.get("/tasks/{task_id}", response_model=BaseResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取任务状态"""
    try:
        task = db.query(KbDocument).filter(
            KbDocument.task_id == task_id
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return BaseResponse(
            success=True,
            message="获取任务状态成功",
            data={
                "task_id": task.task_id,
                "doc_name": task.doc_name,
                "status": task.status.value,
                "progress": task.progress,
                "total_chunks": task.total_chunks,
                "processed_chunks": task.processed_chunks,
                "error_message": task.error_message,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at
            }
        )
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== 知识库查询接口 =====
@router.post("/query", response_model=BaseResponse)
async def query_knowledge_base(
    request: DocumentQueryRequest,
    db: Session = Depends(get_db)
):
    """查询知识库文档"""
    try:
        # 使用向量服务进行搜索
        await vector_service.connect()
        embedding_service = EmbeddingService()
        # 生成查询向量
        query_embedding = await embedding_service.generate_embedding(request.query)
        
        # 执行向量搜索
        results = await vector_service.search_vectors_async(
            collection_name=request.collection_name or 'sparklinkai_knowledge',
            query_embedding=query_embedding,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            user_id=request.user_id,
            group_id=request.group_id
        )
        
        return BaseResponse(
            success=True,
            message="查询成功",
            data={
                "query": request.query,
                "results": results,
                "total": len(results)
            }
        )
        
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/document/delete", response_model=BaseResponse)
async def delete_document(
    request: DocumentDeleteRequest,
    db: Session = Depends(get_db)
):
    """删除文档（软删除数据库记录，真实删除Milvus向量数据）"""
    try:
        # 如果没有提供user_id，使用默认用户ID
        user_id = request.user_id or settings.default_user_id
        
        # 查找文档记录
        document_task = db.query(KbDocument).filter(
            KbDocument.doc_id == request.doc_id,
            KbDocument.user_id == user_id,
            KbDocument.is_active == True
        ).first()
        
        if not document_task:
            return BaseResponse(
                success=False,
                message="文档不存在或已被删除",
                data=None
            )
        
        # 软删除数据库记录
        document_task.is_active = False
        db.commit()
        
        # 真实删除Milvus向量数据
        try:
            collection_name = settings.MILVUS_COLLECTION_NAME
            delete_result = await vector_service.delete_vectors_by_doc_id(
                collection_name=collection_name,
                doc_id=document_task.doc_id
            )
            
            if not delete_result:
                logger.warning(f"Milvus向量删除失败，但数据库记录已软删除: doc_id={document_task.doc_id}")
        except Exception as e:
            logger.error(f"删除Milvus向量时出错: {e}")
            # 即使Milvus删除失败，也不回滚数据库操作
        
        return BaseResponse(
            success=True,
            message="文档删除成功",
            data={
                "doc_id": document_task.doc_id,
                "doc_name": document_task.doc_name,
                "deleted_at": document_task.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        db.rollback()
        return BaseResponse(
            success=False,
            message="删除文档失败",
            data=None
        )

# ===== 文档上传接口 =====
@router.post("/search", response_model=BaseResponse)
async def search_knowledge_base(
    request: KnowledgeSearchRequest,
    db: Session = Depends(get_db)
):
    """搜索知识库"""
    try:
        results = await search_service.knowledge_search(
            query=request.query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            collection_name=request.collection_name,
            group_id=request.group_id,
            user_id=request.user_id
        )
        return BaseResponse(
            success=True,
            message="搜索成功",
            data={
                "query": request.query,
                "results": results,
                "total": len(results)
            }
        )
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))