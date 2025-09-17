"""Pydantic模型定义"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
from models.enums import DocType

# 自定义JSON编码器，统一时间格式
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            # 格式化为 YYYY-MM-DD HH:MM:SS，去掉T分隔符
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)

# 基础响应模型
class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None

# 用户相关模型
class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=100)

class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    email: Optional[str]
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

# 聊天相关模型
class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    session_name: Optional[str] = None  # 会话名称
    is_first: bool = False  # 是否为新会话
    user_id: Optional[str] = None  # 用户ID，如果为空则使用默认用户ID
    use_knowledge_base: bool = True
    use_web_search: bool = True
    stream: bool = True

class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

class ChatSessionCreate(BaseModel):
    """创建聊天会话请求模型"""
    title: str = Field(..., min_length=1, max_length=200)
    user_id: str  # 用户ID改为字符串类型

class ChatSessionResponse(BaseModel):
    """聊天会话响应模型"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

class ChatSessionDelete(BaseModel):
    """删除聊天会话请求模型"""
    session_id: str

class ChatMessageDelete(BaseModel):
    """删除聊天消息请求模型"""
    message_id: str = Field(..., description="要删除的消息ID")

class ChatSessionUpdateTitle(BaseModel):
    """修改会话标题请求模型"""
    session_id: str
    title: str = Field(..., min_length=1, max_length=200)

class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str
    session_id: str
    knowledge_sources: Optional[List[Dict[str, Any]]] = None
    web_search_results: Optional[List[Dict[str, Any]]] = None

# 文档嵌入任务相关模型
# 知识库文档分组相关模型
class DocumentGroupCreate(BaseModel):
    """创建知识库分组请求模型"""
    group_name: str = Field(..., min_length=1, max_length=255, description="知识库分组名称")
    description: Optional[str] = Field(None, max_length=1000, description="知识库分组描述")
    user_id: str = Field(..., description="用户ID")

class DocumentGroupResponse(BaseModel):
    """知识库分组响应模型"""
    id: int
    user_id: str
    group_name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

class DocumentGroupUpdate(BaseModel):
    """更新知识库分组请求模型"""
    group_name: Optional[str] = Field(None, min_length=1, max_length=255, description="知识库分组名称")
    description: Optional[str] = Field(None, max_length=1000, description="知识库分组描述")

class DocumentEmbeddingTaskRequest(BaseModel):
    """文档嵌入任务请求模型"""
    file_path: str = Field(..., description="文件路径或URL")
    doc_type: DocType = Field(..., description="文档类型 (file 或 post)")
    doc_id: Optional[str] = Field(None, description="文档ID")
    doc_content: str = Field("", description="文档内容")
    user_id: str = Field(..., description="用户ID")
    group_id: Optional[int] = Field(None, description="分组ID")
    
    class Config:
        from_attributes = True
        use_enum_values = True  # 使用枚举值而不是枚举对象

# 知识库相关模型
class DocumentProcessRequest(BaseModel):
    """文档处理请求模型"""
    file_url: Optional[str] = None
    user_id: Optional[str] = None

class PostProcessRequest(BaseModel):
    """POST类型文档处理请求模型"""
    content: str = Field(..., min_length=1, max_length=50000, description="文档内容")
    title: Optional[str] = Field(None, max_length=200, description="文档标题")
    user_id: Optional[str] = Field(None, description="用户ID")
    group_id: Optional[int] = Field(None, description="分组ID")
    
class DocumentQueryRequest(BaseModel):
    """文档查询请求模型"""
    query: str = Field(..., min_length=1, max_length=1000)
    user_id: Optional[str] = None
    group_id: Optional[int] = Field(None, description="分组ID，用于指定查询的知识库")
    top_k: int = Field(10, ge=1, le=100)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)
    collection_name: Optional[str] = None

class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求模型"""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(10, ge=1, le=100)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)
    collection_name: Optional[str] = None
    response_time: Optional[float] = None

# 知识库相关模型
class DocumentUpload(BaseModel):
    """文档上传请求模型"""
    filename: str
    file_type: str
    user_id: str

class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

class DocumentChunkResponse(BaseModel):
    """文档分块响应模型"""
    id: int
    chunk_index: int
    content: str
    vector_id: Optional[str]
    
    class Config:
        from_attributes = True

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    chunk_size: int = Field(512, ge=100, le=2000)
    chunk_overlap: int = Field(50, ge=0, le=500)

class KnowledgeBaseResponse(BaseModel):
    """知识库响应模型"""
    id: int
    name: str
    description: Optional[str]
    collection_name: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    document_count: int
    chunk_count: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

# 搜索相关模型
class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., min_length=1, max_length=1000)
    search_type: str = Field("hybrid", pattern="^(knowledge_base|web_search|hybrid)$")
    top_k: int = Field(10, ge=1, le=50)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)

class SearchResult(BaseModel):
    """搜索结果模型"""
    content: str
    score: float
    source: str
    metadata: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    """搜索响应模型"""
    query: str
    results: List[SearchResult]
    total_count: int
    search_type: str
    response_time: float

# 系统状态模型
class SystemStatus(BaseModel):
    """系统状态模型"""
    status: str = "healthy"
    version: str = "1.0.0"
    uptime: float
    database_status: str
    redis_status: str
    milvus_status: str
    celery_status: str
    active_sessions: int
    total_documents: int
    total_chunks: int

# 任务相关模型
class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

# 配置模型
class ModelConfig(BaseModel):
    """模型配置"""
    chat_model: str
    embedding_model: str
    rerank_model: str
    max_tokens: int
    temperature: float
    top_p: float

class KnowledgeBaseConfig(BaseModel):
    """知识库配置"""
    chunk_size: int
    chunk_overlap: int
    top_k: int
    similarity_threshold: float
    rerank_top_k: int

class SearchConfig(BaseModel):
    """搜索配置"""
    web_search_enabled: bool
    web_search_timeout: int
    max_search_results: int
    knowledge_confidence_threshold: float
    use_web_fallback: bool