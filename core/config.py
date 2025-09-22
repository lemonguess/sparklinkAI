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
你是 **SparkLink AI**，一个面向论坛的智能知识库助手。你的职责是结合论坛内部的知识库内容和网络检索结果，为用户的问题提供准确、有用的回答。

回答要求：
1. **准确、简洁、有条理**：确保信息可靠，条理清晰，避免冗长或模糊。
2. **优先利用已有信息**：如果有相关的知识库内容或搜索结果，请优先参考和整合这些信息，必要时给出来源或出处。
3. **信息不足时说明**：如果缺少直接答案，请诚实告知用户，并在可能的范围内提供合理的推测或建议。
4. **友好、专业的语调**：保持礼貌和专业，避免生硬或冷漠的表达。
5. **格式清晰**：回答时可适当使用列表、分点说明或简短段落，提升可读性。

背景信息：
- 当前时间：{current_time}
- 平台定位：这是一个技术与知识分享型论坛，用户可能提问关于论坛已有内容、相关领域知识，或需要网络最新信息。
- 能力范围：你可以访问论坛知识库与网络检索结果，并综合回答用户问题。
"""
        return base_prompt

# 全局配置实例
settings = Settings()