"""
认证中间件
提供Web框架的认证中间件功能
"""

import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime

from .models import User, UserSession
from .database import AuthDatabase
from .session_manager import SessionManager


class AuthenticationMiddleware:
    """认证中间件类"""
    
    def __init__(self, database: AuthDatabase):
        """
        初始化认证中间件
        
        Args:
            database: 认证数据库实例
        """
        self.database = database
        self.session_manager = SessionManager(database)
        self.logger = logging.getLogger(__name__)
    
    def authenticate_request(self, request_headers: Dict[str, str], 
                           request_info: Dict[str, Any] = None) -> Optional[User]:
        """
        认证HTTP请求
        
        Args:
            request_headers: 请求头字典
            request_info: 请求信息（IP地址、用户代理等）
            
        Returns:
            User: 认证成功的用户对象，失败返回None
        """
        try:
            # 1. 从请求头获取会话令牌
            session_token = self._extract_session_token(request_headers)
            if not session_token:
                return None
            
            # 2. 验证会话
            session_result = self.session_manager.validate_session(session_token)
            if not session_result.success:
                return None
            
            session = session_result.session
            
            # 3. 获取用户信息
            user = self.database.get_user_by_id(session.user_id)
            if not user or not user.is_active:
                # 用户不存在或已被禁用，销毁会话
                self.session_manager.destroy_session(session_token)
                return None
            
            # 4. 记录访问日志（可选）
            if request_info:
                self._log_access(user.id, request_info)
            
            return user
            
        except Exception as e:
            self.logger.error(f"认证请求异常: {str(e)}")
            return None
    
    def require_authentication(self, func: Callable) -> Callable:
        """
        装饰器：要求认证
        
        Args:
            func: 被装饰的函数
            
        Returns:
            Callable: 装饰后的函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 这里需要根据具体的Web框架实现
            # 以下是一个通用的示例
            
            # 假设第一个参数是request对象
            if args and hasattr(args[0], 'headers'):
                request = args[0]
                headers = dict(request.headers)
                
                user = self.authenticate_request(headers)
                if not user:
                    # 返回未认证错误
                    return self._create_auth_error_response()
                
                # 将用户信息添加到请求中
                request.user = user
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def require_permission(self, schema_name: str, permission_level: str = "read") -> Callable:
        """
        装饰器：要求特定权限
        
        Args:
            schema_name: Schema名称
            permission_level: 权限级别
            
        Returns:
            Callable: 装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 首先进行认证
                if args and hasattr(args[0], 'headers'):
                    request = args[0]
                    
                    # 如果还没有认证，先进行认证
                    if not hasattr(request, 'user'):
                        headers = dict(request.headers)
                        user = self.authenticate_request(headers)
                        if not user:
                            return self._create_auth_error_response()
                        request.user = user
                    
                    # 检查权限
                    from .permission_manager import PermissionManager
                    perm_manager = PermissionManager(self.database)
                    
                    if not perm_manager.check_schema_access(
                        request.user.id, schema_name, permission_level
                    ):
                        return self._create_permission_error_response()
                
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_admin(self, func: Callable) -> Callable:
        """
        装饰器：要求管理员权限
        
        Args:
            func: 被装饰的函数
            
        Returns:
            Callable: 装饰后的函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            if args and hasattr(args[0], 'headers'):
                request = args[0]
                
                # 如果还没有认证，先进行认证
                if not hasattr(request, 'user'):
                    headers = dict(request.headers)
                    user = self.authenticate_request(headers)
                    if not user:
                        return self._create_auth_error_response()
                    request.user = user
                
                # 检查管理员权限
                if not request.user.is_admin:
                    return self._create_permission_error_response("需要管理员权限")
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def _extract_session_token(self, headers: Dict[str, str]) -> Optional[str]:
        """
        从请求头提取会话令牌
        
        Args:
            headers: 请求头字典
            
        Returns:
            str: 会话令牌，如果不存在返回None
        """
        # 1. 尝试从Authorization头获取Bearer token
        auth_header = headers.get('Authorization') or headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header[7:]  # 移除 "Bearer " 前缀
        
        # 2. 尝试从X-Session-Token头获取
        session_token = headers.get('X-Session-Token') or headers.get('x-session-token')
        if session_token:
            return session_token
        
        # 3. 尝试从Cookie获取（如果有的话）
        cookie_header = headers.get('Cookie') or headers.get('cookie')
        if cookie_header:
            # 简单的Cookie解析
            for cookie in cookie_header.split(';'):
                cookie = cookie.strip()
                if cookie.startswith('session_token='):
                    return cookie[14:]  # 移除 "session_token=" 前缀
        
        return None
    
    def _create_auth_error_response(self) -> Dict[str, Any]:
        """创建认证错误响应"""
        return {
            'error': 'authentication_required',
            'message': '需要认证才能访问此资源',
            'status_code': 401
        }
    
    def _create_permission_error_response(self, message: str = "权限不足") -> Dict[str, Any]:
        """创建权限错误响应"""
        return {
            'error': 'permission_denied',
            'message': message,
            'status_code': 403
        }
    
    def _log_access(self, user_id: str, request_info: Dict[str, Any]):
        """记录访问日志"""
        try:
            from .models import AuditLog
            
            audit_log = AuditLog(
                user_id=user_id,
                action="api_access",
                resource_type="api",
                details={
                    "method": request_info.get("method"),
                    "path": request_info.get("path"),
                    "ip_address": request_info.get("ip_address"),
                    "user_agent": request_info.get("user_agent"),
                    "access_time": datetime.now().isoformat()
                },
                ip_address=request_info.get("ip_address"),
                user_agent=request_info.get("user_agent"),
                created_at=datetime.now()
            )
            
            self.database.create_audit_log(audit_log)
        except Exception as e:
            # 访问日志失败不应该影响主要功能
            self.logger.warning(f"记录访问日志失败: {str(e)}")


# 便利函数，用于快速创建中间件实例
def create_auth_middleware(database_config) -> AuthenticationMiddleware:
    """
    创建认证中间件实例
    
    Args:
        database_config: 数据库配置
        
    Returns:
        AuthenticationMiddleware: 中间件实例
    """
    database = AuthDatabase(database_config)
    return AuthenticationMiddleware(database)


# Flask集成示例
def create_flask_auth_middleware(app, database_config):
    """
    为Flask应用创建认证中间件
    
    Args:
        app: Flask应用实例
        database_config: 数据库配置
    """
    try:
        from flask import request, jsonify, g
        
        middleware = create_auth_middleware(database_config)
        
        @app.before_request
        def authenticate_request():
            """在每个请求前进行认证"""
            # 跳过不需要认证的路径
            skip_paths = ['/login', '/register', '/health', '/static']
            if any(request.path.startswith(path) for path in skip_paths):
                return
            
            headers = dict(request.headers)
            request_info = {
                "method": request.method,
                "path": request.path,
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get('User-Agent')
            }
            
            user = middleware.authenticate_request(headers, request_info)
            if user:
                g.current_user = user
            else:
                return jsonify({
                    'error': 'authentication_required',
                    'message': '需要认证才能访问此资源'
                }), 401
        
        return middleware
        
    except ImportError:
        # Flask未安装
        return None


# FastAPI集成示例
def create_fastapi_auth_middleware(database_config):
    """
    为FastAPI应用创建认证中间件
    
    Args:
        database_config: 数据库配置
        
    Returns:
        认证依赖函数
    """
    try:
        from fastapi import Depends, HTTPException, Request
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        
        middleware = create_auth_middleware(database_config)
        security = HTTPBearer()
        
        async def get_current_user(
            request: Request,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ) -> User:
            """获取当前认证用户"""
            headers = dict(request.headers)
            request_info = {
                "method": request.method,
                "path": str(request.url.path),
                "ip_address": request.client.host,
                "user_agent": request.headers.get('user-agent')
            }
            
            user = middleware.authenticate_request(headers, request_info)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="需要认证才能访问此资源",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return user
        
        return get_current_user
        
    except ImportError:
        # FastAPI未安装
        return None