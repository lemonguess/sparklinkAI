"""知识库API路由"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import logging

from core.database import get_db
from core.config import settings
from models.schemas import (
    DocumentResponse, DocumentUpload, KnowledgeBaseCreate, KnowledgeBaseResponse,
    BaseResponse, TaskStatus
)
from models.database import Document, KnowledgeBase, User
from services.knowledge_service import KnowledgeService
from services.document_service import DocumentService

router = APIRouter()
logger = logging.getLogger(__name__)

# 服务实例
knowledge_service = KnowledgeService()
document_service = DocumentService()

# 允许的文件类型
ALLOWED_FILE_TYPES = {
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.ms-powerpoint': '.ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'text/plain': '.txt',
    'text/markdown': '.md',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif'
}

@router.post("/knowledge_bases", response_model=BaseResponse)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """创建知识库"""
    try:
        # 生成唯一的集合名称
        collection_name = f"kb_{uuid.uuid4().hex[:8]}"
        
        # 创建知识库记录
        kb = KnowledgeBase(
            name=kb_data.name,
            description=kb_data.description,
            collection_name=collection_name,
            embedding_model=kb_data.embedding_model,
            chunk_size=kb_data.chunk_size,
            chunk_overlap=kb_data.chunk_overlap
        )
        db.add(kb)
        db.commit()
        db.refresh(kb)
        
        # 在Milvus中创建集合
        try:
            await knowledge_service.create_collection(collection_name)
        except Exception as e:
            logger.warning(f"创建Milvus集合失败: {e}")
        
        return BaseResponse(
            success=True,
            message="知识库创建成功",
            data=KnowledgeBaseResponse.from_orm(kb)
        )
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge_bases", response_model=BaseResponse)
async def get_knowledge_bases(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取知识库列表"""
    try:
        kbs = db.query(KnowledgeBase).filter(
            KnowledgeBase.is_active == True
        ).offset(skip).limit(limit).all()
        
        kb_responses = [KnowledgeBaseResponse.from_orm(kb) for kb in kbs]
        
        return BaseResponse(
            success=True,
            message="获取知识库列表成功",
            data=kb_responses
        )
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/upload", response_model=BaseResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(""),  # 从表单参数获取用户ID，空字符串表示使用默认用户
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """上传文档"""
    try:
        # 检查文件类型
        if file.content_type not in ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file.content_type}"
            )
        
        # 检查文件大小（10MB限制）
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")
        
        # 生成唯一文件名
        file_extension = ALLOWED_FILE_TYPES[file.content_type]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        # 创建上传目录
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 处理user_id，如果为空则使用默认用户ID
        actual_user_id = user_id if user_id else settings.default_user_id
        
        # 创建文档记录
        document = Document(
            user_id=actual_user_id,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            file_type=file.content_type,
            status="pending"
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 添加后台任务处理文档
        background_tasks.add_task(
            document_service.process_document,
            document.id
        )
        
        return BaseResponse(
            success=True,
            message="文档上传成功，正在后台处理",
            data=DocumentResponse.from_orm(document)
        )
        
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=BaseResponse)
async def get_documents(
    user_id: str = "",  # 空字符串表示使用默认用户
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取文档列表"""
    try:
        # 处理user_id，如果为空则使用默认用户ID
        actual_user_id = user_id if user_id else settings.default_user_id
        query = db.query(Document).filter(Document.user_id == actual_user_id)
        
        if status:
            query = query.filter(Document.status == status)
        
        documents = query.offset(skip).limit(limit).all()
        doc_responses = [DocumentResponse.from_orm(doc) for doc in documents]
        
        return BaseResponse(
            success=True,
            message="获取文档列表成功",
            data=doc_responses
        )
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}", response_model=BaseResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """获取文档详情"""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return BaseResponse(
            success=True,
            message="获取文档详情成功",
            data=DocumentResponse.from_orm(document)
        )
    except Exception as e:
        logger.error(f"获取文档详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}", response_model=BaseResponse)
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """删除文档"""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 删除文件
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # 删除数据库记录
        db.delete(document)
        db.commit()
        
        # 删除向量数据（如果存在）
        try:
            await knowledge_service.delete_document_vectors(document_id)
        except Exception as e:
            logger.warning(f"删除向量数据失败: {e}")
        
        return BaseResponse(
            success=True,
            message="文档删除成功"
        )
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/{document_id}/reprocess", response_model=BaseResponse)
async def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """重新处理文档"""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 重置状态
        document.status = "pending"
        document.error_message = None
        db.commit()
        
        # 添加后台任务
        background_tasks.add_task(
            document_service.process_document,
            document_id
        )
        
        return BaseResponse(
            success=True,
            message="文档重新处理任务已提交"
        )
    except Exception as e:
        logger.error(f"重新处理文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=BaseResponse)
async def search_knowledge_base(
    query: str,
    top_k: int = 10,
    similarity_threshold: float = 0.7,
    collection_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """搜索知识库"""
    try:
        results = await knowledge_service.search(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            collection_name=collection_name
        )
        
        return BaseResponse(
            success=True,
            message="搜索完成",
            data={
                "query": query,
                "results": results,
                "total_count": len(results)
            }
        )
    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/knowledge_bases/{kb_id}", response_model=BaseResponse)
async def delete_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db)
):
    """删除知识库"""
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 软删除
        kb.is_active = False
        db.commit()
        
        # 删除Milvus集合
        try:
            await knowledge_service.drop_collection(kb.collection_name)
        except Exception as e:
            logger.warning(f"删除Milvus集合失败: {e}")
        
        return BaseResponse(
            success=True,
            message="知识库删除成功"
        )
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))