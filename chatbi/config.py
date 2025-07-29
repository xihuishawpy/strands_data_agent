"""
配置管理模块
处理环境变量、数据库连接配置等
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
import urllib.parse
from dotenv import load_dotenv
import logging


# 加载环境变量
load_dotenv()

@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str  # postgresql, mysql, sqlite
    host: str
    port: int
    database: str
    username: str
    password: str
    
    @property
    def connection_string(self) -> str:
        """生成数据库连接字符串"""
        if self.type == "postgresql":
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == "mysql":
            password_encode = urllib.parse.quote_plus(self.password)
            return f"mysql+pymysql://{self.username}:{password_encode}@{self.host}:{self.port}/{self.database}"
        elif self.type == "sqlite":
            return f"sqlite:///{self.database}"
        else:
            raise ValueError(f"不支持的数据库类型: {self.type}")

@dataclass
class LLMConfig:
    """大模型配置"""
    model_name: str = "qwen-max"  # 根据内存使用qwen-max
    coder_model: str = "qwen-coder-plus"  # 根据内存使用qwen-coder-plus处理代码
    embedding_model: str = "text-embedding-v3"  # 根据内存使用text-embedding-v3
    rerank_model: str = "gte-rerank-v2"  # 根据内存使用gte-rerank-v2
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

@dataclass
class WebConfig:
    """Web服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    secret_key: str = ""
    allowed_origins: list = None

class Config:
    """主配置类"""
    
    def __init__(self):
        self.database = self._load_database_config()
        self.llm = self._load_llm_config()
        self.web = self._load_web_config()
        self.knowledge_base_path = os.getenv("KNOWLEDGE_BASE_PATH", "./data/knowledge_base")
        self.schema_cache_ttl = int(os.getenv("SCHEMA_CACHE_TTL", "3600"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "./logs/chatbi.log")
        
        # RAG知识库配置
        self.rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
        self.rag_similarity_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.6"))  # 相似度阈值
        self.rag_confidence_threshold = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.8"))  # 置信度阈值
        self.rag_max_examples = int(os.getenv("RAG_MAX_EXAMPLES", "3"))
        
        # 确保目录存在
        self._ensure_directories()
        
        # 配置日志
        self._setup_logging()
    
    def _load_database_config(self) -> DatabaseConfig:
        """加载数据库配置"""
        db_type = os.getenv("DATABASE_TYPE", "postgresql").lower()
        
        if db_type == "sqlite":
            return DatabaseConfig(
                type="sqlite",
                host="",
                port=0,
                database=os.getenv("SQLITE_PATH", "./data/database.db"),
                username="",
                password=""
            )
        else:
            # PostgreSQL 或 MySQL
            host_key = "DATABASE_HOST" if db_type == "postgresql" else "MYSQL_HOST"
            port_key = "DATABASE_PORT" if db_type == "postgresql" else "MYSQL_PORT"
            db_key = "DATABASE_NAME" if db_type == "postgresql" else "MYSQL_DATABASE"
            user_key = "DATABASE_USER" if db_type == "postgresql" else "MYSQL_USER"
            pass_key = "DATABASE_PASSWORD" if db_type == "postgresql" else "MYSQL_PASSWORD"
            
            default_port = 5432 if db_type == "postgresql" else 3306
            
            return DatabaseConfig(
                type=db_type,
                host=os.getenv(host_key, "localhost"),
                port=int(os.getenv(port_key, default_port)),
                database=os.getenv(db_key, ""),
                username=os.getenv(user_key, ""),
                password=os.getenv(pass_key, "")
            )
    
    def _load_llm_config(self) -> LLMConfig:
        """加载大模型配置"""
        return LLMConfig(
            model_name=os.getenv("LLM_MODEL_NAME", "qwen-max"),
            coder_model=os.getenv("LLM_CODER_MODEL", "qwen-coder-plus"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-v3"),
            rerank_model=os.getenv("RERANK_MODEL", "gte-rerank-v2"),
            api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
    
    def _load_web_config(self) -> WebConfig:
        """加载Web配置"""
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
        origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]
        
        return WebConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            secret_key=os.getenv("SECRET_KEY", "your_secret_key_here"),
            allowed_origins=origins or ["*"]
        )
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            os.path.dirname(self.knowledge_base_path),
            os.path.dirname(self.log_file),
            "./data",
            "./logs"
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def validate(self) -> Dict[str, Any]:
        """验证配置"""
        errors = []
        warnings = []
        
        # 验证数据库配置
        if not self.database.database:
            errors.append("数据库名称不能为空")
        
        if self.database.type in ["postgresql", "mysql"]:
            if not self.database.username:
                errors.append("数据库用户名不能为空")
            if not self.database.password:
                warnings.append("数据库密码为空，可能导致连接失败")
        
        # 验证LLM配置
        if not self.llm.api_key:
            warnings.append("DashScope API密钥未设置")
        
        # 验证Web配置
        if self.web.secret_key == "your_secret_key_here":
            warnings.append("请更改默认的SECRET_KEY")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

# 全局配置实例
config = Config() 