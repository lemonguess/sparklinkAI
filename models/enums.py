from enum import Enum
class SearchStrategy(Enum):
    """搜索策略枚举"""
    KNOWLEDGE_ONLY = "knowledge_only"
    WEB_ONLY = "web_only"
    HYBRID = "hybrid"
    AUTO = "auto"
    NONE  = 'none'