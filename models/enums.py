from enum import Enum
class SearchStrategy(Enum):
    """搜索策略枚举"""
    KNOWLEDGE_FIRST = "knowledge_first"
    WEB_FIRST = "web_first"
    HYBRID = "hybrid"
    AUTO = "auto"