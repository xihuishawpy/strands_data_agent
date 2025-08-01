"""
认证模块
提供用户认证、权限管理和会话管理功能
"""

from .models import User, AllowedEmployee, UserPermission, UserSession, AuditLog
from .user_manager import UserManager, UserRegistrationResult, AuthenticationResult
from .allowed_employee_manager import AllowedEmployeeManager, AllowedEmployeeResult
from .permission_manager import PermissionManager, PermissionResult
from .session_manager import SessionManager, SessionResult
from .middleware import AuthenticationMiddleware
from .config import AuthConfig, PermissionConfig
from .database import AuthDatabase
from .database_permission_filter import DatabasePermissionFilter, UserSpecificDatabaseConnector
from .chatbi_integration import (
    ChatBIAuthIntegration, 
    AuthenticatedOrchestrator, 
    AuthenticatedQueryResult,
    get_integration_adapter,
    require_authentication,
    require_schema_permission
)
from .admin_interface import AdminInterface
from .gradio_admin_app import AdminGradioApp, create_admin_app, launch_admin_app

__all__ = [
    'User', 'AllowedEmployee', 'UserPermission', 'UserSession', 'AuditLog',
    'UserManager', 'UserRegistrationResult', 'AuthenticationResult',
    'AllowedEmployeeManager', 'AllowedEmployeeResult',
    'PermissionManager', 'PermissionResult',
    'SessionManager', 'SessionResult',
    'AuthenticationMiddleware',
    'AuthConfig', 'PermissionConfig',
    'AuthDatabase',
    'DatabasePermissionFilter', 'UserSpecificDatabaseConnector',
    'ChatBIAuthIntegration', 'AuthenticatedOrchestrator', 'AuthenticatedQueryResult',
    'get_integration_adapter', 'require_authentication', 'require_schema_permission',
    'AdminInterface', 'AdminGradioApp', 'create_admin_app', 'launch_admin_app'
]