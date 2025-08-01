"""
权限管理界面
使用Gradio创建管理员权限配置界面
"""

import gradio as gr
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from .user_manager import UserManager
from .permission_manager import PermissionManager
from .allowed_employee_manager import AllowedEmployeeManager
from .session_manager import SessionManager
from .database import AuthDatabase
from .models import User, UserPermission, PermissionLevel

logger = logging.getLogger(__name__)


class AdminInterface:
    """管理员权限管理界面"""
    
    def __init__(self):
        """初始化管理界面"""
        self.user_manager = UserManager()
        self.permission_manager = PermissionManager()
        self.allowed_employee_manager = AllowedEmployeeManager()
        self.session_manager = SessionManager()
        self.auth_database = AuthDatabase()
        
        # 当前登录的管理员信息
        self.current_admin = None
        
        logger.info("管理员权限管理界面初始化完成")
    
    def authenticate_admin(self, employee_id: str, password: str) -> Tuple[bool, str]:
        """
        管理员身份验证
        
        Args:
            employee_id: 工号
            password: 密码
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            # 验证用户身份
            auth_result = self.user_manager.authenticate_user(employee_id, password)
            
            if not auth_result.success:
                return False, auth_result.message
            
            # 检查是否为管理员
            user = auth_result.user
            if not user or not user.is_admin:
                return False, "您没有管理员权限"
            
            self.current_admin = user
            return True, f"欢迎，管理员 {user.employee_id}"
            
        except Exception as e:
            logger.error(f"管理员身份验证异常: {str(e)}")
            return False, f"身份验证失败: {str(e)}"
    
    def get_users_list(self) -> pd.DataFrame:
        """
        获取用户列表
        
        Returns:
            pd.DataFrame: 用户列表数据
        """
        try:
            users = self.auth_database.get_all_users()
            
            users_data = []
            for user in users:
                # 获取用户权限
                permissions = self.permission_manager.get_user_permissions(user.id)
                schema_count = len([p for p in permissions if p.is_valid()])
                
                users_data.append({
                    "用户ID": user.id,
                    "工号": user.employee_id,
                    "邮箱": user.email or "未设置",
                    "姓名": user.full_name or "未设置",
                    "状态": "活跃" if user.is_active else "禁用",
                    "管理员": "是" if user.is_admin else "否",
                    "权限数量": schema_count,
                    "注册时间": user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "未知",
                    "最后登录": user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "从未登录"
                })
            
            return pd.DataFrame(users_data)
            
        except Exception as e:
            logger.error(f"获取用户列表异常: {str(e)}")
            return pd.DataFrame()
    
    def get_user_permissions(self, user_id: str) -> pd.DataFrame:
        """
        获取用户权限列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            pd.DataFrame: 用户权限数据
        """
        try:
            permissions = self.permission_manager.get_user_permissions(user_id)
            
            permissions_data = []
            for perm in permissions:
                permissions_data.append({
                    "权限ID": perm.id,
                    "Schema名称": perm.schema_name,
                    "权限级别": perm.permission_level.value,
                    "授权人": perm.granted_by,
                    "授权时间": perm.granted_at.strftime("%Y-%m-%d %H:%M"),
                    "过期时间": perm.expires_at.strftime("%Y-%m-%d %H:%M") if perm.expires_at else "永不过期",
                    "状态": "有效" if perm.is_valid() else "无效"
                })
            
            return pd.DataFrame(permissions_data)
            
        except Exception as e:
            logger.error(f"获取用户权限异常: {str(e)}")
            return pd.DataFrame()
    
    def assign_permission(self, user_id: str, schema_name: str, 
                         permission_level: str) -> Tuple[bool, str]:
        """
        分配用户权限
        
        Args:
            user_id: 用户ID
            schema_name: Schema名称
            permission_level: 权限级别
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if not self.current_admin:
                return False, "请先登录管理员账户"
            
            # 转换权限级别
            level_map = {
                "读取": PermissionLevel.READ,
                "写入": PermissionLevel.WRITE,
                "管理": PermissionLevel.ADMIN
            }
            
            if permission_level not in level_map:
                return False, "无效的权限级别"
            
            # 分配权限
            result = self.permission_manager.assign_schema_permission(
                user_id=user_id,
                schema_name=schema_name,
                permission_level=level_map[permission_level],
                granted_by=self.current_admin.id
            )
            
            if result.success:
                return True, f"成功为用户分配 {schema_name} 的 {permission_level} 权限"
            else:
                return False, result.message
                
        except Exception as e:
            logger.error(f"分配权限异常: {str(e)}")
            return False, f"分配权限失败: {str(e)}"
    
    def revoke_permission(self, permission_id: str) -> Tuple[bool, str]:
        """
        撤销用户权限
        
        Args:
            permission_id: 权限ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if not self.current_admin:
                return False, "请先登录管理员账户"
            
            # 撤销权限
            result = self.permission_manager.revoke_permission(permission_id)
            
            if result.success:
                return True, "权限撤销成功"
            else:
                return False, result.message
                
        except Exception as e:
            logger.error(f"撤销权限异常: {str(e)}")
            return False, f"撤销权限失败: {str(e)}"
    
    def get_allowed_employees(self) -> pd.DataFrame:
        """
        获取允许注册的工号列表
        
        Returns:
            pd.DataFrame: 允许注册的工号数据
        """
        try:
            allowed_employees = self.allowed_employee_manager.get_all_allowed_employees()
            
            employees_data = []
            for emp in allowed_employees:
                employees_data.append({
                    "工号": emp.employee_id,
                    "添加人": emp.added_by,
                    "添加时间": emp.added_at.strftime("%Y-%m-%d %H:%M") if emp.added_at else "未知",
                    "描述": emp.description or "无描述"
                })
            
            return pd.DataFrame(employees_data)
            
        except Exception as e:
            logger.error(f"获取允许工号列表异常: {str(e)}")
            return pd.DataFrame()
    
    def add_allowed_employee(self, employee_id: str, description: str = "") -> Tuple[bool, str]:
        """
        添加允许注册的工号
        
        Args:
            employee_id: 工号
            description: 描述
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if not self.current_admin:
                return False, "请先登录管理员账户"
            
            if not employee_id.strip():
                return False, "工号不能为空"
            
            # 添加允许的工号
            result = self.allowed_employee_manager.add_allowed_employee(
                employee_id=employee_id.strip(),
                added_by=self.current_admin.id,
                description=description.strip() if description else None
            )
            
            if result.success:
                return True, f"成功添加工号 {employee_id} 到允许注册列表"
            else:
                return False, result.message
                
        except Exception as e:
            logger.error(f"添加允许工号异常: {str(e)}")
            return False, f"添加工号失败: {str(e)}"
    
    def remove_allowed_employee(self, employee_id: str) -> Tuple[bool, str]:
        """
        移除允许注册的工号
        
        Args:
            employee_id: 工号
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if not self.current_admin:
                return False, "请先登录管理员账户"
            
            # 移除允许的工号
            result = self.allowed_employee_manager.remove_allowed_employee(
                employee_id=employee_id,
                removed_by=self.current_admin.id
            )
            
            if result.success:
                return True, f"成功从允许注册列表中移除工号 {employee_id}"
            else:
                return False, result.message
                
        except Exception as e:
            logger.error(f"移除允许工号异常: {str(e)}")
            return False, f"移除工号失败: {str(e)}"
    
    def toggle_user_status(self, user_id: str) -> Tuple[bool, str]:
        """
        切换用户状态（启用/禁用）
        
        Args:
            user_id: 用户ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if not self.current_admin:
                return False, "请先登录管理员账户"
            
            # 获取用户信息
            user = self.auth_database.get_user_by_id(user_id)
            if not user:
                return False, "用户不存在"
            
            # 不能禁用自己
            if user.id == self.current_admin.id:
                return False, "不能禁用自己的账户"
            
            # 切换状态
            new_status = not user.is_active
            success = self.auth_database.update_user_status(user_id, new_status)
            
            if success:
                status_text = "启用" if new_status else "禁用"
                return True, f"成功{status_text}用户 {user.employee_id}"
            else:
                return False, "更新用户状态失败"
                
        except Exception as e:
            logger.error(f"切换用户状态异常: {str(e)}")
            return False, f"切换用户状态失败: {str(e)}"
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            Dict[str, Any]: 系统统计数据
        """
        try:
            # 用户统计
            all_users = self.auth_database.get_all_users()
            active_users = [u for u in all_users if u.is_active]
            admin_users = [u for u in all_users if u.is_admin]
            
            # 权限统计
            all_permissions = []
            for user in all_users:
                permissions = self.permission_manager.get_user_permissions(user.id)
                all_permissions.extend(permissions)
            
            valid_permissions = [p for p in all_permissions if p.is_valid()]
            
            # 允许工号统计
            allowed_employees = self.allowed_employee_manager.get_all_allowed_employees()
            
            return {
                "总用户数": len(all_users),
                "活跃用户数": len(active_users),
                "管理员数": len(admin_users),
                "总权限数": len(all_permissions),
                "有效权限数": len(valid_permissions),
                "允许注册工号数": len(allowed_employees),
                "统计时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"获取系统统计异常: {str(e)}")
            return {"错误": str(e)}
    
    def search_users(self, keyword: str) -> pd.DataFrame:
        """
        搜索用户
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            pd.DataFrame: 搜索结果
        """
        try:
            if not keyword.strip():
                return self.get_users_list()
            
            all_users = self.auth_database.get_all_users()
            filtered_users = []
            
            keyword = keyword.lower().strip()
            
            for user in all_users:
                # 搜索工号、邮箱、姓名
                if (keyword in user.employee_id.lower() or
                    (user.email and keyword in user.email.lower()) or
                    (user.full_name and keyword in user.full_name.lower())):
                    filtered_users.append(user)
            
            # 转换为DataFrame格式
            users_data = []
            for user in filtered_users:
                permissions = self.permission_manager.get_user_permissions(user.id)
                schema_count = len([p for p in permissions if p.is_valid()])
                
                users_data.append({
                    "用户ID": user.id,
                    "工号": user.employee_id,
                    "邮箱": user.email or "未设置",
                    "姓名": user.full_name or "未设置",
                    "状态": "活跃" if user.is_active else "禁用",
                    "管理员": "是" if user.is_admin else "否",
                    "权限数量": schema_count,
                    "注册时间": user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "未知",
                    "最后登录": user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "从未登录"
                })
            
            return pd.DataFrame(users_data)
            
        except Exception as e:
            logger.error(f"搜索用户异常: {str(e)}")
            return pd.DataFrame()
    
    def get_available_schemas(self) -> List[str]:
        """
        获取可用的Schema列表
        
        Returns:
            List[str]: Schema名称列表
        """
        try:
            from ..database import get_schema_manager
            
            schema_manager = get_schema_manager()
            tables = schema_manager.get_all_tables()
            
            # 提取Schema名称
            schemas = set()
            for table in tables:
                if '.' in table:
                    schema_name = table.split('.')[0]
                    schemas.add(schema_name)
                else:
                    schemas.add('default')  # 默认schema
            
            return sorted(list(schemas))
            
        except Exception as e:
            logger.error(f"获取可用Schema异常: {str(e)}")
            return ["public", "default"]  # 返回默认值