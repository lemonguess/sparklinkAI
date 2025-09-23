from .database import DatabaseManager
# 全局数据库管理器实例
db_manager = DatabaseManager()
# 全局共享状态，用于追踪和取消活动的流式请求
active_streams = {}
