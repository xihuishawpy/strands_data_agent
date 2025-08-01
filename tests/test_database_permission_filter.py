"""
数据库权限过滤器测试
测试SQL查询权限验证、schema访问控制和用户特定数据库连接功能
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import logging

# 设置测试日志级别
logging.basicConfig(level=logging.DEBUG)

from chatbi.auth.database_permission_filter import (
    DatabasePermissionFilter, 
    UserSpecificDatabaseConnector,
    ValidationResult
)
from chatbi.auth.models import User, UserPermission, PermissionLevel
from chatbi.auth.permission_manager import PermissionManager
from chatbi.auth.database import AuthDatabase
from chatbi.auth.config import PermissionConfig


class TestDatabasePermissionFilter(unittest.TestCase):
    """数据库权限过滤器测试类"""
    
    def setUp(self):
        """测试前置设置"""
        # 创建模拟对象
        self.mock_permission_manager = Mock(spec=PermissionManager)
        self.mock_auth_database = Mock(spec=AuthDatabase)
        
        # 创建测试用户
        self.test_user = User(
            id="user123",
            employee_id="EMP001",
            is_active=True,
            is_admin=False
        )
        
        self.admin_user = User(
            id="admin123",
            employee_id="ADMIN001",
            is_active=True,
            is_admin=True
        )
        
        # 创建测试权限
        self.test_permission = UserPermission(
            user_id="user123",
            schema_name="test_schema",
            permission_level=PermissionLevel.READ,
            granted_by="admin123",
            is_active=True
        )
        
        # 模拟权限配置
        self.mock_permission_config = PermissionConfig(
            schema_isolation_enabled=True,
            strict_permission_check=True,
            inherit_admin_permissions=True,
            public_schemas=["public"],
            admin_schemas=["admin_schema"],
            default_schema_access=["default_schema"]
        )
        
        # 创建权限过滤器实例
        with patch('chatbi.auth.database_permission_filter.get_permission_config', 
                  return_value=self.mock_permission_config):
            self.filter = DatabasePermissionFilter(
                self.mock_permission_manager,
                self.mock_auth_database
            )
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.filter)
        self.assertEqual(self.filter.permission_manager, self.mock_permission_manager)
        self.assertEqual(self.filter.auth_database, self.mock_auth_database)
        self.assertIsNotNone(self.filter.table_pattern)
        self.assertIsNotNone(self.filter.schema_pattern)
    
    def test_filter_schemas_normal_user(self):
        """测试普通用户的schema过滤"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        self.mock_permission_manager.get_user_permissions.return_value = [self.test_permission]
        
        available_schemas = ["public", "test_schema", "private_schema", "default_schema"]
        
        # 执行测试
        result = self.filter.filter_schemas("user123", available_schemas)
        
        # 验证结果
        expected_schemas = {"public", "test_schema", "default_schema"}  # 公共 + 用户权限 + 默认
        self.assertEqual(set(result), expected_schemas)
        
        # 验证调用
        self.mock_auth_database.get_user_by_id.assert_called_once_with("user123")
        self.mock_permission_manager.get_user_permissions.assert_called_once_with("user123")
    
    def test_filter_schemas_admin_user(self):
        """测试管理员用户的schema过滤"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.admin_user
        self.mock_permission_manager.get_user_permissions.return_value = []
        
        available_schemas = ["public", "admin_schema", "private_schema", "default_schema"]
        
        # 执行测试
        result = self.filter.filter_schemas("admin123", available_schemas)
        
        # 验证结果
        expected_schemas = {"public", "admin_schema", "default_schema"}  # 公共 + 管理员 + 默认
        self.assertEqual(set(result), expected_schemas)
    
    def test_filter_schemas_inactive_user(self):
        """测试非活跃用户的schema过滤"""
        inactive_user = User(id="user123", is_active=False)
        self.mock_auth_database.get_user_by_id.return_value = inactive_user
        
        available_schemas = ["public", "test_schema"]
        
        # 执行测试
        result = self.filter.filter_schemas("user123", available_schemas)
        
        # 验证结果
        self.assertEqual(result, [])
    
    def test_filter_schemas_isolation_disabled(self):
        """测试schema隔离禁用时的过滤"""
        # 修改配置
        self.filter.permission_config.schema_isolation_enabled = False
        
        available_schemas = ["schema1", "schema2", "schema3"]
        
        # 执行测试
        result = self.filter.filter_schemas("user123", available_schemas)
        
        # 验证结果
        self.assertEqual(result, available_schemas)
    
    def test_validate_sql_permissions_valid_query(self):
        """测试有效SQL查询的权限验证"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        self.mock_permission_manager.check_schema_access.return_value = True
        
        sql_query = "SELECT * FROM test_schema.users"
        
        # 执行测试
        result = self.filter.validate_sql_permissions("user123", sql_query)
        
        # 验证结果
        self.assertTrue(result.valid)
        self.assertEqual(result.message, "SQL权限验证通过")
        self.assertIn("test_schema", result.allowed_schemas)
    
    def test_validate_sql_permissions_invalid_schema(self):
        """测试无权限schema的SQL查询验证"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        self.mock_permission_manager.check_schema_access.return_value = False
        
        sql_query = "SELECT * FROM private_schema.users"
        
        # 执行测试
        result = self.filter.validate_sql_permissions("user123", sql_query)
        
        # 验证结果
        self.assertFalse(result.valid)
        self.assertIn("没有权限访问", result.message)
        self.assertIn("private_schema", result.blocked_schemas)
    
    def test_validate_sql_permissions_system_tables_non_admin(self):
        """测试非管理员访问系统表"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        
        sql_query = "SELECT * FROM information_schema.tables"
        
        # 执行测试
        result = self.filter.validate_sql_permissions("user123", sql_query)
        
        # 验证结果
        self.assertFalse(result.valid)
        self.assertIn("不能访问系统表", result.message)
    
    def test_validate_sql_permissions_system_tables_admin(self):
        """测试管理员访问系统表"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.admin_user
        
        sql_query = "SELECT * FROM information_schema.tables"
        
        # 执行测试
        result = self.filter.validate_sql_permissions("admin123", sql_query)
        
        # 验证结果
        self.assertTrue(result.valid)
    
    def test_validate_sql_permissions_write_operation(self):
        """测试写操作权限验证"""
        # 设置模拟返回值 - 用户只有读权限
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        self.mock_permission_manager.check_schema_access.return_value = False  # 没有写权限
        
        sql_query = "INSERT INTO test_schema.users (name) VALUES ('test')"
        
        # 执行测试
        result = self.filter.validate_sql_permissions("user123", sql_query)
        
        # 验证结果
        self.assertFalse(result.valid)
        self.assertIn("没有权限访问", result.message)
    
    def test_validate_sql_permissions_write_operation_with_permission(self):
        """测试有写权限的写操作验证"""
        # 设置模拟返回值 - 用户有写权限
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        self.mock_permission_manager.check_schema_access.return_value = True
        
        sql_query = "INSERT INTO test_schema.users (name) VALUES ('test')"
        
        # 执行测试
        result = self.filter.validate_sql_permissions("user123", sql_query)
        
        # 验证结果
        self.assertTrue(result.valid)
        self.assertEqual(result.message, "SQL权限验证通过")
    
    def test_validate_sql_permissions_complex_query(self):
        """测试复杂SQL查询的权限验证"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        
        # 模拟用户对test_schema有权限，对private_schema无权限
        def mock_check_schema_access(user_id, schema_name, required_level):
            return schema_name == "test_schema"
        
        self.mock_permission_manager.check_schema_access.side_effect = mock_check_schema_access
        
        sql_query = """
        SELECT u.name, p.title 
        FROM test_schema.users u 
        JOIN private_schema.profiles p ON u.id = p.user_id
        """
        
        # 执行测试
        result = self.filter.validate_sql_permissions("user123", sql_query)
        
        # 验证结果
        self.assertFalse(result.valid)
        self.assertIn("private_schema", result.blocked_schemas)
    
    def test_validate_sql_permissions_no_schema_specified(self):
        """测试未指定schema的SQL查询验证"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        
        sql_query = "SELECT * FROM users"  # 没有指定schema
        
        # 执行测试
        result = self.filter.validate_sql_permissions("user123", sql_query)
        
        # 验证结果 - 应该允许，因为会使用默认schema
        self.assertTrue(result.valid)
    
    def test_validate_sql_permissions_inactive_user(self):
        """测试非活跃用户的SQL权限验证"""
        inactive_user = User(id="user123", is_active=False)
        self.mock_auth_database.get_user_by_id.return_value = inactive_user
        
        sql_query = "SELECT * FROM test_schema.users"
        
        # 执行测试
        result = self.filter.validate_sql_permissions("user123", sql_query)
        
        # 验证结果
        self.assertFalse(result.valid)
        self.assertIn("用户未激活", result.message)
    
    def test_validate_sql_permissions_user_not_found(self):
        """测试用户不存在的SQL权限验证"""
        self.mock_auth_database.get_user_by_id.return_value = None
        
        sql_query = "SELECT * FROM test_schema.users"
        
        # 执行测试
        result = self.filter.validate_sql_permissions("nonexistent", sql_query)
        
        # 验证结果
        self.assertFalse(result.valid)
        self.assertIn("用户不存在", result.message)
    
    def test_extract_schemas_from_sql(self):
        """测试从SQL中提取schema名称"""
        test_cases = [
            ("SELECT * FROM schema1.table1", ["schema1"]),
            ("SELECT * FROM schema1.table1, schema2.table2", ["schema1", "schema2"]),
            ("INSERT INTO schema1.table1 SELECT * FROM schema2.table2", ["schema1", "schema2"]),
            ("SELECT * FROM table1", []),  # 没有schema
            ("SELECT * FROM `schema with spaces`.table1", ["schema with spaces"]),
            ("SELECT * FROM [schema_brackets].table1", ["schema_brackets"]),
        ]
        
        for sql, expected_schemas in test_cases:
            with self.subTest(sql=sql):
                result = self.filter._extract_schemas_from_sql(sql)
                self.assertEqual(sorted(result), sorted(expected_schemas))
    
    def test_is_write_operation(self):
        """测试写操作检测"""
        write_operations = [
            "INSERT INTO table VALUES (1)",
            "UPDATE table SET col = 1",
            "DELETE FROM table WHERE id = 1",
            "CREATE TABLE test (id INT)",
            "DROP TABLE test",
            "ALTER TABLE test ADD COLUMN name VARCHAR(50)",
            "TRUNCATE TABLE test",
        ]
        
        read_operations = [
            "SELECT * FROM table",
            "SHOW TABLES",
            "DESCRIBE table",
            "EXPLAIN SELECT * FROM table",
        ]
        
        for sql in write_operations:
            with self.subTest(sql=sql):
                self.assertTrue(self.filter._is_write_operation(sql))
        
        for sql in read_operations:
            with self.subTest(sql=sql):
                self.assertFalse(self.filter._is_write_operation(sql))
    
    def test_is_system_table_access(self):
        """测试系统表访问检测"""
        system_table_queries = [
            "SELECT * FROM information_schema.tables",
            "SELECT * FROM mysql.user",
            "SELECT * FROM pg_catalog.pg_tables",
            "SELECT * FROM sys.tables",
        ]
        
        regular_queries = [
            "SELECT * FROM user_schema.tables",
            "SELECT * FROM public.users",
            "SELECT * FROM test.data",
        ]
        
        for sql in system_table_queries:
            with self.subTest(sql=sql):
                self.assertTrue(self.filter._is_system_table_access(sql))
        
        for sql in regular_queries:
            with self.subTest(sql=sql):
                self.assertFalse(self.filter._is_system_table_access(sql))


class TestUserSpecificDatabaseConnector(unittest.TestCase):
    """用户特定数据库连接器测试类"""
    
    def setUp(self):
        """测试前置设置"""
        self.mock_base_connector = Mock()
        self.mock_permission_filter = Mock(spec=DatabasePermissionFilter)
        
        # 创建测试用户
        self.test_user = User(
            id="user123",
            employee_id="EMP001",
            is_active=True,
            is_admin=False
        )
        
        # 创建连接器实例
        self.connector = UserSpecificDatabaseConnector(
            base_connector=self.mock_base_connector,
            permission_filter=self.mock_permission_filter,
            user_id="user123"
        )
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.connector)
        self.assertEqual(self.connector.base_connector, self.mock_base_connector)
        self.assertEqual(self.connector.permission_filter, self.mock_permission_filter)
        self.assertEqual(self.connector.user_id, "user123")
    
    def test_get_schemas_filtered(self):
        """测试获取过滤后的schema列表"""
        # 设置模拟返回值
        self.mock_base_connector.get_schemas.return_value = ["schema1", "schema2", "schema3"]
        self.mock_permission_filter.filter_schemas.return_value = ["schema1", "schema3"]
        
        # 执行测试
        result = self.connector.get_schemas()
        
        # 验证结果
        self.assertEqual(result, ["schema1", "schema3"])
        self.mock_base_connector.get_schemas.assert_called_once()
        self.mock_permission_filter.filter_schemas.assert_called_once_with(
            "user123", ["schema1", "schema2", "schema3"]
        )
    
    def test_execute_query_valid_permissions(self):
        """测试执行有权限的查询"""
        # 设置模拟返回值
        validation_result = ValidationResult(
            valid=True,
            message="权限验证通过",
            allowed_schemas=["test_schema"],
            blocked_schemas=[]
        )
        self.mock_permission_filter.validate_sql_permissions.return_value = validation_result
        self.mock_base_connector.execute_query.return_value = [{"id": 1, "name": "test"}]
        
        sql_query = "SELECT * FROM test_schema.users"
        
        # 执行测试
        result = self.connector.execute_query(sql_query)
        
        # 验证结果
        self.assertEqual(result, [{"id": 1, "name": "test"}])
        self.mock_permission_filter.validate_sql_permissions.assert_called_once_with(
            "user123", sql_query
        )
        self.mock_base_connector.execute_query.assert_called_once_with(sql_query)
    
    def test_execute_query_invalid_permissions(self):
        """测试执行无权限的查询"""
        # 设置模拟返回值
        validation_result = ValidationResult(
            valid=False,
            message="没有权限访问schema: private_schema",
            allowed_schemas=[],
            blocked_schemas=["private_schema"]
        )
        self.mock_permission_filter.validate_sql_permissions.return_value = validation_result
        
        sql_query = "SELECT * FROM private_schema.users"
        
        # 执行测试并验证异常
        with self.assertRaises(PermissionError) as context:
            self.connector.execute_query(sql_query)
        
        self.assertIn("没有权限访问schema", str(context.exception))
        self.mock_base_connector.execute_query.assert_not_called()
    
    def test_get_table_info_filtered(self):
        """测试获取过滤后的表信息"""
        # 设置模拟返回值
        self.mock_base_connector.get_table_info.return_value = {
            "schema1.table1": {"columns": ["id", "name"]},
            "schema2.table2": {"columns": ["id", "data"]},
        }
        self.mock_permission_filter.filter_schemas.return_value = ["schema1"]
        
        # 执行测试
        result = self.connector.get_table_info()
        
        # 验证结果
        expected_result = {
            "schema1.table1": {"columns": ["id", "name"]}
        }
        self.assertEqual(result, expected_result)
    
    def test_get_table_info_specific_schema(self):
        """测试获取特定schema的表信息"""
        # 设置模拟返回值
        self.mock_permission_filter.filter_schemas.return_value = ["allowed_schema"]
        self.mock_base_connector.get_table_info.return_value = {
            "allowed_schema.table1": {"columns": ["id", "name"]}
        }
        
        # 执行测试
        result = self.connector.get_table_info(schema_name="allowed_schema")
        
        # 验证结果
        self.assertEqual(result, {"allowed_schema.table1": {"columns": ["id", "name"]}})
        self.mock_base_connector.get_table_info.assert_called_once_with("allowed_schema")
    
    def test_get_table_info_unauthorized_schema(self):
        """测试获取无权限schema的表信息"""
        # 设置模拟返回值
        self.mock_permission_filter.filter_schemas.return_value = ["allowed_schema"]
        
        # 执行测试并验证异常
        with self.assertRaises(PermissionError) as context:
            self.connector.get_table_info(schema_name="unauthorized_schema")
        
        self.assertIn("没有权限访问schema", str(context.exception))
        self.mock_base_connector.get_table_info.assert_not_called()


class TestValidationResult(unittest.TestCase):
    """验证结果测试类"""
    
    def test_validation_result_creation(self):
        """测试验证结果创建"""
        result = ValidationResult(
            valid=True,
            message="测试消息",
            allowed_schemas=["schema1", "schema2"],
            blocked_schemas=["schema3"]
        )
        
        self.assertTrue(result.valid)
        self.assertEqual(result.message, "测试消息")
        self.assertEqual(result.allowed_schemas, ["schema1", "schema2"])
        self.assertEqual(result.blocked_schemas, ["schema3"])
    
    def test_validation_result_defaults(self):
        """测试验证结果默认值"""
        result = ValidationResult(valid=False, message="错误")
        
        self.assertFalse(result.valid)
        self.assertEqual(result.message, "错误")
        self.assertEqual(result.allowed_schemas, [])
        self.assertEqual(result.blocked_schemas, [])


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)