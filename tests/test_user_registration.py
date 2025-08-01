"""
用户注册功能单元测试
测试UserManager和AllowedEmployeeManager的功能
"""

import unittest
import tempfile
import os
import sqlite3
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chatbi.auth.user_manager import UserManager, UserRegistrationResult, AuthenticationResult
from chatbi.auth.allowed_employee_manager import AllowedEmployeeManager, AllowedEmployeeResult
from chatbi.auth.database import AuthDatabase
from chatbi.auth.models import User, AllowedEmployee, validate_employee_id, validate_password_strength
from chatbi.auth.config import AuthConfig


class MockDatabaseConfig:
    """模拟数据库配置"""
    def __init__(self, db_path):
        self.type = "sqlite"
        self.database = db_path
        self.host = None
        self.port = None
        self.username = None
        self.password = None


class TestUserRegistration(unittest.TestCase):
    """用户注册功能测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 创建数据库配置
        self.db_config = MockDatabaseConfig(self.temp_db.name)
        
        # 初始化数据库
        self.database = AuthDatabase(self.db_config)
        self._create_test_tables()
        
        # 创建管理器实例
        self.user_manager = UserManager(self.database)
        self.employee_manager = AllowedEmployeeManager(self.database)
        
        # 创建测试数据
        self._setup_test_data()
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时数据库文件
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def _create_test_tables(self):
        """创建测试用的数据表"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute("""
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            employee_id VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            full_name VARCHAR(100),
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            login_count INTEGER DEFAULT 0
        )
        """)
        
        # 创建允许工号表
        cursor.execute("""
        CREATE TABLE allowed_employees (
            employee_id VARCHAR(50) PRIMARY KEY,
            added_by VARCHAR(36) NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        """)
        
        # 创建审计日志表
        cursor.execute("""
        CREATE TABLE audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id VARCHAR(100),
            details TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
    
    def _setup_test_data(self):
        """设置测试数据"""
        # 添加允许注册的工号
        allowed_employee = AllowedEmployee(
            employee_id="TEST001",
            added_by="admin",
            added_at=datetime.now(),
            description="测试工号"
        )
        self.database.add_allowed_employee(allowed_employee)
        
        # 创建已存在的用户
        existing_user = User(
            id="existing-user-id",
            employee_id="EXISTING001",
            email="existing@test.com",
            full_name="现有用户"
        )
        existing_user.set_password("password123")
        self.database.create_user(existing_user)
        
        # 添加现有用户的工号到允许列表
        existing_allowed = AllowedEmployee(
            employee_id="EXISTING001",
            added_by="admin",
            added_at=datetime.now(),
            description="现有用户工号"
        )
        self.database.add_allowed_employee(existing_allowed)


class TestUserManagerRegistration(TestUserRegistration):
    """UserManager注册功能测试"""
    
    def test_successful_registration(self):
        """测试成功注册"""
        result = self.user_manager.register_user(
            employee_id="TEST001",
            password="password123",
            email="test@example.com",
            full_name="测试用户"
        )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.user_id)
        self.assertEqual(result.message, "用户注册成功")
        self.assertEqual(len(result.errors), 0)
        
        # 验证用户已保存到数据库
        user = self.database.get_user_by_employee_id("TEST001")
        self.assertIsNotNone(user)
        self.assertEqual(user.employee_id, "TEST001")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.full_name, "测试用户")
        self.assertTrue(user.check_password("password123"))
    
    def test_registration_with_invalid_employee_id(self):
        """测试无效工号注册"""
        # 空工号
        result = self.user_manager.register_user("", "password123")
        self.assertFalse(result.success)
        self.assertIn("工号不能为空", result.errors)
        
        # 格式无效的工号
        result = self.user_manager.register_user("@#$%", "password123")
        self.assertFalse(result.success)
        self.assertIn("工号格式无效", result.errors[0])
    
    def test_registration_with_weak_password(self):
        """测试弱密码注册"""
        result = self.user_manager.register_user("TEST001", "123")
        self.assertFalse(result.success)
        self.assertIn("密码长度至少8位", result.errors)
    
    def test_registration_with_invalid_email(self):
        """测试无效邮箱注册"""
        result = self.user_manager.register_user(
            "TEST001", "password123", email="invalid-email"
        )
        self.assertFalse(result.success)
        self.assertIn("邮箱格式无效", result.errors)
    
    def test_registration_employee_not_allowed(self):
        """测试不允许的工号注册"""
        result = self.user_manager.register_user("NOTALLOWED", "password123")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "该工号不允许注册，请联系管理员")
        self.assertIn("employee_id_not_allowed", result.errors)
    
    def test_registration_user_already_exists(self):
        """测试用户已存在的情况"""
        result = self.user_manager.register_user("EXISTING001", "password123")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "该工号已注册，请直接登录")
        self.assertIn("user_already_exists", result.errors)
    
    def test_registration_database_error(self):
        """测试数据库错误情况"""
        # 模拟数据库错误
        with patch.object(self.database, 'create_user', return_value=False):
            result = self.user_manager.register_user("TEST001", "password123")
            self.assertFalse(result.success)
            self.assertEqual(result.message, "注册失败，请稍后重试")
            self.assertIn("database_error", result.errors)


class TestUserManagerAuthentication(TestUserRegistration):
    """UserManager认证功能测试"""
    
    def test_successful_authentication(self):
        """测试成功认证"""
        result = self.user_manager.authenticate_user("EXISTING001", "password123")
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.user)
        self.assertEqual(result.user.employee_id, "EXISTING001")
        self.assertEqual(result.message, "登录成功")
        self.assertEqual(len(result.errors), 0)
    
    def test_authentication_with_invalid_credentials(self):
        """测试无效凭据认证"""
        # 错误密码
        result = self.user_manager.authenticate_user("EXISTING001", "wrongpassword")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "工号或密码错误")
        self.assertIn("invalid_credentials", result.errors)
        
        # 不存在的用户
        result = self.user_manager.authenticate_user("NONEXISTENT", "password123")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "工号或密码错误")
        self.assertIn("invalid_credentials", result.errors)
    
    def test_authentication_with_empty_input(self):
        """测试空输入认证"""
        result = self.user_manager.authenticate_user("", "password123")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "工号和密码不能为空")
        self.assertIn("invalid_input", result.errors)
        
        result = self.user_manager.authenticate_user("EXISTING001", "")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "工号和密码不能为空")
        self.assertIn("invalid_input", result.errors)
    
    def test_authentication_with_inactive_user(self):
        """测试非活跃用户认证"""
        # 创建非活跃用户
        inactive_user = User(
            id="inactive-user-id",
            employee_id="INACTIVE001",
            is_active=False
        )
        inactive_user.set_password("password123")
        self.database.create_user(inactive_user)
        
        result = self.user_manager.authenticate_user("INACTIVE001", "password123")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "账户已被禁用，请联系管理员")
        self.assertIn("account_disabled", result.errors)


class TestAllowedEmployeeManager(TestUserRegistration):
    """AllowedEmployeeManager功能测试"""
    
    def test_add_allowed_employee_success(self):
        """测试成功添加允许工号"""
        result = self.employee_manager.add_allowed_employee(
            employee_id="NEW001",
            added_by="admin",
            description="新测试工号"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "工号添加成功")
        self.assertEqual(len(result.errors), 0)
        
        # 验证工号已添加
        self.assertTrue(self.employee_manager.is_employee_allowed("NEW001"))
    
    def test_add_existing_employee(self):
        """测试添加已存在的工号"""
        result = self.employee_manager.add_allowed_employee(
            employee_id="TEST001",  # 已存在的工号
            added_by="admin"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.message, "该工号已在允许列表中")
        self.assertIn("employee_already_exists", result.errors)
    
    def test_add_invalid_employee_id(self):
        """测试添加无效工号"""
        result = self.employee_manager.add_allowed_employee(
            employee_id="",
            added_by="admin"
        )
        
        self.assertFalse(result.success)
        self.assertIn("工号不能为空", result.errors)
        
        result = self.employee_manager.add_allowed_employee(
            employee_id="@#$%",
            added_by="admin"
        )
        
        self.assertFalse(result.success)
        self.assertIn("工号格式无效", result.errors[0])
    
    def test_remove_allowed_employee_success(self):
        """测试成功移除允许工号"""
        result = self.employee_manager.remove_allowed_employee(
            employee_id="TEST001",
            removed_by="admin"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "工号移除成功")
        self.assertEqual(len(result.errors), 0)
        
        # 验证工号已移除
        self.assertFalse(self.employee_manager.is_employee_allowed("TEST001"))
    
    def test_remove_nonexistent_employee(self):
        """测试移除不存在的工号"""
        result = self.employee_manager.remove_allowed_employee(
            employee_id="NONEXISTENT",
            removed_by="admin"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.message, "该工号不在允许列表中")
        self.assertIn("employee_not_found", result.errors)
    
    def test_get_allowed_employees(self):
        """测试获取允许工号列表"""
        employees = self.employee_manager.get_allowed_employees()
        
        self.assertIsInstance(employees, list)
        self.assertGreater(len(employees), 0)
        
        # 验证包含测试数据
        employee_ids = [emp.employee_id for emp in employees]
        self.assertIn("TEST001", employee_ids)
        self.assertIn("EXISTING001", employee_ids)
    
    def test_batch_add_allowed_employees(self):
        """测试批量添加允许工号"""
        employee_ids = ["BATCH001", "BATCH002", "BATCH003"]
        results = self.employee_manager.batch_add_allowed_employees(
            employee_ids=employee_ids,
            added_by="admin",
            description="批量添加测试"
        )
        
        self.assertEqual(len(results), 3)
        
        for employee_id in employee_ids:
            self.assertIn(employee_id, results)
            self.assertTrue(results[employee_id].success)
            self.assertTrue(self.employee_manager.is_employee_allowed(employee_id))
    
    def test_batch_remove_allowed_employees(self):
        """测试批量移除允许工号"""
        # 先添加一些工号
        employee_ids = ["REMOVE001", "REMOVE002"]
        for employee_id in employee_ids:
            self.employee_manager.add_allowed_employee(employee_id, "admin")
        
        # 批量移除
        results = self.employee_manager.batch_remove_allowed_employees(
            employee_ids=employee_ids,
            removed_by="admin"
        )
        
        self.assertEqual(len(results), 2)
        
        for employee_id in employee_ids:
            self.assertIn(employee_id, results)
            self.assertTrue(results[employee_id].success)
            self.assertFalse(self.employee_manager.is_employee_allowed(employee_id))
    
    def test_search_allowed_employees(self):
        """测试搜索允许工号"""
        # 添加一些测试数据
        self.employee_manager.add_allowed_employee("SEARCH001", "admin", "搜索测试1")
        self.employee_manager.add_allowed_employee("SEARCH002", "admin", "搜索测试2")
        
        # 按工号搜索
        results = self.employee_manager.search_allowed_employees("SEARCH")
        self.assertGreaterEqual(len(results), 2)
        
        # 按描述搜索
        results = self.employee_manager.search_allowed_employees("搜索测试")
        self.assertGreaterEqual(len(results), 2)
    
    def test_get_allowed_employees_count(self):
        """测试获取允许工号总数"""
        count = self.employee_manager.get_allowed_employees_count()
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 2)  # 至少有测试数据中的2个


class TestPasswordValidation(unittest.TestCase):
    """密码验证功能测试"""
    
    def test_validate_password_strength(self):
        """测试密码强度验证"""
        # 有效密码
        result = validate_password_strength("Password123!")
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['errors']), 0)
        
        # 太短的密码
        result = validate_password_strength("123")
        self.assertFalse(result['valid'])
        self.assertIn("密码长度至少8位", result['errors'])
        
        # 太长的密码
        result = validate_password_strength("a" * 130)
        self.assertFalse(result['valid'])
        self.assertIn("密码长度不能超过128位", result['errors'])
        
        # 简单密码（只有警告）
        result = validate_password_strength("password")
        self.assertTrue(result['valid'])  # 仍然有效，但有警告
        self.assertGreater(len(result['warnings']), 0)


class TestEmployeeIdValidation(unittest.TestCase):
    """工号验证功能测试"""
    
    def test_validate_employee_id(self):
        """测试工号格式验证"""
        # 有效工号
        self.assertTrue(validate_employee_id("EMP001"))
        self.assertTrue(validate_employee_id("TEST-123"))
        self.assertTrue(validate_employee_id("USER_456"))
        
        # 无效工号
        self.assertFalse(validate_employee_id(""))  # 空字符串
        self.assertFalse(validate_employee_id("AB"))  # 太短
        self.assertFalse(validate_employee_id("A" * 25))  # 太长
        self.assertFalse(validate_employee_id("EMP@001"))  # 包含特殊字符


if __name__ == '__main__':
    # 配置日志
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # 运行测试
    unittest.main(verbosity=2)