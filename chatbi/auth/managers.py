"""
认证模块管理器集合
导入和导出所有管理器类
"""

from .user_manager import UserManager, UserRegistrationResult, AuthenticationResult
from .allowed_employee_manager import AllowedEmployeeManager, AllowedEmployeeResult
from .permission_manager import PermissionManager, PermissionResult
from .session_manager import SessionManager, SessionResult

__all__ = [
    'UserManager', 'UserRegistrationResult', 'AuthenticationResult',
    'AllowedEmployeeManager', 'AllowedEmployeeResult',
    'PermissionManager', 'PermissionResult',
    'SessionManager', 'SessionResult'
]