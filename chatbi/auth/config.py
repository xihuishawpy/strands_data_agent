"""
认证模块配置
定义认证和权限相关的配置参数
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging


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
    password_history_count: int = 5  # 密码历史记录数量
    
    # JWT配置
    jwt_secret_key: str = ""  # JWT密钥
    jwt_algorithm: str = "HS256"  # JWT算法
    jwt_expiration: int = 3600  # JWT过期时间（秒）
    
    # 安全配置
    enable_csrf_protection: bool = True  # 启用CSRF防护
    enable_session_fixation_protection: bool = True  # 启用会话固定攻击防护
    secure_cookies: bool = True  # 安全Cookie
    
    # 审计配置
    enable_audit_logging: bool = True  # 启用审计日志
    audit_log_retention_days: int = 90  # 审计日志保留天数
    
    @classmethod
    def from_env(cls) -> 'AuthConfig':
        """从环境变量加载配置"""
        return cls(
            session_timeout=int(os.getenv("AUTH_SESSION_TIMEOUT", "3600")),
            session_cleanup_interval=int(os.getenv("AUTH_SESSION_CLEANUP_INTERVAL", "300")),
            max_sessions_per_user=int(os.getenv("AUTH_MAX_SESSIONS_PER_USER", "5")),
            
            max_login_attempts=int(os.getenv("AUTH_MAX_LOGIN_ATTEMPTS", "5")),
            lockout_duration=int(os.getenv("AUTH_LOCKOUT_DURATION", "900")),
            lockout_enabled=os.getenv("AUTH_LOCKOUT_ENABLED", "true").lower() == "true",
            
            password_min_length=int(os.getenv("AUTH_PASSWORD_MIN_LENGTH", "8")),
            password_max_length=int(os.getenv("AUTH_PASSWORD_MAX_LENGTH", "128")),
            require_password_complexity=os.getenv("AUTH_REQUIRE_PASSWORD_COMPLEXITY", "true").lower() == "true",
            password_history_count=int(os.getenv("AUTH_PASSWORD_HISTORY_COUNT", "5")),
            
            jwt_secret_key=os.getenv("AUTH_JWT_SECRET_KEY", ""),
            jwt_algorithm=os.getenv("AUTH_JWT_ALGORITHM", "HS256"),
            jwt_expiration=int(os.getenv("AUTH_JWT_EXPIRATION", "3600")),
            
            enable_csrf_protection=os.getenv("AUTH_ENABLE_CSRF_PROTECTION", "true").lower() == "true",
            enable_session_fixation_protection=os.getenv("AUTH_ENABLE_SESSION_FIXATION_PROTECTION", "true").lower() == "true",
            secure_cookies=os.getenv("AUTH_SECURE_COOKIES", "true").lower() == "true",
            
            enable_audit_logging=os.getenv("AUTH_ENABLE_AUDIT_LOGGING", "true").lower() == "true",
            audit_log_retention_days=int(os.getenv("AUTH_AUDIT_LOG_RETENTION_DAYS", "90"))
        )
    
    def validate(self) -> Dict[str, Any]:
        """验证配置参数"""
        errors = []
        warnings = []
        
        # 验证会话配置
        if self.session_timeout <= 0:
            errors.append("会话超时时间必须大于0")
        elif self.session_timeout < 300:
            warnings.append("会话超时时间过短，建议至少5分钟")
        
        if self.session_cleanup_interval <= 0:
            errors.append("会话清理间隔必须大于0")
        
        if self.max_sessions_per_user <= 0:
            errors.append("每用户最大会话数必须大于0")
        
        # 验证登录安全配置
        if self.max_login_attempts <= 0:
            errors.append("最大登录尝试次数必须大于0")
        
        if self.lockout_duration <= 0:
            errors.append("账户锁定时间必须大于0")
        
        # 验证密码配置
        if self.password_min_length < 6:
            warnings.append("密码最小长度建议至少6位")
        elif self.password_min_length < 8:
            warnings.append("密码最小长度建议至少8位")
        
        if self.password_max_length < self.password_min_length:
            errors.append("密码最大长度不能小于最小长度")
        
        if self.password_history_count < 0:
            errors.append("密码历史记录数量不能为负数")
        
        # 验证JWT配置
        if not self.jwt_secret_key:
            errors.append("JWT密钥不能为空")
        elif len(self.jwt_secret_key) < 32:
            warnings.append("JWT密钥长度建议至少32位")
        
        if self.jwt_expiration <= 0:
            errors.append("JWT过期时间必须大于0")
        
        # 验证审计配置
        if self.audit_log_retention_days <= 0:
            errors.append("审计日志保留天数必须大于0")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


@dataclass
class PermissionConfig:
    """权限配置"""
    # 默认权限配置
    default_schema_access: List[str] = None  # 默认schema访问权限
    admin_schemas: List[str] = None  # 管理员可访问的所有schema
    public_schemas: List[str] = None  # 公共schema（所有用户可访问）
    
    # 权限控制配置
    schema_isolation_enabled: bool = True  # 是否启用schema隔离
    strict_permission_check: bool = True  # 是否启用严格权限检查
    inherit_admin_permissions: bool = True  # 管理员是否继承所有权限
    
    # 权限缓存配置
    permission_cache_enabled: bool = True  # 是否启用权限缓存
    permission_cache_ttl: int = 300  # 权限缓存TTL（秒）
    permission_cache_size: int = 1000  # 权限缓存大小
    
    # 权限变更配置
    require_approval_for_admin_permissions: bool = True  # 管理员权限变更是否需要审批
    log_permission_changes: bool = True  # 是否记录权限变更日志
    
    def __post_init__(self):
        """初始化后处理"""
        if self.default_schema_access is None:
            self.default_schema_access = []
        if self.admin_schemas is None:
            self.admin_schemas = []
        if self.public_schemas is None:
            self.public_schemas = []
    
    @classmethod
    def from_env(cls) -> 'PermissionConfig':
        """从环境变量加载配置"""
        # 解析列表类型的环境变量
        def parse_list_env(env_var: str, default: List[str] = None) -> List[str]:
            value = os.getenv(env_var, "")
            if not value:
                return default or []
            return [item.strip() for item in value.split(",") if item.strip()]
        
        return cls(
            default_schema_access=parse_list_env("PERM_DEFAULT_SCHEMA_ACCESS"),
            admin_schemas=parse_list_env("PERM_ADMIN_SCHEMAS"),
            public_schemas=parse_list_env("PERM_PUBLIC_SCHEMAS"),
            
            schema_isolation_enabled=os.getenv("PERM_SCHEMA_ISOLATION_ENABLED", "true").lower() == "true",
            strict_permission_check=os.getenv("PERM_STRICT_PERMISSION_CHECK", "true").lower() == "true",
            inherit_admin_permissions=os.getenv("PERM_INHERIT_ADMIN_PERMISSIONS", "true").lower() == "true",
            
            permission_cache_enabled=os.getenv("PERM_CACHE_ENABLED", "true").lower() == "true",
            permission_cache_ttl=int(os.getenv("PERM_CACHE_TTL", "300")),
            permission_cache_size=int(os.getenv("PERM_CACHE_SIZE", "1000")),
            
            require_approval_for_admin_permissions=os.getenv("PERM_REQUIRE_APPROVAL_FOR_ADMIN", "true").lower() == "true",
            log_permission_changes=os.getenv("PERM_LOG_PERMISSION_CHANGES", "true").lower() == "true"
        )
    
    def validate(self) -> Dict[str, Any]:
        """验证配置参数"""
        errors = []
        warnings = []
        
        # 验证缓存配置
        if self.permission_cache_ttl <= 0:
            errors.append("权限缓存TTL必须大于0")
        
        if self.permission_cache_size <= 0:
            errors.append("权限缓存大小必须大于0")
        
        # 验证schema配置
        if self.schema_isolation_enabled and not self.default_schema_access:
            warnings.append("启用schema隔离但未配置默认schema访问权限")
        
        # 检查schema配置冲突
        admin_set = set(self.admin_schemas)
        public_set = set(self.public_schemas)
        default_set = set(self.default_schema_access)
        
        if admin_set & public_set:
            warnings.append("管理员schema和公共schema有重叠")
        
        if not default_set.issubset(public_set | admin_set):
            warnings.append("默认schema访问权限包含非公共和非管理员schema")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_user_default_schemas(self, is_admin: bool = False) -> List[str]:
        """获取用户默认schema列表"""
        schemas = set(self.public_schemas + self.default_schema_access)
        
        if is_admin and self.inherit_admin_permissions:
            schemas.update(self.admin_schemas)
        
        return list(schemas)
    
    def is_public_schema(self, schema_name: str) -> bool:
        """检查是否为公共schema"""
        return schema_name in self.public_schemas
    
    def is_admin_schema(self, schema_name: str) -> bool:
        """检查是否为管理员schema"""
        return schema_name in self.admin_schemas


# 全局配置实例
def get_auth_config() -> AuthConfig:
    """获取认证配置实例"""
    return AuthConfig.from_env()


def get_permission_config() -> PermissionConfig:
    """获取权限配置实例"""
    return PermissionConfig.from_env()


# 配置验证函数
def validate_all_configs() -> Dict[str, Any]:
    """验证所有认证相关配置"""
    auth_config = get_auth_config()
    perm_config = get_permission_config()
    
    auth_validation = auth_config.validate()
    perm_validation = perm_config.validate()
    
    all_errors = auth_validation["errors"] + perm_validation["errors"]
    all_warnings = auth_validation["warnings"] + perm_validation["warnings"]
    
    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "warnings": all_warnings,
        "auth_config": auth_validation,
        "permission_config": perm_validation
    }