from enum import Enum


class SearchStrategy(Enum):
    """搜索策略枚举"""
    KNOWLEDGE_ONLY = "knowledge_only"
    WEB_ONLY = "web_only"
    HYBRID = "hybrid"
    AUTO = "auto"
    NONE  = 'none'


class DocType(Enum):
    """文档类型枚举"""
    FILE = "file"  # 文件类型
    POST = "post"  # 帖子类型


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败