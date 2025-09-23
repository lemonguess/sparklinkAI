"""系统API路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import time
import psutil
import logging

from core.database import get_db
from core import db_manager
from core.config import settings
from models.schemas import BaseResponse, SystemStatus, ModelConfig, KnowledgeBaseConfig, SearchConfig
from models.database import ChatSession
from services.vector_service import VectorService

router = APIRouter()
logger = logging.getLogger(__name__)

# 应用启动时间
start_time = time.time()

@router.get("/status", response_model=BaseResponse)
async def get_system_status(db: Session = Depends(get_db)):
    """获取系统状态"""
    try:
        # 计算运行时间
        uptime = time.time() - start_time
        
        # 检查各组件状态
        database_status = "healthy" if db_manager.test_connection() else "unhealthy"
        redis_status = "healthy" if db_manager.test_redis_connection() else "unhealthy"
        
        # Milvus状态检查
        vector_service = VectorService()
        try:
            milvus_status = "healthy" if await vector_service.test_connection() else "unhealthy"
        except Exception as e:
            logger.warning(f"Milvus状态检查失败: {e}")
            milvus_status = "unhealthy"
        
        # Celery状态检查（简化）
        celery_status = "unknown"  # 实际项目中需要实现Celery状态检查
        
        # 统计信息
        active_sessions = db.query(ChatSession).filter(
            ChatSession.is_active == True
        ).count()
        
        total_documents = 0  # db.query(KbDocument).count()
        total_chunks = 0  # db.query(DocumentChunk).count()
        
        # 整体状态
        overall_status = "healthy" if all([
            database_status == "healthy",
            redis_status == "healthy"
        ]) else "unhealthy"
        
        status_data = SystemStatus(
            status=overall_status,
            version="1.0.0",
            uptime=uptime,
            database_status=database_status,
            redis_status=redis_status,
            milvus_status=milvus_status,
            celery_status=celery_status,
            active_sessions=active_sessions,
            total_documents=total_documents,
            total_chunks=total_chunks
        )
        
        return BaseResponse(
            success=True,
            message="系统状态获取成功",
            data=status_data
        )
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info", response_model=BaseResponse)
async def get_system_info():
    """获取系统信息"""
    try:
        # 系统资源信息
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = {
            "version": "1.0.0",
            "python_version": "3.13",
            "fastapi_version": "0.116.1",
            "uptime": time.time() - start_time,
            "resources": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            },
            "configuration": {
                "debug_mode": settings.APP_DEBUG,
                "host": settings.APP_HOST,
                "port": settings.APP_PORT
            }
        }
        
        return BaseResponse(
            success=True,
            message="系统信息获取成功",
            data=system_info
        )
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/models", response_model=BaseResponse)
async def get_model_config():
    """获取模型配置"""
    try:
        config = ModelConfig(
            chat_model=settings.chat_model,
            embedding_model=settings.embedding_model,
            rerank_model=settings.rerank_model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            top_p=0.9  # 从配置文件读取
        )
        
        return BaseResponse(
            success=True,
            message="模型配置获取成功",
            data=config
        )
    except Exception as e:
        logger.error(f"获取模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/knowledge_base", response_model=BaseResponse)
async def get_knowledge_base_config():
    """获取知识库配置"""
    try:
        config = KnowledgeBaseConfig(
            chunk_size=settings.chunk_size,
            chunk_overlap=50,  # 从配置文件读取
            top_k=settings.top_k,
            similarity_threshold=settings.similarity_threshold,
            rerank_top_k=5  # 从配置文件读取
        )
        
        return BaseResponse(
            success=True,
            message="知识库配置获取成功",
            data=config
        )
    except Exception as e:
        logger.error(f"获取知识库配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/search", response_model=BaseResponse)
async def get_search_config():
    """获取搜索配置"""
    try:
        config = SearchConfig(
            web_search_enabled=settings.web_search_enabled,
            web_search_timeout=10,  # 从配置文件读取
            max_search_results=5,  # 从配置文件读取
            knowledge_confidence_threshold=settings.knowledge_confidence_threshold,
            use_web_fallback=True  # 从配置文件读取
        )
        
        return BaseResponse(
            success=True,
            message="搜索配置获取成功",
            data=config
        )
    except Exception as e:
        logger.error(f"获取搜索配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=BaseResponse)
async def get_system_stats(db: Session = Depends(get_db)):
    """获取系统统计信息"""
    try:
        # 数据库统计
        total_sessions = db.query(ChatSession).count()
        active_sessions = db.query(ChatSession).filter(
            ChatSession.is_active == True
        ).count()
        
        total_documents = 0  # db.query(KbDocument).count()
        processed_documents = 0  # db.query(KbDocument).filter(KbDocument.status == "completed").count()
        
        total_chunks = 0  # db.query(DocumentChunk).count()
        
        # 按状态统计文档
        doc_stats = {}
        for status in ["pending", "processing", "completed", "failed"]:
            count = 0  # db.query(KbDocument).filter(KbDocument.status == status).count()
            doc_stats[status] = count
        
        stats = {
            "sessions": {
                "total": total_sessions,
                "active": active_sessions,
                "inactive": total_sessions - active_sessions
            },
            "documents": {
                "total": total_documents,
                "processed": processed_documents,
                "processing_rate": (processed_documents / total_documents * 100) if total_documents > 0 else 0,
                "by_status": doc_stats
            },
            "chunks": {
                "total": total_chunks,
                "average_per_document": total_chunks / total_documents if total_documents > 0 else 0
            },
            "system": {
                "uptime": time.time() - start_time,
                "requests_handled": "N/A",  # 需要实现请求计数器
                "average_response_time": "N/A"  # 需要实现响应时间统计
            }
        }
        
        return BaseResponse(
            success=True,
            message="系统统计信息获取成功",
            data=stats
        )
    except Exception as e:
        logger.error(f"获取系统统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/database", response_model=BaseResponse)
async def test_database_connection():
    """测试数据库连接"""
    try:
        mysql_status = db_manager.test_connection()
        redis_status = db_manager.test_redis_connection()
        
        return BaseResponse(
            success=mysql_status and redis_status,
            message="数据库连接测试完成",
            data={
                "mysql": "connected" if mysql_status else "disconnected",
                "redis": "connected" if redis_status else "disconnected"
            }
        )
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs", response_model=BaseResponse)
async def get_recent_logs(
    lines: int = 100,
    level: str = "INFO"
):
    """获取最近的日志（简化实现）"""
    try:
        # 这里应该实现真正的日志读取逻辑
        # 暂时返回模拟数据
        logs = [
            {
                "timestamp": "2024-01-01 12:00:00",
                "level": "INFO",
                "message": "应用启动成功",
                "module": "main"
            },
            {
                "timestamp": "2024-01-01 12:01:00",
                "level": "INFO",
                "message": "数据库连接正常",
                "module": "database"
            }
        ]
        
        return BaseResponse(
            success=True,
            message="日志获取成功",
            data={
                "logs": logs,
                "total_lines": len(logs),
                "level_filter": level
            }
        )
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))