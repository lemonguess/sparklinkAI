"""数据库模型定义"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# 上海时区
SHANGHAI_TZ = timezone(timedelta(hours=8))

def get_shanghai_time():
    """获取上海时间"""
    return datetime.now(SHANGHAI_TZ)

Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String(32), primary_key=True, index=True, default=lambda: uuid.uuid4().hex)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=get_shanghai_time)
    updated_at = Column(DateTime, default=get_shanghai_time, onupdate=get_shanghai_time)
    is_active = Column(Boolean, default=True)
    
    # 关系
    sessions = relationship("ChatSession", back_populates="user")
    documents = relationship("Document", back_populates="user")

class ChatSession(Base):
    """聊天会话模型"""
    __tablename__ = "chat_sessions"
    
    id = Column(String(32), primary_key=True, index=True, default=lambda: uuid.uuid4().hex)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=get_shanghai_time)
    updated_at = Column(DateTime, default=get_shanghai_time, onupdate=get_shanghai_time)
    is_active = Column(Boolean, default=True)
    
    # 关系
    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = "chat_messages"
    
    id = Column(String(32), primary_key=True, index=True, default=lambda: uuid.uuid4().hex)
    session_id = Column(String(32), ForeignKey("chat_sessions.id"), nullable=False)
    request_id = Column(String(32), nullable=False, index=True, default=lambda: uuid.uuid4().hex)  # 请求ID，用于追溯
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    sequence_number = Column(Integer, nullable=False, default=0)  # 消息序号，确保正确排序
    created_at = Column(DateTime, default=get_shanghai_time)
    
    # 扩展字段
    use_knowledge_base = Column(Boolean, default=False)
    use_web_search = Column(Boolean, default=False)
    knowledge_sources = Column(Text)  # JSON格式存储知识库来源
    web_search_results = Column(Text)  # JSON格式存储搜索结果
    
    # 关系
    session = relationship("ChatSession", back_populates="messages")

class Document(Base):
    """文档模型"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    
    # 处理状态
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    processed_at = Column(DateTime)
    error_message = Column(Text)
    
    # 时间戳
    created_at = Column(DateTime, default=get_shanghai_time)
    updated_at = Column(DateTime, default=get_shanghai_time, onupdate=get_shanghai_time)
    
    # 关系
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    """文档分块模型"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    # 向量相关
    vector_id = Column(String(100))  # Milvus中的向量ID
    embedding_model = Column(String(100))
    
    # 时间戳
    created_at = Column(DateTime, default=get_shanghai_time)
    
    # 关系
    document = relationship("Document", back_populates="chunks")

class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    collection_name = Column(String(100), nullable=False)  # Milvus集合名
    
    # 配置
    embedding_model = Column(String(100), nullable=False)
    chunk_size = Column(Integer, default=512)
    chunk_overlap = Column(Integer, default=50)
    
    # 统计信息
    document_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=get_shanghai_time)
    updated_at = Column(DateTime, default=get_shanghai_time, onupdate=get_shanghai_time)
    is_active = Column(Boolean, default=True)

class SearchLog(Base):
    """搜索日志模型"""
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(32), ForeignKey("chat_sessions.id"))
    query = Column(Text, nullable=False)
    search_type = Column(String(20), nullable=False)  # knowledge_base, web_search, hybrid
    
    # 结果统计
    knowledge_results_count = Column(Integer, default=0)
    web_results_count = Column(Integer, default=0)
    total_results_count = Column(Integer, default=0)
    
    # 性能指标
    response_time = Column(Float)  # 响应时间（秒）
    knowledge_confidence = Column(Float)  # 知识库置信度
    
    # 时间戳
    created_at = Column(DateTime, default=get_shanghai_time)