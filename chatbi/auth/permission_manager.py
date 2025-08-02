"""
权限管理器
实现用户权限的分配、检查和管理功能
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .models import UserPermission, PermissionLevel
from .database import AuthDatabase
from .config import get_permission_config


@dataclass
class PermissionResult:
    """权限操作结果"""
    success: bool
    message: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class PermissionManager:
    """权限管理器类"""
    
    def __init__(self, database: AuthDatabase):
        """
        初始化权限管理器
        
        Args:
            database: 认证数据库实例
        """
        self.database = database
        self.permission_config = get_permission_config()
        self.logger = logging.getLogger(__name__)
        self._permission_cache = {}  # 简单的内存缓存
    
    def assign_schema_permission(self, user_id: str, schema_name: str, 
                               permission_level: str, granted_by: str,
                               expires_at: datetime = None) -> PermissionResult:
        """
        分配schema权限给用户
        
        Args:
            user_id: 用户ID
            schema_name: schema名称
            permission_level: 权限级别 (read/write/admin)
            granted_by: 授权者用户ID
            expires_at: 过期时间（可选）
            
        Returns:
            PermissionResult: 操作结果
        """
        try:
            self.logger.info(f"开始分配权限: {user_id} - {schema_name} - {permission_level}")
            
            # 1. 验证输入参数
            validation_result = self._validate_permission_input(
                user_id, schema_name, permission_level, granted_by
            )
            if not validation_result.success:
                return validation_result
            
            # 2. 检查是否已存在权限
            existing_permission = self._get_user_schema_permission(user_id, schema_name)
            if existing_permission and existing_permission.is_valid():
                # 更新现有权限
                return self._update_existing_permission(
                    existing_permission, permission_level, granted_by, expires_at
                )
            
            # 3. 创建新权限
            permission = UserPermission(
                user_id=user_id,
                schema_name=schema_name,
                permission_level=PermissionLevel(permission_level),
                granted_by=granted_by,
                granted_at=datetime.now(),
                expires_at=expires_at,
                is_active=True
            )
            
            # 4. 保存到数据库
            if self.database.create_user_permission(permission):
                self.logger.info(f"权限分配成功: {user_id} - {schema_name}")
                
                # 清除缓存
                self._clear_user_permission_cache(user_id)
                
                # 记录审计日志
                self._log_permission_action(
                    user_id=granted_by,
                    action="permission_assigned",
                    resource_id=f"{user_id}:{schema_name}",
                    details={
                        "target_user_id": user_id,
                        "schema_name": schema_name,
                        "permission_level": permission_level,
                        "expires_at": expires_at.isoformat() if expires_at else None,
                        "assigned_time": datetime.now().isoformat()
                    }
                )
                
                return PermissionResult(
                    success=True,
                    message="权限分配成功"
                )
            else:
                self.logger.error(f"权限分配失败，数据库保存错误: {user_id} - {schema_name}")
                return PermissionResult(
                    success=False,
                    message="权限分配失败，请稍后重试",
                    errors=["database_error"]
                )
                
        except Exception as e:
            self.logger.error(f"分配权限异常: {user_id} - {schema_name} - {str(e)}")
            return PermissionResult(
                success=False,
                message="分配权限过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def revoke_schema_permission(self, user_id: str, schema_name: str, 
                               revoked_by: str) -> PermissionResult:
        """
        撤销用户的schema权限
        
        Args:
            user_id: 用户ID
            schema_name: schema名称
            revoked_by: 撤销者用户ID
            
        Returns:
            PermissionResult: 操作结果
        """
        try:
            self.logger.info(f"开始撤销权限: {user_id} - {schema_name}")
            
            # 1. 验证输入参数
            if not all([user_id, schema_name, revoked_by]):
                return PermissionResult(
                    success=False,
                    message="用户ID、schema名称和撤销者ID不能为空",
                    errors=["invalid_input"]
                )
            
            # 2. 检查权限是否存在
            existing_permission = self._get_user_schema_permission(user_id, schema_name)
            if not existing_permission or not existing_permission.is_active:
                return PermissionResult(
                    success=False,
                    message="用户没有该schema的权限",
                    errors=["permission_not_found"]
                )
            
            # 3. 撤销权限（软删除）
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE user_permissions 
            SET is_active = 0
            WHERE user_id = {placeholder} AND schema_name = {placeholder} AND is_active = 1
            """
            
            affected = self.database.execute_update(sql, (user_id, schema_name))
            
            if affected > 0:
                self.logger.info(f"权限撤销成功: {user_id} - {schema_name}")
                
                # 清除缓存
                self._clear_user_permission_cache(user_id)
                
                # 记录审计日志
                self._log_permission_action(
                    user_id=revoked_by,
                    action="permission_revoked",
                    resource_id=f"{user_id}:{schema_name}",
                    details={
                        "target_user_id": user_id,
                        "schema_name": schema_name,
                        "revoked_time": datetime.now().isoformat()
                    }
                )
                
                return PermissionResult(
                    success=True,
                    message="权限撤销成功"
                )
            else:
                return PermissionResult(
                    success=False,
                    message="权限撤销失败，权限可能不存在",
                    errors=["no_records_affected"]
                )
                
        except Exception as e:
            self.logger.error(f"撤销权限异常: {user_id} - {schema_name} - {str(e)}")
            return PermissionResult(
                success=False,
                message="撤销权限过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def check_schema_access(self, user_id: str, schema_name: str, 
                          required_level: str = "read") -> bool:
        """
        检查用户是否有schema访问权限
        
        Args:
            user_id: 用户ID
            schema_name: schema名称
            required_level: 所需权限级别
            
        Returns:
            bool: 是否有权限
        """
        try:
            # 1. 检查缓存
            cache_key = f"{user_id}:{schema_name}:{required_level}"
            if self.permission_config.permission_cache_enabled:
                cached_result = self._permission_cache.get(cache_key)
                if cached_result is not None:
                    cache_time, result = cached_result
                    if (datetime.now() - cache_time).seconds < self.permission_config.permission_cache_ttl:
                        return result
            
            # 2. 检查是否为公共schema
            if self.permission_config.is_public_schema(schema_name):
                result = True
            else:
                # 3. 检查用户权限
                result = self._check_user_permission(user_id, schema_name, required_level)
            
            # 4. 缓存结果
            if self.permission_config.permission_cache_enabled:
                self._permission_cache[cache_key] = (datetime.now(), result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"检查权限异常: {user_id} - {schema_name} - {str(e)}")
            return False
    
    def get_user_permissions(self, user_id: str) -> List[UserPermission]:
        """
        获取用户的所有权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[UserPermission]: 用户权限列表
        """
        try:
            self.logger.info(f"获取用户权限: {user_id}")
            permissions = self.database.get_user_permissions(user_id)
            self.logger.info(f"从数据库获取到 {len(permissions)} 条权限记录")
            return permissions
        except Exception as e:
            self.logger.error(f"获取用户权限异常: {user_id} - {str(e)}")
            return []
    
    def get_schema_permissions(self, schema_name: str) -> List[UserPermission]:
        """
        获取schema的所有权限分配
        
        Args:
            schema_name: schema名称
            
        Returns:
            List[UserPermission]: 权限列表
        """
        try:
            placeholder = self.database._get_placeholder()
            sql = f"""
            SELECT * FROM user_permissions 
            WHERE schema_name = {placeholder} AND is_active = 1
            ORDER BY granted_at DESC
            """
            
            results = self.database.execute_query(sql, (schema_name,))
            return [UserPermission.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"获取schema权限异常: {schema_name} - {str(e)}")
            return []
    
    def cleanup_expired_permissions(self) -> int:
        """
        清理过期权限
        
        Returns:
            int: 清理的权限数量
        """
        try:
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE user_permissions 
            SET is_active = 0 
            WHERE expires_at < {placeholder} AND is_active = 1
            """
            
            affected = self.database.execute_update(sql, (datetime.now(),))
            
            if affected > 0:
                self.logger.info(f"清理过期权限: {affected} 个")
                # 清除所有缓存
                self._permission_cache.clear()
            
            return affected
            
        except Exception as e:
            self.logger.error(f"清理过期权限异常: {str(e)}")
            return 0
    
    def extend_permission_expiry(self, user_id: str, schema_name: str, 
                               new_expiry: datetime, extended_by: str) -> PermissionResult:
        """
        延长权限过期时间
        
        Args:
            user_id: 用户ID
            schema_name: schema名称
            new_expiry: 新的过期时间
            extended_by: 延长者用户ID
            
        Returns:
            PermissionResult: 操作结果
        """
        try:
            self.logger.info(f"开始延长权限过期时间: {user_id} - {schema_name}")
            
            # 1. 检查权限是否存在
            existing_permission = self._get_user_schema_permission(user_id, schema_name)
            if not existing_permission or not existing_permission.is_active:
                return PermissionResult(
                    success=False,
                    message="用户没有该schema的权限",
                    errors=["permission_not_found"]
                )
            
            # 2. 更新过期时间
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE user_permissions 
            SET expires_at = {placeholder}
            WHERE user_id = {placeholder} AND schema_name = {placeholder} AND is_active = 1
            """
            
            affected = self.database.execute_update(sql, (new_expiry, user_id, schema_name))
            
            if affected > 0:
                self.logger.info(f"权限过期时间延长成功: {user_id} - {schema_name}")
                
                # 清除缓存
                self._clear_user_permission_cache(user_id)
                
                # 记录审计日志
                self._log_permission_action(
                    user_id=extended_by,
                    action="permission_expiry_extended",
                    resource_id=f"{user_id}:{schema_name}",
                    details={
                        "target_user_id": user_id,
                        "schema_name": schema_name,
                        "new_expiry": new_expiry.isoformat(),
                        "extended_time": datetime.now().isoformat()
                    }
                )
                
                return PermissionResult(
                    success=True,
                    message="权限过期时间延长成功"
                )
            else:
                return PermissionResult(
                    success=False,
                    message="延长失败，权限可能不存在",
                    errors=["no_records_affected"]
                )
                
        except Exception as e:
            self.logger.error(f"延长权限过期时间异常: {user_id} - {schema_name} - {str(e)}")
            return PermissionResult(
                success=False,
                message="延长过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def _get_user_schema_permission(self, user_id: str, schema_name: str) -> Optional[UserPermission]:
        """获取用户特定schema的权限"""
        try:
            placeholder = self.database._get_placeholder()
            sql = f"""
            SELECT * FROM user_permissions 
            WHERE user_id = {placeholder} AND schema_name = {placeholder}
            ORDER BY granted_at DESC 
            LIMIT 1
            """
            
            results = self.database.execute_query(sql, (user_id, schema_name))
            if results:
                return UserPermission.from_dict(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"获取用户schema权限异常: {user_id} - {schema_name} - {str(e)}")
            return None
    
    def _update_existing_permission(self, permission: UserPermission, new_level: str,
                                  granted_by: str, expires_at: datetime = None) -> PermissionResult:
        """更新现有权限"""
        try:
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE user_permissions 
            SET permission_level = {placeholder}, granted_by = {placeholder}, 
                granted_at = {placeholder}, expires_at = {placeholder}, is_active = 1
            WHERE id = {placeholder}
            """
            
            params = (
                new_level, granted_by, datetime.now(), expires_at, permission.id
            )
            
            affected = self.database.execute_update(sql, params)
            
            if affected > 0:
                return PermissionResult(success=True, message="权限更新成功")
            else:
                return PermissionResult(
                    success=False, 
                    message="权限更新失败", 
                    errors=["update_failed"]
                )
                
        except Exception as e:
            self.logger.error(f"更新权限异常: {str(e)}")
            return PermissionResult(
                success=False,
                message="更新权限过程中发生错误",
                errors=["internal_error"]
            )
    
    def _check_user_permission(self, user_id: str, schema_name: str, required_level: str) -> bool:
        """检查用户权限"""
        try:
            # 1. 获取用户信息（检查是否为管理员）
            user = self.database.get_user_by_id(user_id)
            if not user or not user.is_active:
                return False
            
            # 2. 管理员权限检查
            if user.is_admin and self.permission_config.inherit_admin_permissions:
                if self.permission_config.is_admin_schema(schema_name):
                    return True
            
            # 3. 检查具体权限
            permission = self._get_user_schema_permission(user_id, schema_name)
            if not permission or not permission.is_valid():
                return False
            
            # 4. 权限级别检查
            permission_levels = {
                "read": 1,
                "write": 2,
                "admin": 3
            }
            
            user_level = permission_levels.get(permission.permission_level.value, 0)
            required_level_num = permission_levels.get(required_level, 1)
            
            return user_level >= required_level_num
            
        except Exception as e:
            self.logger.error(f"检查用户权限异常: {str(e)}")
            return False
    
    def _validate_permission_input(self, user_id: str, schema_name: str, 
                                 permission_level: str, granted_by: str) -> PermissionResult:
        """验证权限输入参数"""
        errors = []
        
        if not user_id:
            errors.append("用户ID不能为空")
        
        if not schema_name:
            errors.append("Schema名称不能为空")
        
        if not permission_level:
            errors.append("权限级别不能为空")
        elif permission_level not in ["read", "write", "admin"]:
            errors.append("权限级别必须是read、write或admin之一")
        
        if not granted_by:
            errors.append("授权者ID不能为空")
        
        if errors:
            return PermissionResult(
                success=False,
                message="输入参数验证失败",
                errors=errors
            )
        
        return PermissionResult(success=True)
    
    def _clear_user_permission_cache(self, user_id: str):
        """清除用户权限缓存"""
        if not self.permission_config.permission_cache_enabled:
            return
        
        keys_to_remove = [key for key in self._permission_cache.keys() 
                         if key.startswith(f"{user_id}:")]
        
        for key in keys_to_remove:
            del self._permission_cache[key]
    
    def _log_permission_action(self, user_id: str, action: str, resource_id: str = None,
                             details: Dict[str, Any] = None):
        """记录权限操作审计日志"""
        try:
            from .models import AuditLog
            
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="permission",
                resource_id=resource_id,
                details=details or {},
                created_at=datetime.now()
            )
            
            self.database.create_audit_log(audit_log)
        except Exception as e:
            # 审计日志失败不应该影响主要功能
            self.logger.warning(f"记录审计日志失败: {str(e)}")