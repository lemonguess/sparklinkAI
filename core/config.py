"""配置管理模块"""
import os
import configparser
from typing import List, Optional
from dotenv import load_dotenv
from datetime import datetime
# 加载环境变量
load_dotenv()

class Settings:
    """应用配置类"""
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'conf.ini')
        self.config.read(config_path, encoding='utf-8')
    
    # SiliconFlow配置
    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_BASE_URL: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    
    # TextIn OCR配置
    TEXTIN_API_KEY: str = os.getenv("TEXTIN_API_KEY", "")
    TEXTIN_API_SECRET: str = os.getenv("TEXTIN_API_SECRET", "")
    
    # Web搜索配置
    WEB_SEARCH_API_KEY: str = os.getenv("WEB_SEARCH_API_KEY", "")
    
    # 数据库配置
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "sparklinkai")
    
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_CHAT_MEMORY_DB: int = int(os.getenv("REDIS_CHAT_MEMORY_DB", "0"))
    
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_USER: str = os.getenv("MILVUS_USER", "")
    MILVUS_PASSWORD: str = os.getenv("MILVUS_PASSWORD", "")
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "sparklinkai_knowledge")
    
    # 应用配置
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    
    # Celery配置
    CELERY_BROKER_DB: int = int(os.getenv("CELERY_BROKER_DB", "1"))
    CELERY_RESULT_DB: int = int(os.getenv("CELERY_RESULT_DB", "2"))
    
    @property
    def chat_model(self) -> str:
        """获取对话模型名称"""
        return self.config.get('models', 'chat_model', fallback='deepseek-ai/DeepSeek-R1')
    
    @property
    def embedding_model(self) -> str:
        """获取嵌入模型名称"""
        return self.config.get('models', 'embedding_model', fallback='BAAI/bge-large-zh-v1.5')
    
    @property
    def rerank_model(self) -> str:
        """获取重排序模型名称"""
        return self.config.get('models', 'rerank_model', fallback='BAAI/bge-reranker-v2-m3')
    
    @property
    def max_tokens(self) -> int:
        """获取最大token数"""
        return self.config.getint('models', 'max_tokens', fallback=4096)
    
    @property
    def temperature(self) -> float:
        """获取温度参数"""
        return self.config.getfloat('models', 'temperature', fallback=0.7)
    
    @property
    def chunk_size(self) -> int:
        """获取文档分块大小"""
        return self.config.getint('embedding', 'chunk_size', fallback=512)
    
    @property
    def chunk_overlap(self) -> int:
        """获取文档分块重叠大小"""
        return self.config.getint('embedding', 'chunk_overlap', fallback=50)
    
    @property
    def top_k(self) -> int:
        """获取检索top_k"""
        return self.config.getint('knowledge_base', 'top_k', fallback=10)
    
    @property
    def similarity_threshold(self) -> float:
        """获取相似度阈值"""
        return self.config.getfloat('knowledge_base', 'similarity_threshold', fallback=0.5)
    
    @property
    def web_search_enabled(self) -> bool:
        """是否启用联网搜索"""
        return self.config.getboolean('search', 'web_search_enabled', fallback=True)
    
    @property
    def knowledge_confidence_threshold(self) -> float:
        """知识库置信度阈值"""
        return self.config.getfloat('search', 'knowledge_confidence_threshold', fallback=0.5)
    
    @property
    def cors_origins(self) -> List[str]:
        """获取CORS允许的源"""
        origins_str = self.config.get('api', 'cors_origins', fallback='["*"]')
        # 简单解析，实际项目中可能需要更复杂的解析
        return ["*"] if origins_str == '["*"]' else origins_str.strip('[]').replace('"', '').split(',')
    
    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    @property
    def redis_url(self) -> str:
        """获取Redis连接URL（用于聊天记忆缓存）"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_CHAT_MEMORY_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_CHAT_MEMORY_DB}"
    
    @property
    def celery_broker_url(self) -> str:
        """获取Celery Broker连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.CELERY_BROKER_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.CELERY_BROKER_DB}"
    
    @property
    def celery_result_backend(self) -> str:
        """获取Celery Result Backend连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.CELERY_RESULT_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.CELERY_RESULT_DB}"
    
    @property
    def default_username(self) -> str:
        """获取默认用户名"""
        return self.config.get('default_user', 'username', fallback='admin')
    
    @property
    def default_email(self) -> str:
        """获取默认用户邮箱"""
        return self.config.get('default_user', 'email', fallback='admin@sparklinkai.com')
    
    @property
    def default_user_active(self) -> bool:
        """获取默认用户激活状态"""
        return self.config.getboolean('default_user', 'is_active', fallback=True)
    
    @property
    def default_user_id(self) -> str:
        """获取默认用户ID"""
        return self.config.get('default_user', 'id', fallback='admin123456789abcdef0123456789ab')
    
    @property
    def default_kb_group_id(self) -> str:
        """获取默认知识库分组ID"""
        return self.config.get('default_kb_group', 'id', fallback='default_kb_group_123456789abcdef')
    
    @property
    def default_kb_group_name(self) -> str:
        """获取默认知识库分组名称"""
        return self.config.get('default_kb_group', 'name', fallback='默认知识库')
    
    @property
    def default_kb_group_description(self) -> str:
        """获取默认知识库分组描述"""
        return self.config.get('default_kb_group', 'description', fallback='系统自动创建的默认知识库分组')
    
    @property
    def upload_dir(self) -> str:
        """获取文件上传目录"""
        return self.config.get('upload', 'upload_dir', fallback='uploads')
    
    @property
    def max_file_size(self) -> int:
        """获取最大文件上传大小（字节）"""
        return self.config.getint('upload', 'max_file_size', fallback=10485760)  # 默认10MB
    
    @property
    def allowed_file_types(self) -> List[str]:
        """获取允许的文件类型"""
        types_str = self.config.get('upload', 'allowed_file_types', fallback='["pdf", "doc", "docx", "ppt", "pptx", "txt", "md", "jpg", "png", "gif"]')
        # 简单解析配置文件中的列表格式
        import json
        try:
            return json.loads(types_str.replace("'", '"'))
        except:
            return ["pdf", "doc", "docx", "ppt", "pptx", "txt", "md", "jpg", "png", "gif"]
    
    @property
    def base_prompt(self) -> str:
        """获取基础提示词"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base_prompt = f"""
你是 **SparkLink AI**，一个面向论坛的智能知识库助手。你的职责是结合论坛内部的知识库内容和网络检索结果，为用户的问题提供准确、有用的回答，并在回答中标注信息来源。
回答要求：
回答要求：
1. **准确、简洁、有条理**：确保信息可靠，条理清晰，避免冗长或模糊。
2. **来源引用**：
   - 如果来源包含 `title` 和 `url`，请使用 Markdown 超链接格式 `[title](url)`。
   - 如果来源没有 `url`，请直接显示 `title`。
   - 【知识库片段】来源请标记为“摘自本站内容”，没有则不标记；【网络搜索结果】请标记为“来自网络搜索”，没有则不标记。
   - 如果多个来源涉及同一结论，可以合并说明，但每个来源都应当被保留。
3. **信息不足时说明**：缺少直接答案时，需诚实告知用户，并提供合理推测或建议。
4. **友好、专业的语调**：保持礼貌和专业。
5. **格式清晰**：回答时可使用列表、分点说明或简短段落，提升可读性。
背景信息：
- 当前时间：{current_time}
- 平台定位：本站名叫星闪联盟社区，以提升开发者互动、强化社区生态和会员体验、支持多元化的内容运营，构建技术论坛、众筹能力货架、代码管理及项目管理及与之配套的完整的后台管理系统。
- 能力范围：目标将以“平台化、智能化、国际化”为导向，构建集内容展示、知识资料、开发者社区、技术论坛、智能问答、项目管理等功能于一体的综合社区门户
"""
        return base_prompt.strip()
    @property
    def conversation_history_limit(self) -> int:
        """获取对话历史记录限制数量"""
        return self.config.getint('chat', 'conversation_history_limit', fallback=20)
# 全局配置实例
settings = Settings()