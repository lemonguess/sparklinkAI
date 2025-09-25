"""FastAPI主应用"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import time
import logging
from contextlib import asynccontextmanager
from core.config import settings
from core import db_manager
from api import chat, knowledge_base, system
from models.schemas import BaseResponse
from utils.user_utils import create_default_user, ensure_default_kb_groups
from services.vector_service import VectorService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("正在启动 SparkLink AI 应用...")
    # 创建数据库表
    try:
        db_manager.create_tables()
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
    # 测试数据库连接
    if db_manager.test_connection():
        logger.info("数据库连接正常")
    else:
        logger.error("数据库连接失败")
    # 测试Redis连接
    if db_manager.test_redis_connection():
        logger.info("Redis连接正常")
    else:
        logger.error("Redis连接失败")
    # 创建默认用户
    try:
        create_default_user()
        logger.info("默认用户检查/创建完成")
    except Exception as e:
        logger.error(f"默认用户创建失败: {e}")
    # 创建默认知识库分组
    try:
        ensure_default_kb_groups()
        logger.info("默认知识库分组检查/创建完成")
    except Exception as e:
        logger.error(f"默认知识库分组创建失败: {e}")
    # 创建上传目录
    try:
        import os
        upload_dir = settings.upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        logger.info(f"上传目录创建/检查完成: {upload_dir}")
    except Exception as e:
        logger.error(f"上传目录创建失败: {e}")
    # 初始化 Milvus 集合
    try:
        vector_service = VectorService()
        if await vector_service.connect():
            await vector_service.create_collection(settings.MILVUS_COLLECTION_NAME)
            logger.info(f"Milvus集合初始化完成: {settings.MILVUS_COLLECTION_NAME}")
        else:
            logger.warning("Milvus 未连接，向量相关功能不可用")
    except Exception as e:
        logger.error(f"Milvus 初始化失败: {e}")
    logger.info("SparkLink AI 应用启动完成")
    yield
    
    # 关闭时执行
    logger.info("正在关闭 SparkLink AI 应用...")

# 创建FastAPI应用
app = FastAPI(
    title="SparkLink AI",
    description="智能聊天助手系统 - 支持知识库增强和联网搜索",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 模板配置
templates = Jinja2Templates(directory="templates")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 添加请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=BaseResponse(
            success=False,
            message=f"服务器内部错误: {str(exc)}",
            data=None
        ).dict()
    )

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 路由配置
app.include_router(chat.router, prefix="/api/v1/chat", tags=["聊天"])
app.include_router(knowledge_base.router, prefix="/api/v1/kb", tags=["知识库"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统"])

# 页面路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """聊天页面"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request):
    """知识库管理页面"""
    return templates.TemplateResponse("knowledge.html", {"request": request})

# API根路径
@app.get("/api", response_model=BaseResponse)
async def root():
    """API根路径"""
    return BaseResponse(
        success=True,
        message="欢迎使用 SparkLink AI 智能聊天助手系统",
        data={
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    )

# 健康检查
@app.get("/health", response_model=BaseResponse)
async def health_check():
    """健康检查"""
    # 检查数据库连接
    db_status = "healthy" if db_manager.test_connection() else "unhealthy"
    redis_status = "healthy" if db_manager.test_redis_connection() else "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"
    
    return BaseResponse(
        success=overall_status == "healthy",
        message=f"系统状态: {overall_status}",
        data={
            "status": overall_status,
            "database": db_status,
            "redis": redis_status,
            "timestamp": time.time()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level="info"
    )
