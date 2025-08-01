"""
用户管理器
实现用户注册、认证和管理功能
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .models import User, validate_employee_id, validate_password_strength, validate_email
from .database import AuthDatabase
from .config import get_auth_config


@dataclass
class UserRegistrationResult:
    """用户注册结果"""
    success: bool
    user_id: Optional[str] = None
    message: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class AuthenticationResult:
    """用户认证结果"""
    success: bool
    user: Optional[User] = None
    message: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class UserManager:
    """用户管理器类"""
    
    def __init__(self, database: AuthDatabase):
        """
        初始化用户管理器
        
        Args:
            database: 认证数据库实例
        """
        self.database = database
        self.auth_config = get_auth_config()
        self.logger = logging.getLogger(__name__)
    
    def register_user(self, employee_id: str, password: str, email: str = None, 
                     full_name: str = None) -> UserRegistrationResult:
        """
        注册新用户
        
        Args:
            employee_id: 工号
            password: 密码
            email: 邮箱（可选）
            full_name: 全名（可选）
            
        Returns:
            UserRegistrationResult: 注册结果
        """
        try:
            self.logger.info(f"开始用户注册: {employee_id}")
            
            # 1. 验证输入参数
            validation_result = self._validate_registration_input(
                employee_id, password, email
            )
            if not validation_result.success:
                return validation_result
            
            # 2. 检查工号是否在允许列表中
            if not self.is_employee_id_allowed(employee_id):
                self.logger.warning(f"工号不在允许列表中: {employee_id}")
                return UserRegistrationResult(
                    success=False,
                    message="该工号不允许注册，请联系管理员",
                    errors=["employee_id_not_allowed"]
                )
            
            # 3. 检查用户是否已存在
            existing_user = self.database.get_user_by_employee_id(employee_id)
            if existing_user:
                self.logger.warning(f"用户已存在: {employee_id}")
                return UserRegistrationResult(
                    success=False,
                    message="该工号已注册，请直接登录",
                    errors=["user_already_exists"]
                )
            
            # 4. 创建用户对象
            user = User(
                id=str(uuid.uuid4()),
                employee_id=employee_id,
                email=email,
                full_name=full_name,
                is_active=True,
                is_admin=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 5. 设置密码（自动加密）
            user.set_password(password)
            
            # 6. 保存到数据库
            if self.database.create_user(user):
                self.logger.info(f"用户注册成功: {employee_id}")
                
                # 记录审计日志
                self._log_user_action(
                    user_id=user.id,
                    action="user_registered",
                    details={
                        "employee_id": employee_id,
                        "email": email,
                        "registration_time": datetime.now().isoformat()
                    }
                )
                
                return UserRegistrationResult(
                    success=True,
                    user_id=user.id,
                    message="用户注册成功"
                )
            else:
                self.logger.error(f"用户注册失败，数据库保存错误: {employee_id}")
                return UserRegistrationResult(
                    success=False,
                    message="注册失败，请稍后重试",
                    errors=["database_error"]
                )
                
        except Exception as e:
            self.logger.error(f"用户注册异常: {employee_id} - {str(e)}")
            return UserRegistrationResult(
                success=False,
                message="注册过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def authenticate_user(self, employee_id: str, password: str) -> AuthenticationResult:
        """
        用户身份验证
        
        Args:
            employee_id: 工号
            password: 密码
            
        Returns:
            AuthenticationResult: 认证结果
        """
        try:
            self.logger.info(f"开始用户认证: {employee_id}")
            
            # 1. 验证输入参数
            if not employee_id or not password:
                return AuthenticationResult(
                    success=False,
                    message="工号和密码不能为空",
                    errors=["invalid_input"]
                )
            
            # 2. 获取用户信息
            user = self.database.get_user_by_employee_id(employee_id)
            if not user:
                self.logger.warning(f"用户不存在: {employee_id}")
                return AuthenticationResult(
                    success=False,
                    message="工号或密码错误",
                    errors=["invalid_credentials"]
                )
            
            # 3. 检查用户状态
            if not user.is_active:
                self.logger.warning(f"用户已被禁用: {employee_id}")
                return AuthenticationResult(
                    success=False,
                    message="账户已被禁用，请联系管理员",
                    errors=["account_disabled"]
                )
            
            # 4. 验证密码
            if not user.check_password(password):
                self.logger.warning(f"密码验证失败: {employee_id}")
                
                # 记录登录失败
                self._log_user_action(
                    user_id=user.id,
                    action="login_failed",
                    details={
                        "employee_id": employee_id,
                        "reason": "invalid_password",
                        "attempt_time": datetime.now().isoformat()
                    }
                )
                
                return AuthenticationResult(
                    success=False,
                    message="工号或密码错误",
                    errors=["invalid_credentials"]
                )
            
            # 5. 更新登录信息
            if self.database.update_user_login_info(user.id):
                user.update_login_info()
            
            # 6. 记录登录成功
            self._log_user_action(
                user_id=user.id,
                action="login_success",
                details={
                    "employee_id": employee_id,
                    "login_time": datetime.now().isoformat(),
                    "login_count": user.login_count
                }
            )
            
            self.logger.info(f"用户认证成功: {employee_id}")
            return AuthenticationResult(
                success=True,
                user=user,
                message="登录成功"
            )
            
        except Exception as e:
            self.logger.error(f"用户认证异常: {employee_id} - {str(e)}")
            return AuthenticationResult(
                success=False,
                message="认证过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def get_user_info(self, user_id: str) -> Optional[User]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            User: 用户对象，如果不存在返回None
        """
        try:
            return self.database.get_user_by_id(user_id)
        except Exception as e:
            self.logger.error(f"获取用户信息异常: {user_id} - {str(e)}")
            return None
    
    def update_user_info(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            updates: 更新的字段字典
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取当前用户信息
            user = self.database.get_user_by_id(user_id)
            if not user:
                self.logger.warning(f"用户不存在: {user_id}")
                return False
            
            # 验证更新字段
            allowed_fields = {'email', 'full_name'}
            update_fields = set(updates.keys())
            
            if not update_fields.issubset(allowed_fields):
                invalid_fields = update_fields - allowed_fields
                self.logger.warning(f"包含不允许更新的字段: {invalid_fields}")
                return False
            
            # 验证邮箱格式
            if 'email' in updates and updates['email']:
                if not validate_email(updates['email']):
                    self.logger.warning(f"邮箱格式无效: {updates['email']}")
                    return False
            
            # 构建更新SQL
            set_clauses = []
            params = []
            placeholder = self.database._get_placeholder()
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = {placeholder}")
                params.append(value)
            
            # 添加更新时间
            set_clauses.append(f"updated_at = {placeholder}")
            params.append(datetime.now())
            params.append(user_id)
            
            sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = {placeholder}"
            
            affected = self.database.execute_update(sql, tuple(params))
            
            if affected > 0:
                # 记录审计日志
                self._log_user_action(
                    user_id=user_id,
                    action="user_info_updated",
                    details={
                        "updated_fields": list(updates.keys()),
                        "update_time": datetime.now().isoformat()
                    }
                )
                
                self.logger.info(f"用户信息更新成功: {user_id}")
                return True
            else:
                self.logger.warning(f"用户信息更新失败，没有记录被更新: {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"更新用户信息异常: {user_id} - {str(e)}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """
        删除用户（软删除，设置为非活跃状态）
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE users 
            SET is_active = 0, updated_at = {placeholder}
            WHERE id = {placeholder}
            """
            
            affected = self.database.execute_update(sql, (datetime.now(), user_id))
            
            if affected > 0:
                # 记录审计日志
                self._log_user_action(
                    user_id=user_id,
                    action="user_deleted",
                    details={
                        "delete_time": datetime.now().isoformat(),
                        "delete_type": "soft_delete"
                    }
                )
                
                self.logger.info(f"用户删除成功: {user_id}")
                return True
            else:
                self.logger.warning(f"用户删除失败，没有记录被更新: {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"删除用户异常: {user_id} - {str(e)}")
            return False
    
    def is_employee_id_allowed(self, employee_id: str) -> bool:
        """
        检查工号是否允许注册
        
        Args:
            employee_id: 工号
            
        Returns:
            bool: 是否允许注册
        """
        try:
            return self.database.is_employee_allowed(employee_id)
        except Exception as e:
            self.logger.error(f"检查工号允许状态异常: {employee_id} - {str(e)}")
            return False
    
    def _validate_registration_input(self, employee_id: str, password: str, 
                                   email: str = None) -> UserRegistrationResult:
        """
        验证注册输入参数
        
        Args:
            employee_id: 工号
            password: 密码
            email: 邮箱
            
        Returns:
            UserRegistrationResult: 验证结果
        """
        errors = []
        
        # 验证工号
        if not employee_id:
            errors.append("工号不能为空")
        elif not validate_employee_id(employee_id):
            errors.append("工号格式无效，只允许字母数字和连字符，长度3-20位")
        
        # 验证密码
        if not password:
            errors.append("密码不能为空")
        else:
            password_validation = validate_password_strength(password)
            if not password_validation['valid']:
                errors.extend(password_validation['errors'])
        
        # 验证邮箱
        if email and not validate_email(email):
            errors.append("邮箱格式无效")
        
        if errors:
            return UserRegistrationResult(
                success=False,
                message="输入参数验证失败",
                errors=errors
            )
        
        return UserRegistrationResult(success=True)
    
    def _log_user_action(self, user_id: str, action: str, details: Dict[str, Any] = None):
        """
        记录用户操作审计日志
        
        Args:
            user_id: 用户ID
            action: 操作类型
            details: 操作详情
        """
        try:
            from .models import AuditLog
            
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="user",
                resource_id=user_id,
                details=details or {},
                created_at=datetime.now()
            )
            
            self.database.create_audit_log(audit_log)
        except Exception as e:
            # 审计日志失败不应该影响主要功能
            self.logger.warning(f"记录审计日志失败: {str(e)}")