"""数据库模型定义"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import pytz
from .enums import TaskStatus, DocType

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
    kb_groups = relationship("KbGroup", back_populates="user")
    kb_documents = relationship("KbDocument", back_populates="user")

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
    thinking_process = Column(Text)  # 思考过程内容
    
    # 关系
    session = relationship("ChatSession", back_populates="messages")

class KbGroup(Base):
    """知识库分组表"""
    __tablename__ = "kb_groups"
    
    id = Column(String(32), primary_key=True, index=True, default=lambda: uuid.uuid4().hex)  # UUID字符串主键
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    group_name = Column(String(255), nullable=False)  # 知识库分组名称
    description = Column(Text, nullable=True)  # 知识库分组描述
    created_at = Column(DateTime, default=get_shanghai_time)
    updated_at = Column(DateTime, default=get_shanghai_time, onupdate=get_shanghai_time)
    is_active = Column(Boolean, default=True)
    
    # 关系
    user = relationship("User", back_populates="kb_groups")
    kb_documents = relationship("KbDocument", back_populates="kb_group")

class KbDocument(Base):
    """文档嵌入处理任务表"""
    __tablename__ = "kb_documents"
    doc_id = Column(String(500), primary_key=True, index=True)  # 文档ID，用于唯一标识文档，作为主键
    task_id = Column(String(64), nullable=True, index=True)  # Celery任务ID
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    group_id = Column(String(32), ForeignKey("kb_groups.id"), nullable=True)  # 文档所属组ID，关联KbGroup表
    doc_name = Column(String(255), nullable=False)  # 文档文件名
    doc_path = Column(String(500), nullable=True)  # 文档路径（可选）
    doc_content = Column(Text, nullable=True)  # 文档内容，仅限于doc_type==post的情况
    doc_type = Column(Enum(DocType), nullable=True)  # 文档类型,文件或帖子(files or posts)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)  # 进度百分比 0.0-100.0
    result = Column(Text, nullable=True)  # 任务处理结果
    total_chunks = Column(Integer, default=0)  # 总分块数
    processed_chunks = Column(Integer, default=0)  # 已处理分块数
    error_message = Column(Text, nullable=True)  # 错误信息
    is_active = Column(Boolean, default=True, nullable=False)  # 是否激活（软删除标记）
    created_at = Column(DateTime, default=get_shanghai_time)
    updated_at = Column(DateTime, default=get_shanghai_time, onupdate=get_shanghai_time)
    started_at = Column(DateTime, nullable=True)  # 开始处理时间
    completed_at = Column(DateTime, nullable=True)  # 完成时间
    
    # 关系
    user = relationship("User", back_populates="kb_documents")
    kb_group = relationship("KbGroup", back_populates="kb_documents")