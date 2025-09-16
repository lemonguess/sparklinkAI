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