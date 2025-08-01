"""
权限管理界面测试
测试管理员权限管理界面的功能
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import pandas as pd
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试日志级别
logging.basicConfig(level=logging.DEBUG)

try:
    from chatbi.auth.admin_interface import AdminInterface
    from chatbi.auth.models import User, UserPermission, PermissionLevel, AllowedEmployee
    from chatbi.auth.user_manager import AuthenticationResult
    from chatbi.auth.permission_manager import PermissionResult
    from chatbi.auth.allowed_employee_manager import AllowedEmployeeResult
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录下运行测试")
    sys.exit(1)


class TestAdminInterface(unittest.TestCase):
    """管理员界面测试类"""
    
    def setUp(self):
        """测试前置设置"""
        # 创建模拟对象
        self.mock_user_manager = Mock()
        self.mock_permission_manager = Mock()
        self.mock_allowed_employee_manager = Mock()
        self.mock_session_manager = Mock()
        self.mock_auth_database = Mock()
        
        # 创建测试用户
        self.admin_user = User(
            id="admin123",
            employee_id="ADMIN001",
            email="admin@test.com",
            full_name="管理员",
            is_active=True,
            is_admin=True,
            created_at=datetime.now()
        )
        
        self.normal_user = User(
            id="user123",
            employee_id="EMP001",
            email="user@test.com",
            full_name="普通用户",
            is_active=True,
            is_admin=False,
            created_at=datetime.now()
        )
        
        # 创建管理界面实例
        with patch('chatbi.auth.admin_interface.UserManager', return_value=self.mock_user_manager), \
             patch('chatbi.auth.admin_interface.PermissionManager', return_value=self.mock_permission_manager), \
             patch('chatbi.auth.admin_interface.AllowedEmployeeManager', return_value=self.mock_allowed_employee_manager), \
             patch('chatbi.auth.admin_interface.SessionManager', return_value=self.mock_session_manager), \
             patch('chatbi.auth.admin_interface.AuthDatabase', return_value=self.mock_auth_database):
            
            self.admin_interface = AdminInterface()
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.admin_interface)
        self.assertIsNone(self.admin_interface.current_admin)
    
    def test_authenticate_admin_success(self):
        """测试管理员身份验证成功"""
        # 设置模拟返回值
        auth_result = AuthenticationResult(
            success=True,
            user=self.admin_user,
            message="认证成功"
        )
        self.mock_user_manager.authenticate_user.return_value = auth_result
        self.mock_auth_database.get_user_by_id.return_value = self.admin_user
        
        # 执行测试
        success, message = self.admin_interface.authenticate_admin("ADMIN001", "password")
        
        # 验证结果
        self.assertTrue(success)
        self.assertIn("欢迎", message)
        self.assertEqual(self.admin_interface.current_admin, self.admin_user)
        self.mock_user_manager.authenticate_user.assert_called_once_with("ADMIN001", "password")
    
    def test_authenticate_admin_not_admin(self):
        """测试非管理员用户认证"""
        # 设置模拟返回值
        auth_result = AuthenticationResult(
            success=True,
            user=self.normal_user,
            message="认证成功"
        )
        self.mock_user_manager.authenticate_user.return_value = auth_result
        self.mock_auth_database.get_user_by_id.return_value = self.normal_user
        
        # 执行测试
        success, message = self.admin_interface.authenticate_admin("EMP001", "password")
        
        # 验证结果
        self.assertFalse(success)
        self.assertIn("没有管理员权限", message)
        self.assertIsNone(self.admin_interface.current_admin)
    
    def test_authenticate_admin_failed(self):
        """测试管理员身份验证失败"""
        # 设置模拟返回值
        auth_result = AuthenticationResult(
            success=False,
            user=None,
            message="密码错误"
        )
        self.mock_user_manager.authenticate_user.return_value = auth_result
        
        # 执行测试
        success, message = self.admin_interface.authenticate_admin("ADMIN001", "wrong_password")
        
        # 验证结果
        self.assertFalse(success)
        self.assertEqual(message, "密码错误")
        self.assertIsNone(self.admin_interface.current_admin)
    
    def test_get_users_list(self):
        """测试获取用户列表"""
        # 设置模拟返回值
        users = [self.admin_user, self.normal_user]
        self.mock_auth_database.get_all_users.return_value = users
        
        # 模拟权限数据
        admin_permissions = [
            UserPermission(
                user_id="admin123",
                schema_name="admin_schema",
                permission_level=PermissionLevel.ADMIN,
                is_active=True
            )
        ]
        user_permissions = [
            UserPermission(
                user_id="user123",
                schema_name="public",
                permission_level=PermissionLevel.READ,
                is_active=True
            )
        ]
        
        def mock_get_permissions(user_id):
            if user_id == "admin123":
                return admin_permissions
            elif user_id == "user123":
                return user_permissions
            return []
        
        self.mock_permission_manager.get_user_permissions.side_effect = mock_get_permissions
        
        # 执行测试
        result = self.admin_interface.get_users_list()
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn("用户ID", result.columns)
        self.assertIn("工号", result.columns)
        self.assertIn("管理员", result.columns)
    
    def test_get_user_permissions(self):
        """测试获取用户权限"""
        # 设置模拟返回值
        permissions = [
            UserPermission(
                id="perm123",
                user_id="user123",
                schema_name="public",
                permission_level=PermissionLevel.READ,
                granted_by="admin123",
                granted_at=datetime.now(),
                is_active=True
            )
        ]
        self.mock_permission_manager.get_user_permissions.return_value = permissions
        
        # 执行测试
        result = self.admin_interface.get_user_permissions("user123")
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertIn("权限ID", result.columns)
        self.assertIn("Schema名称", result.columns)
        self.assertIn("权限级别", result.columns)
    
    def test_assign_permission_success(self):
        """测试成功分配权限"""
        # 设置当前管理员
        self.admin_interface.current_admin = self.admin_user
        
        # 设置模拟返回值
        result = PermissionResult(success=True, message="权限分配成功")
        self.mock_permission_manager.assign_schema_permission.return_value = result
        
        # 执行测试
        success, message = self.admin_interface.assign_permission("user123", "test_schema", "读取")
        
        # 验证结果
        self.assertTrue(success)
        self.assertIn("成功为用户分配", message)
        self.mock_permission_manager.assign_schema_permission.assert_called_once()
    
    def test_assign_permission_not_authenticated(self):
        """测试未认证时分配权限"""
        # 执行测试
        success, message = self.admin_interface.assign_permission("user123", "test_schema", "读取")
        
        # 验证结果
        self.assertFalse(success)
        self.assertIn("请先登录", message)
    
    def test_revoke_permission_success(self):
        """测试成功撤销权限"""
        # 设置当前管理员
        self.admin_interface.current_admin = self.admin_user
        
        # 设置模拟返回值
        result = PermissionResult(success=True, message="权限撤销成功")
        self.mock_permission_manager.revoke_permission.return_value = result
        
        # 执行测试
        success, message = self.admin_interface.revoke_permission("perm123")
        
        # 验证结果
        self.assertTrue(success)
        self.assertEqual(message, "权限撤销成功")
        self.mock_permission_manager.revoke_permission.assert_called_once_with("perm123")
    
    def test_get_allowed_employees(self):
        """测试获取允许工号列表"""
        # 设置模拟返回值
        allowed_employees = [
            AllowedEmployee(
                employee_id="EMP001",
                added_by="admin123",
                added_at=datetime.now(),
                description="测试工号"
            )
        ]
        self.mock_allowed_employee_manager.get_all_allowed_employees.return_value = allowed_employees
        
        # 执行测试
        result = self.admin_interface.get_allowed_employees()
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertIn("工号", result.columns)
        self.assertIn("添加人", result.columns)
    
    def test_add_allowed_employee_success(self):
        """测试成功添加允许工号"""
        # 设置当前管理员
        self.admin_interface.current_admin = self.admin_user
        
        # 设置模拟返回值
        result = AllowedEmployeeResult(success=True, message="工号添加成功")
        self.mock_allowed_employee_manager.add_allowed_employee.return_value = result
        
        # 执行测试
        success, message = self.admin_interface.add_allowed_employee("EMP002", "新员工")
        
        # 验证结果
        self.assertTrue(success)
        self.assertIn("成功添加工号", message)
        self.mock_allowed_employee_manager.add_allowed_employee.assert_called_once()
    
    def test_remove_allowed_employee_success(self):
        """测试成功移除允许工号"""
        # 设置当前管理员
        self.admin_interface.current_admin = self.admin_user
        
        # 设置模拟返回值
        result = AllowedEmployeeResult(success=True, message="工号移除成功")
        self.mock_allowed_employee_manager.remove_allowed_employee.return_value = result
        
        # 执行测试
        success, message = self.admin_interface.remove_allowed_employee("EMP002")
        
        # 验证结果
        self.assertTrue(success)
        self.assertIn("成功从允许注册列表中移除", message)
        self.mock_allowed_employee_manager.remove_allowed_employee.assert_called_once()
    
    def test_toggle_user_status_success(self):
        """测试成功切换用户状态"""
        # 设置当前管理员
        self.admin_interface.current_admin = self.admin_user
        
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.normal_user
        self.mock_auth_database.update_user_status.return_value = True
        
        # 执行测试
        success, message = self.admin_interface.toggle_user_status("user123")
        
        # 验证结果
        self.assertTrue(success)
        self.assertIn("成功禁用用户", message)  # 因为normal_user.is_active=True，所以会被禁用
        self.mock_auth_database.update_user_status.assert_called_once_with("user123", False)
    
    def test_toggle_user_status_self(self):
        """测试不能禁用自己"""
        # 设置当前管理员
        self.admin_interface.current_admin = self.admin_user
        
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.admin_user
        
        # 执行测试
        success, message = self.admin_interface.toggle_user_status("admin123")
        
        # 验证结果
        self.assertFalse(success)
        self.assertIn("不能禁用自己", message)
    
    def test_get_system_stats(self):
        """测试获取系统统计"""
        # 设置模拟返回值
        users = [self.admin_user, self.normal_user]
        self.mock_auth_database.get_all_users.return_value = users
        
        permissions = [
            UserPermission(user_id="user123", schema_name="public", is_active=True)
        ]
        self.mock_permission_manager.get_user_permissions.return_value = permissions
        
        allowed_employees = [
            AllowedEmployee(employee_id="EMP001"),
            AllowedEmployee(employee_id="EMP002")
        ]
        self.mock_allowed_employee_manager.get_all_allowed_employees.return_value = allowed_employees
        
        # 执行测试
        result = self.admin_interface.get_system_stats()
        
        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result["总用户数"], 2)
        self.assertEqual(result["活跃用户数"], 2)
        self.assertEqual(result["管理员数"], 1)
        self.assertEqual(result["允许注册工号数"], 2)
    
    def test_search_users(self):
        """测试搜索用户"""
        # 设置模拟返回值
        users = [self.admin_user, self.normal_user]
        self.mock_auth_database.get_all_users.return_value = users
        self.mock_permission_manager.get_user_permissions.return_value = []
        
        # 执行测试 - 搜索管理员
        result = self.admin_interface.search_users("ADMIN")
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)  # 只应该找到管理员
        self.assertEqual(result.iloc[0]["工号"], "ADMIN001")
    
    def test_get_available_schemas(self):
        """测试获取可用Schema"""
        # 模拟schema管理器
        with patch('chatbi.database.get_schema_manager') as mock_get_manager:
            mock_schema_manager = Mock()
            mock_schema_manager.get_all_tables.return_value = [
                "public.users", "public.orders", "private.secrets", "admin.logs"
            ]
            mock_get_manager.return_value = mock_schema_manager
            
            # 执行测试
            result = self.admin_interface.get_available_schemas()
            
            # 验证结果
            self.assertIsInstance(result, list)
            self.assertIn("public", result)
            self.assertIn("private", result)
            self.assertIn("admin", result)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)