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

@dataclass
class RAGConfig:
    """RAG配置"""
    enabled: bool = True
    similarity_threshold: float = 0.6
    confidence_threshold: float = 0.8
    max_examples: int = 3
    vector_dimension: int = 1536
    search_timeout: float = 5.0
    cache_size: int = 1000
    batch_size: int = 100
    index_type: str = "hnsw"
    distance_metric: str = "cosine"
    
    def validate(self) -> Dict[str, Any]:
        """验证RAG配置参数"""
        errors = []
        warnings = []
        
        # 验证阈值范围
        if not 0.0 <= self.similarity_threshold <= 1.0:
            errors.append("RAG_SIMILARITY_THRESHOLD必须在0.0-1.0之间")
        
        if not 0.0 <= self.confidence_threshold <= 1.0:
            errors.append("RAG_CONFIDENCE_THRESHOLD必须在0.0-1.0之间")
        
        if self.similarity_threshold >= self.confidence_threshold:
            warnings.append("RAG_SIMILARITY_THRESHOLD应该小于RAG_CONFIDENCE_THRESHOLD")
        
        # 验证数值参数
        if self.max_examples <= 0:
            errors.append("RAG_MAX_EXAMPLES必须大于0")
        elif self.max_examples > 10:
            warnings.append("RAG_MAX_EXAMPLES过大可能影响性能")
        
        if self.vector_dimension <= 0:
            errors.append("RAG_VECTOR_DIMENSION必须大于0")
        
        if self.search_timeout <= 0:
            errors.append("RAG_SEARCH_TIMEOUT必须大于0")
        
        if self.cache_size <= 0:
            errors.append("RAG_CACHE_SIZE必须大于0")
        
        if self.batch_size <= 0:
            errors.append("RAG_BATCH_SIZE必须大于0")
        
        # 验证枚举值
        valid_index_types = ["hnsw", "flat", "ivf"]
        if self.index_type not in valid_index_types:
            errors.append(f"RAG_INDEX_TYPE必须是{valid_index_types}之一")
        
        valid_distance_metrics = ["cosine", "euclidean", "manhattan"]
        if self.distance_metric not in valid_distance_metrics:
            errors.append(f"RAG_DISTANCE_METRIC必须是{valid_distance_metrics}之一")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

@dataclass
class AuthConfig:
    """认证配置"""
    # 会话配置
    session_timeout: int = 3600  # 会话超时时间（秒）
    session_cleanup_interval: int = 300  # 会话清理间隔（秒）
    max_sessions_per_user: int = 5  # 每个用户最大会话数
    
    # 登录安全配置
    max_login_attempts: int = 5  # 最大登录尝试次数
    lockout_duration: int = 900  # 账户锁定时间（秒）
    lockout_enabled: bool = True  # 是否启用账户锁定
    
    # 密码配置
    password_min_length: int = 8  # 密码最小长度
    password_max_length: int = 128  # 密码最大长度
    require_password_complexity: bool = True  # 是否要求密码复杂度
    
    # JWT配置
    jwt_secret_key: str = ""  # JWT密钥
    jwt_algorithm: str = "HS256"  # JWT算法
    jwt_expiration: int = 3600  # JWT过期时间（秒）
    
    # 安全配置
    enable_csrf_protection: bool = True  # 启用CSRF防护
    enable_audit_logging: bool = True  # 启用审计日志

@dataclass
class PermissionConfig:
    """权限配置"""
    # 默认权限配置
    default_schema_access: list = None  # 默认schema访问权限
    admin_schemas: list = None  # 管理员可访问的所有schema
    public_schemas: list = None  # 公共schema（所有用户可访问）
    
    # 权限控制配置
    schema_isolation_enabled: bool = True  # 是否启用schema隔离
    strict_permission_check: bool = True  # 是否启用严格权限检查
    inherit_admin_permissions: bool = True  # 管理员是否继承所有权限
    
    # 权限缓存配置
    permission_cache_enabled: bool = True  # 是否启用权限缓存
    permission_cache_ttl: int = 300  # 权限缓存TTL（秒）
    
    def __post_init__(self):
        """初始化后处理"""
        if self.default_schema_access is None:
            self.default_schema_access = []
        if self.admin_schemas is None:
            self.admin_schemas = []
        if self.public_schemas is None:
            self.public_schemas = []

class Config:
    """主配置类"""
    
    def __init__(self):
        self.database = self._load_database_config()
        self.llm = self._load_llm_config()
        self.web = self._load_web_config()
        self.rag = self._load_rag_config()
        self.auth = self._load_auth_config()
        self.permission = self._load_permission_config()
        self.knowledge_base_path = os.getenv("KNOWLEDGE_BASE_PATH", "./data/knowledge_base")
        self.schema_cache_ttl = int(os.getenv("SCHEMA_CACHE_TTL", "3600"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "./logs/chatbi.log")
        
        # 确保目录存在
        self._ensure_directories()
        
        # 配置日志
        self._setup_logging()
        
        # 验证配置
        self._validate_config()
    
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
    
    def _load_rag_config(self) -> RAGConfig:
        """加载RAG配置"""
        try:
            return RAGConfig(
                enabled=os.getenv("RAG_ENABLED", "true").lower() == "true",
                similarity_threshold=float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.6")),
                confidence_threshold=float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.8")),
                max_examples=int(os.getenv("RAG_MAX_EXAMPLES", "3")),
                vector_dimension=int(os.getenv("RAG_VECTOR_DIMENSION", "1536")),
                search_timeout=float(os.getenv("RAG_SEARCH_TIMEOUT", "5.0")),
                cache_size=int(os.getenv("RAG_CACHE_SIZE", "1000")),
                batch_size=int(os.getenv("RAG_BATCH_SIZE", "100")),
                index_type=os.getenv("RAG_INDEX_TYPE", "hnsw").lower(),
                distance_metric=os.getenv("RAG_DISTANCE_METRIC", "cosine").lower()
            )
        except (ValueError, TypeError) as e:
            logging.warning(f"RAG配置参数解析失败，使用默认值: {e}")
            return RAGConfig()  # 使用默认值
    
    def _load_auth_config(self) -> AuthConfig:
        """加载认证配置"""
        return AuthConfig(
            session_timeout=int(os.getenv("AUTH_SESSION_TIMEOUT", "3600")),
            session_cleanup_interval=int(os.getenv("AUTH_SESSION_CLEANUP_INTERVAL", "300")),
            max_sessions_per_user=int(os.getenv("AUTH_MAX_SESSIONS_PER_USER", "5")),
            max_login_attempts=int(os.getenv("AUTH_MAX_LOGIN_ATTEMPTS", "5")),
            lockout_duration=int(os.getenv("AUTH_LOCKOUT_DURATION", "900")),
            lockout_enabled=os.getenv("AUTH_LOCKOUT_ENABLED", "true").lower() == "true",
            password_min_length=int(os.getenv("AUTH_PASSWORD_MIN_LENGTH", "8")),
            password_max_length=int(os.getenv("AUTH_PASSWORD_MAX_LENGTH", "128")),
            require_password_complexity=os.getenv("AUTH_REQUIRE_PASSWORD_COMPLEXITY", "true").lower() == "true",
            jwt_secret_key=os.getenv("AUTH_JWT_SECRET_KEY", "your_jwt_secret_key_here"),
            jwt_algorithm=os.getenv("AUTH_JWT_ALGORITHM", "HS256"),
            jwt_expiration=int(os.getenv("AUTH_JWT_EXPIRATION", "3600")),
            enable_csrf_protection=os.getenv("AUTH_ENABLE_CSRF_PROTECTION", "true").lower() == "true",
            enable_audit_logging=os.getenv("AUTH_ENABLE_AUDIT_LOGGING", "true").lower() == "true"
        )
    
    def _load_permission_config(self) -> PermissionConfig:
        """加载权限配置"""
        # 解析列表类型的环境变量
        def parse_list_env(env_var: str, default: list = None) -> list:
            value = os.getenv(env_var, "")
            if not value:
                return default or []
            return [item.strip() for item in value.split(",") if item.strip()]
        
        return PermissionConfig(
            default_schema_access=parse_list_env("PERM_DEFAULT_SCHEMA_ACCESS"),
            admin_schemas=parse_list_env("PERM_ADMIN_SCHEMAS"),
            public_schemas=parse_list_env("PERM_PUBLIC_SCHEMAS"),
            schema_isolation_enabled=os.getenv("PERM_SCHEMA_ISOLATION_ENABLED", "true").lower() == "true",
            strict_permission_check=os.getenv("PERM_STRICT_PERMISSION_CHECK", "true").lower() == "true",
            inherit_admin_permissions=os.getenv("PERM_INHERIT_ADMIN_PERMISSIONS", "true").lower() == "true",
            permission_cache_enabled=os.getenv("PERM_CACHE_ENABLED", "true").lower() == "true",
            permission_cache_ttl=int(os.getenv("PERM_CACHE_TTL", "300"))
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
    
    def _validate_config(self):
        """内部配置验证，在初始化时调用"""
        validation_result = self.validate()
        
        if validation_result["errors"]:
            error_msg = "配置验证失败:\n" + "\n".join(f"- {error}" for error in validation_result["errors"])
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        if validation_result["warnings"]:
            warning_msg = "配置警告:\n" + "\n".join(f"- {warning}" for warning in validation_result["warnings"])
            logging.warning(warning_msg)
    
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
        
        # 验证RAG配置
        rag_validation = self.rag.validate()
        errors.extend(rag_validation["errors"])
        warnings.extend(rag_validation["warnings"])
        
        # 验证认证配置
        if not self.auth.jwt_secret_key or self.auth.jwt_secret_key == "your_jwt_secret_key_here":
            warnings.append("请设置JWT密钥 (AUTH_JWT_SECRET_KEY)")
        
        if self.auth.password_min_length < 6:
            warnings.append("密码最小长度建议至少6位")
        
        if self.auth.session_timeout < 300:
            warnings.append("会话超时时间过短，建议至少5分钟")
        
        # 验证权限配置
        if self.permission.schema_isolation_enabled and not self.permission.default_schema_access:
            warnings.append("启用schema隔离但未配置默认schema访问权限")
        
        # 验证路径配置
        if not os.path.exists(os.path.dirname(self.knowledge_base_path)):
            try:
                os.makedirs(os.path.dirname(self.knowledge_base_path), exist_ok=True)
            except Exception as e:
                errors.append(f"无法创建知识库目录: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def update_rag_config(self, **kwargs) -> bool:
        """动态更新RAG配置"""
        try:
            # 创建新的RAG配置对象
            current_config = self.rag.__dict__.copy()
            current_config.update(kwargs)
            
            # 验证新配置
            new_rag_config = RAGConfig(**current_config)
            validation_result = new_rag_config.validate()
            
            if validation_result["errors"]:
                logging.error(f"RAG配置更新失败: {validation_result['errors']}")
                return False
            
            # 更新配置
            self.rag = new_rag_config
            
            if validation_result["warnings"]:
                logging.warning(f"RAG配置更新警告: {validation_result['warnings']}")
            
            logging.info("RAG配置更新成功")
            return True
            
        except Exception as e:
            logging.error(f"RAG配置更新异常: {e}")
            return False
    
    def reload_config(self):
        """重新加载配置"""
        try:
            # 重新加载环境变量
            load_dotenv(override=True)
            
            # 重新加载各个配置
            self.database = self._load_database_config()
            self.llm = self._load_llm_config()
            self.web = self._load_web_config()
            self.rag = self._load_rag_config()
            
            # 重新验证配置
            self._validate_config()
            
            logging.info("配置重新加载成功")
            return True
            
        except Exception as e:
            logging.error(f"配置重新加载失败: {e}")
            return False

# 全局配置实例
config = Config() 