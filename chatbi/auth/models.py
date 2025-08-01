"""
认证模块数据模型
定义用户、权限、会话等相关数据结构
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import bcrypt
import json


class PermissionLevel(Enum):
    """权限级别枚举"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class User:
    """用户数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str = ""
    password_hash: str = ""
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    login_count: int = 0
    
    def set_password(self, password: str) -> None:
        """设置密码（加密存储）"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        self.updated_at = datetime.now()
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def update_login_info(self) -> None:
        """更新登录信息"""
        self.last_login = datetime.now()
        self.login_count += 1
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含敏感信息）"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """从字典创建用户对象"""
        user = cls()
        user.id = data.get('id', str(uuid.uuid4()))
        user.employee_id = data.get('employee_id', '')
        user.password_hash = data.get('password_hash', '')
        user.email = data.get('email')
        user.full_name = data.get('full_name')
        user.is_active = data.get('is_active', True)
        user.is_admin = data.get('is_admin', False)
        
        # 处理日期时间字段
        if data.get('created_at'):
            user.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if data.get('updated_at'):
            user.updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        if data.get('last_login'):
            user.last_login = datetime.fromisoformat(data['last_login'].replace('Z', '+00:00'))
        
        user.login_count = data.get('login_count', 0)
        return user


@dataclass
class AllowedEmployee:
    """允许注册的工号数据模型"""
    employee_id: str = ""
    added_by: str = ""
    added_at: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'employee_id': self.employee_id,
            'added_by': self.added_by,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllowedEmployee':
        """从字典创建对象"""
        allowed_employee = cls()
        allowed_employee.employee_id = data.get('employee_id', '')
        allowed_employee.added_by = data.get('added_by', '')
        allowed_employee.description = data.get('description')
        
        if data.get('added_at'):
            allowed_employee.added_at = datetime.fromisoformat(data['added_at'].replace('Z', '+00:00'))
        
        return allowed_employee


@dataclass
class UserPermission:
    """用户权限数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    schema_name: str = ""
    permission_level: PermissionLevel = PermissionLevel.READ
    granted_by: str = ""
    granted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    def is_expired(self) -> bool:
        """检查权限是否已过期"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查权限是否有效"""
        return self.is_active and not self.is_expired()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'schema_name': self.schema_name,
            'permission_level': self.permission_level.value,
            'granted_by': self.granted_by,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPermission':
        """从字典创建对象"""
        permission = cls()
        permission.id = data.get('id', str(uuid.uuid4()))
        permission.user_id = data.get('user_id', '')
        permission.schema_name = data.get('schema_name', '')
        permission.permission_level = PermissionLevel(data.get('permission_level', 'read'))
        permission.granted_by = data.get('granted_by', '')
        permission.is_active = data.get('is_active', True)
        
        # 处理日期时间字段
        if data.get('granted_at'):
            permission.granted_at = datetime.fromisoformat(data['granted_at'].replace('Z', '+00:00'))
        if data.get('expires_at'):
            permission.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        
        return permission


@dataclass
class UserSession:
    """用户会话数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    session_token: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=24))
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查会话是否有效"""
        return self.is_active and not self.is_expired()
    
    def refresh(self, timeout_hours: int = 24) -> None:
        """刷新会话"""
        self.expires_at = datetime.now() + timedelta(hours=timeout_hours)
        self.last_activity = datetime.now()
    
    def update_activity(self) -> None:
        """更新最后活动时间"""
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """从字典创建对象"""
        session = cls()
        session.id = data.get('id', str(uuid.uuid4()))
        session.user_id = data.get('user_id', '')
        session.session_token = data.get('session_token', '')
        session.ip_address = data.get('ip_address')
        session.user_agent = data.get('user_agent')
        session.is_active = data.get('is_active', True)
        
        # 处理日期时间字段
        if data.get('created_at'):
            session.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if data.get('expires_at'):
            session.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        if data.get('last_activity'):
            session.last_activity = datetime.fromisoformat(data['last_activity'].replace('Z', '+00:00'))
        
        return session


@dataclass
class AuditLog:
    """审计日志数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    action: str = ""
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditLog':
        """从字典创建对象"""
        log = cls()
        log.id = data.get('id', str(uuid.uuid4()))
        log.user_id = data.get('user_id')
        log.action = data.get('action', '')
        log.resource_type = data.get('resource_type')
        log.resource_id = data.get('resource_id')
        log.details = data.get('details', {})
        log.ip_address = data.get('ip_address')
        log.user_agent = data.get('user_agent')
        
        if data.get('created_at'):
            log.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        
        return log


# 数据验证函数
def validate_employee_id(employee_id: str) -> bool:
    """验证工号格式"""
    if not employee_id:
        return False
    
    # 基本格式验证：只允许字母数字和连字符
    import re
    pattern = r'^[A-Za-z0-9\-_]{3,20}$'
    return bool(re.match(pattern, employee_id))


def validate_password_strength(password: str) -> Dict[str, Any]:
    """验证密码强度"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    if len(password) < 8:
        result['valid'] = False
        result['errors'].append('密码长度至少8位')
    
    if len(password) > 128:
        result['valid'] = False
        result['errors'].append('密码长度不能超过128位')
    
    # 检查是否包含数字
    if not any(c.isdigit() for c in password):
        result['warnings'].append('建议密码包含数字')
    
    # 检查是否包含大写字母
    if not any(c.isupper() for c in password):
        result['warnings'].append('建议密码包含大写字母')
    
    # 检查是否包含小写字母
    if not any(c.islower() for c in password):
        result['warnings'].append('建议密码包含小写字母')
    
    # 检查是否包含特殊字符
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        result['warnings'].append('建议密码包含特殊字符')
    
    return result


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    if not email:
        return True  # 邮箱是可选的
    
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))