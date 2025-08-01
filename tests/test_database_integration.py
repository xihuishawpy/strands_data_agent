"""
数据库集成测试
测试修改后的数据库组件与认证系统的集成
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试日志级别
logging.basicConfig(level=logging.DEBUG)

try:
    from chatbi.database.sql_executor import SQLExecutor, SQLResult, get_sql_executor, create_user_sql_executor
    from chatbi.database.schema_manager import SchemaManager, get_schema_manager, create_user_schema_manager
    from chatbi.auth.models import User, UserPermission, PermissionLevel
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录下运行测试")
    sys.exit(1)


class TestSQLExecutorIntegration(unittest.TestCase):
    """SQL执行器集成测试类"""
    
    def setUp(self):
        """测试前置设置"""
        # 创建模拟数据库连接器
        self.mock_connector = Mock()
        self.mock_connector.is_connected = True
        self.mock_connector.connect.return_value = True
        self.mock_connector.execute_query.return_value = {
            "success": True,
            "data": [{"id": 1, "name": "test"}],
            "columns": ["id", "name"],
            "row_count": 1
        }
        
        # 创建测试用户
        self.test_user = User(
            id="user123",
            employee_id="EMP001",
            is_active=True,
            is_admin=False
        )
    
    def test_sql_executor_without_user(self):
        """测试不带用户的SQL执行器"""
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector):
            executor = SQLExecutor()
            
            # 执行查询
            result = executor.execute("SELECT * FROM test_table")
            
            # 验证结果
            self.assertTrue(result.success)
            self.assertEqual(len(result.data), 1)
            self.assertEqual(result.data[0]["name"], "test")
            self.mock_connector.execute_query.assert_called_once()
    
    def test_sql_executor_with_user_valid_permissions(self):
        """测试带用户的SQL执行器（有效权限）"""
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.sql_executor.SQLExecutor._setup_user_connector'), \
             patch('chatbi.database.sql_executor.SQLExecutor._validate_user_permissions') as mock_validate:
            
            # 模拟权限验证通过
            mock_validate.return_value = {
                "valid": True,
                "error": None,
                "allowed_schemas": ["test_schema"],
                "blocked_schemas": []
            }
            
            executor = SQLExecutor(user_id="user123")
            
            # 执行查询
            result = executor.execute("SELECT * FROM test_schema.test_table")
            
            # 验证结果
            self.assertTrue(result.success)
            self.assertEqual(len(result.data), 1)
            mock_validate.assert_called_once()
            self.mock_connector.execute_query.assert_called_once()
    
    def test_sql_executor_with_user_invalid_permissions(self):
        """测试带用户的SQL执行器（无效权限）"""
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.sql_executor.SQLExecutor._setup_user_connector'), \
             patch('chatbi.database.sql_executor.SQLExecutor._validate_user_permissions') as mock_validate:
            
            # 模拟权限验证失败
            mock_validate.return_value = {
                "valid": False,
                "error": "没有权限访问schema: private_schema",
                "allowed_schemas": [],
                "blocked_schemas": ["private_schema"]
            }
            
            executor = SQLExecutor(user_id="user123")
            
            # 执行查询
            result = executor.execute("SELECT * FROM private_schema.secret_table")
            
            # 验证结果
            self.assertFalse(result.success)
            self.assertIn("权限验证失败", result.error)
            mock_validate.assert_called_once()
            self.mock_connector.execute_query.assert_not_called()
    
    def test_sql_executor_unsafe_query(self):
        """测试不安全的SQL查询"""
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector):
            executor = SQLExecutor()
            
            # 执行危险查询
            result = executor.execute("DROP TABLE test_table")
            
            # 验证结果
            self.assertFalse(result.success)
            self.assertIn("SQL安全检查失败", result.error)
            self.mock_connector.execute_query.assert_not_called()
    
    def test_get_sql_executor_global(self):
        """测试获取全局SQL执行器"""
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector):
            executor1 = get_sql_executor()
            executor2 = get_sql_executor()
            
            # 验证是同一个实例
            self.assertIs(executor1, executor2)
            self.assertIsNone(executor1.user_id)
    
    def test_get_sql_executor_with_user(self):
        """测试获取用户特定的SQL执行器"""
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.sql_executor.SQLExecutor._setup_user_connector'):
            
            executor1 = get_sql_executor(user_id="user123")
            executor2 = get_sql_executor(user_id="user456")
            
            # 验证是不同的实例
            self.assertIsNot(executor1, executor2)
            self.assertEqual(executor1.user_id, "user123")
            self.assertEqual(executor2.user_id, "user456")
    
    def test_create_user_sql_executor(self):
        """测试创建用户特定的SQL执行器"""
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.sql_executor.SQLExecutor._setup_user_connector'):
            
            executor = create_user_sql_executor("user123")
            
            # 验证结果
            self.assertIsNotNone(executor)
            self.assertEqual(executor.user_id, "user123")


class TestSchemaManagerIntegration(unittest.TestCase):
    """Schema管理器集成测试类"""
    
    def setUp(self):
        """测试前置设置"""
        # 创建模拟数据库连接器
        self.mock_connector = Mock()
        self.mock_connector.get_tables.return_value = [
            "public.users", "public.orders", "private.secrets", "admin.logs"
        ]
        self.mock_connector.get_table_schema.return_value = {
            "table_name": "users",
            "columns": [
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "name", "type": "VARCHAR(100)", "nullable": True}
            ],
            "primary_keys": ["id"],
            "foreign_keys": [],
            "indexes": []
        }
        
        # 创建模拟权限过滤器
        self.mock_permission_filter = Mock()
        self.mock_permission_filter.filter_schemas.return_value = ["public"]
        
        # 创建测试用户
        self.test_user = User(
            id="user123",
            employee_id="EMP001",
            is_active=True,
            is_admin=False
        )
    
    def test_schema_manager_without_user(self):
        """测试不带用户的Schema管理器"""
        with patch('chatbi.database.schema_manager.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.schema_manager.config') as mock_config:
            
            mock_config.knowledge_base_path = "/tmp"
            mock_config.schema_cache_ttl = 3600
            mock_config.database.type = "postgresql"
            
            manager = SchemaManager()
            
            # 获取所有表名
            tables = manager.get_all_tables()
            
            # 验证结果
            self.assertEqual(len(tables), 4)
            self.assertIn("public.users", tables)
            self.assertIn("private.secrets", tables)
            self.mock_connector.get_tables.assert_called_once()
    
    def test_schema_manager_with_user_permission_filtering(self):
        """测试带用户的Schema管理器（权限过滤）"""
        with patch('chatbi.database.schema_manager.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.schema_manager.config') as mock_config, \
             patch('chatbi.database.schema_manager.SchemaManager._setup_user_components') as mock_setup:
            
            mock_config.knowledge_base_path = "/tmp"
            mock_config.schema_cache_ttl = 3600
            mock_config.database.type = "postgresql"
            
            manager = SchemaManager(user_id="user123")
            manager._permission_filter = self.mock_permission_filter
            
            # 获取所有表名
            tables = manager.get_all_tables()
            
            # 验证结果 - 由于权限过滤器被设置，应该调用过滤方法
            if manager._permission_filter:
                # 如果有权限过滤器，验证过滤结果
                self.assertEqual(len(tables), 2)  # 只有public schema的表
                self.assertIn("public.users", tables)
                self.assertIn("public.orders", tables)
                self.assertNotIn("private.secrets", tables)
            else:
                # 如果没有权限过滤器，返回所有表
                self.assertEqual(len(tables), 4)
    
    def test_schema_manager_get_database_schema_with_user(self):
        """测试带用户的数据库Schema获取"""
        with patch('chatbi.database.schema_manager.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.schema_manager.config') as mock_config, \
             patch('chatbi.database.schema_manager.SchemaManager._setup_user_components'):
            
            mock_config.knowledge_base_path = "/tmp"
            mock_config.schema_cache_ttl = 3600
            mock_config.database.type = "postgresql"
            
            manager = SchemaManager(user_id="user123")
            manager._permission_filter = self.mock_permission_filter
            
            # 获取数据库Schema
            schema = manager.get_database_schema()
            
            # 验证结果
            self.assertEqual(schema["database_type"], "postgresql")
            self.assertEqual(schema["user_id"], "user123")
            self.assertTrue(schema["permission_filtered"])
            self.assertIn("tables", schema)
    
    def test_schema_manager_get_schema_summary_with_permissions(self):
        """测试带权限的Schema摘要获取"""
        with patch('chatbi.database.schema_manager.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.schema_manager.config') as mock_config, \
             patch('chatbi.database.schema_manager.SchemaManager._setup_user_components'), \
             patch('chatbi.database.schema_manager.SchemaManager.get_database_schema') as mock_get_schema:
            
            mock_config.knowledge_base_path = "/tmp"
            mock_config.schema_cache_ttl = 3600
            mock_config.database.type = "postgresql"
            
            # 模拟返回的schema数据
            mock_get_schema.return_value = {
                "database_type": "postgresql",
                "user_id": "user123",
                "permission_filtered": True,
                "tables": {
                    "public.users": {
                        "table_name": "users",
                        "columns": [{"name": "id", "type": "INTEGER"}],
                        "primary_keys": ["id"],
                        "foreign_keys": [],
                        "indexes": []
                    }
                },
                "relationships": []
            }
            
            manager = SchemaManager(user_id="user123")
            manager._permission_filter = self.mock_permission_filter
            
            # 模拟表元数据管理器
            with patch.object(manager, '_metadata_manager') as mock_metadata:
                mock_metadata.get_enhanced_schema_summary.return_value = "Enhanced schema summary"
                
                # 获取Schema摘要
                summary = manager.get_schema_summary()
                
                # 验证结果
                self.assertIn("Enhanced schema summary", summary)
                self.assertIn("以上信息已根据用户权限进行过滤", summary)
    
    def test_get_schema_manager_global(self):
        """测试获取全局Schema管理器"""
        with patch('chatbi.database.schema_manager.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.schema_manager.config') as mock_config:
            
            mock_config.knowledge_base_path = "/tmp"
            mock_config.schema_cache_ttl = 3600
            
            manager1 = get_schema_manager()
            manager2 = get_schema_manager()
            
            # 验证是同一个实例
            self.assertIs(manager1, manager2)
            self.assertIsNone(manager1.user_id)
    
    def test_get_schema_manager_with_user(self):
        """测试获取用户特定的Schema管理器"""
        with patch('chatbi.database.schema_manager.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.schema_manager.config') as mock_config, \
             patch('chatbi.database.schema_manager.SchemaManager._setup_user_components'):
            
            mock_config.knowledge_base_path = "/tmp"
            mock_config.schema_cache_ttl = 3600
            
            manager1 = get_schema_manager(user_id="user123")
            manager2 = get_schema_manager(user_id="user456")
            
            # 验证是不同的实例
            self.assertIsNot(manager1, manager2)
            self.assertEqual(manager1.user_id, "user123")
            self.assertEqual(manager2.user_id, "user456")
    
    def test_create_user_schema_manager(self):
        """测试创建用户特定的Schema管理器"""
        with patch('chatbi.database.schema_manager.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.schema_manager.config') as mock_config, \
             patch('chatbi.database.schema_manager.SchemaManager._setup_user_components'):
            
            mock_config.knowledge_base_path = "/tmp"
            mock_config.schema_cache_ttl = 3600
            
            manager = create_user_schema_manager("user123")
            
            # 验证结果
            self.assertIsNotNone(manager)
            self.assertEqual(manager.user_id, "user123")


class TestDatabaseIntegrationWithAuth(unittest.TestCase):
    """数据库与认证系统集成测试类"""
    
    def setUp(self):
        """测试前置设置"""
        self.mock_connector = Mock()
        self.mock_integration = Mock()
        self.mock_permission_filter = Mock()
        
        # 创建测试用户
        self.test_user = User(
            id="user123",
            employee_id="EMP001",
            is_active=True,
            is_admin=False
        )
    
    def test_sql_executor_user_connector_setup(self):
        """测试SQL执行器的用户连接器设置"""
        mock_user_connector = Mock()
        self.mock_integration.create_user_database_connector.return_value = mock_user_connector
        
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.auth.chatbi_integration.get_integration_adapter', return_value=self.mock_integration):
            
            executor = SQLExecutor(user_id="user123")
            
            # 验证用户连接器设置
            self.mock_integration.create_user_database_connector.assert_called_once_with("user123")
            self.assertEqual(executor.connector, mock_user_connector)
    
    def test_schema_manager_user_components_setup(self):
        """测试Schema管理器的用户组件设置"""
        mock_user_connector = Mock()
        self.mock_integration.create_user_database_connector.return_value = mock_user_connector
        self.mock_integration.permission_filter = self.mock_permission_filter
        
        with patch('chatbi.database.schema_manager.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.database.schema_manager.config') as mock_config, \
             patch('chatbi.auth.chatbi_integration.get_integration_adapter', return_value=self.mock_integration):
            
            mock_config.knowledge_base_path = "/tmp"
            mock_config.schema_cache_ttl = 3600
            
            manager = SchemaManager(user_id="user123")
            
            # 验证用户组件设置
            self.mock_integration.create_user_database_connector.assert_called_once_with("user123")
            self.assertEqual(manager.connector, mock_user_connector)
            self.assertEqual(manager._permission_filter, self.mock_permission_filter)
    
    def test_permission_validation_integration(self):
        """测试权限验证集成"""
        # 模拟权限验证组件
        mock_permission_manager = Mock()
        mock_auth_database = Mock()
        mock_permission_filter = Mock()
        
        validation_result = Mock()
        validation_result.valid = False
        validation_result.message = "没有权限访问schema: private"
        validation_result.allowed_schemas = ["public"]
        validation_result.blocked_schemas = ["private"]
        
        mock_permission_filter.validate_sql_permissions.return_value = validation_result
        
        with patch('chatbi.database.sql_executor.get_global_connector', return_value=self.mock_connector), \
             patch('chatbi.auth.permission_manager.PermissionManager', return_value=mock_permission_manager), \
             patch('chatbi.auth.database.AuthDatabase', return_value=mock_auth_database), \
             patch('chatbi.auth.database_permission_filter.DatabasePermissionFilter', return_value=mock_permission_filter):
            
            executor = SQLExecutor(user_id="user123")
            
            # 执行查询
            result = executor.execute("SELECT * FROM private.secret_data")
            
            # 验证权限检查被调用
            mock_permission_filter.validate_sql_permissions.assert_called_once_with("user123", "SELECT * FROM private.secret_data")
            
            # 验证查询被拒绝
            self.assertFalse(result.success)
            self.assertIn("权限验证失败", result.error)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)