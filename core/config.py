"""配置管理模块"""
import os
import configparser
from typing import List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings:
    """应用配置类"""
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'conf.ini')
        self.config.read(config_path, encoding='utf-8')
    
    # OpenAI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
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
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_USER: str = os.getenv("MILVUS_USER", "")
    MILVUS_PASSWORD: str = os.getenv("MILVUS_PASSWORD", "")
    
    # 应用配置
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    
    # Celery配置
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
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
        return self.config.getint('knowledge_base', 'chunk_size', fallback=512)
    
    @property
    def top_k(self) -> int:
        """获取检索top_k"""
        return self.config.getint('knowledge_base', 'top_k', fallback=10)
    
    @property
    def similarity_threshold(self) -> float:
        """获取相似度阈值"""
        return self.config.getfloat('knowledge_base', 'similarity_threshold', fallback=0.7)
    
    @property
    def web_search_enabled(self) -> bool:
        """是否启用联网搜索"""
        return self.config.getboolean('search', 'web_search_enabled', fallback=True)
    
    @property
    def knowledge_confidence_threshold(self) -> float:
        """知识库置信度阈值"""
        return self.config.getfloat('search', 'knowledge_confidence_threshold', fallback=0.8)
    
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
        """获取Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

# 全局配置实例
settings = Settings()