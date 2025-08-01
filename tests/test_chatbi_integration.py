"""
ChatBI集成适配器测试
测试认证模块与ChatBI系统的集成功能
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import logging

# 设置测试日志级别
logging.basicConfig(level=logging.DEBUG)

from chatbi.auth.chatbi_integration import (
    ChatBIAuthIntegration,
    AuthenticatedOrchestrator,
    AuthenticatedQueryResult,
    get_integration_adapter,
    require_authentication,
    require_schema_permission
)
from chatbi.auth.models import User, UserPermission, PermissionLevel
from chatbi.orchestrator import ChatBIOrchestrator, QueryResult


class TestChatBIAuthIntegration(unittest.TestCase):
    """ChatBI认证集成适配器测试类"""
    
    def setUp(self):
        """测试前置设置"""
        # 创建模拟对象
        self.mock_session_manager = Mock()
        self.mock_permission_manager = Mock()
        self.mock_auth_database = Mock()
        self.mock_permission_filter = Mock()
        
        # 创建测试用户
        self.test_user = User(
            id="user123",
            employee_id="EMP001",
            is_active=True,
            is_admin=False
        )
        
        # 创建集成适配器实例
        with patch('chatbi.auth.chatbi_integration.SessionManager', return_value=self.mock_session_manager), \
             patch('chatbi.auth.chatbi_integration.PermissionManager', return_value=self.mock_permission_manager), \
             patch('chatbi.auth.chatbi_integration.AuthDatabase', return_value=self.mock_auth_database), \
             patch('chatbi.auth.chatbi_integration.DatabasePermissionFilter', return_value=self.mock_permission_filter):
            
            self.integration = ChatBIAuthIntegration()
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.integration)
        self.assertIsNotNone(self.integration.session_manager)
        self.assertIsNotNone(self.integration.permission_manager)
        self.assertIsNotNone(self.integration.auth_database)
        self.assertIsNotNone(self.integration.permission_filter)
    
    def test_wrap_orchestrator_success(self):
        """测试成功包装orchestrator"""
        # 设置模拟返回值
        session_result = Mock()
        session_result.valid = True
        session_result.user_id = "user123"
        self.mock_session_manager.validate_session.return_value = session_result
        
        # 创建模拟orchestrator
        mock_orchestrator = Mock(spec=ChatBIOrchestrator)
        
        # 执行测试
        with patch('chatbi.auth.chatbi_integration.get_global_connector'), \
             patch('chatbi.auth.chatbi_integration.UserSpecificDatabaseConnector'):
            
            result = self.integration.wrap_orchestrator(mock_orchestrator, "valid_token")
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AuthenticatedOrchestrator)
        self.assertEqual(result.user_id, "user123")
        self.mock_session_manager.validate_session.assert_called_once_with("valid_token")
    
    def test_wrap_orchestrator_invalid_session(self):
        """测试无效会话的orchestrator包装"""
        # 设置模拟返回值
        session_result = Mock()
        session_result.valid = False
        session_result.message = "会话已过期"
        self.mock_session_manager.validate_session.return_value = session_result
        
        mock_orchestrator = Mock(spec=ChatBIOrchestrator)
        
        # 执行测试
        result = self.integration.wrap_orchestrator(mock_orchestrator, "invalid_token")
        
        # 验证结果
        self.assertIsNone(result)
        self.mock_session_manager.validate_session.assert_called_once_with("invalid_token")
    
    def test_create_user_database_connector_success(self):
        """测试成功创建用户数据库连接器"""
        # 设置模拟返回值
        self.mock_auth_database.get_user_by_id.return_value = self.test_user
        
        # 执行测试
        with patch('chatbi.auth.chatbi_integration.get_global_connector') as mock_get_connector, \
             patch('chatbi.auth.chatbi_integration.UserSpecificDatabaseConnector') as mock_connector_class:
            
            mock_base_connector = Mock()
            mock_get_connector.return_value = mock_base_connector
            
            mock_user_connector = Mock()
            mock_user_connector.connect.return_value = True
            mock_connector_class.return_value = mock_user_connector
            
            result = self.integration.create_user_database_connector("user123")
        
        # 验证结果
        self.assertIsNotNone(result)
        self.mock_auth_database.get_user_by_id.assert_called_once_with("user123")
        mock_connector_class.assert_called_once_with(
            base_connector=mock_base_connector,
            user_id="user123",
            permission_filter=self.mock_permission_filter
        )
    
    def test_create_user_database_connector_inactive_user(self):
        """测试为非活跃用户创建数据库连接器"""
        inactive_user = User(id="user123", is_active=False)
        self.mock_auth_database.get_user_by_id.return_value = inactive_user
        
        # 执行测试
        result = self.integration.create_user_database_connector("user123")
        
        # 验证结果
        self.assertIsNone(result)
    
    def test_filter_schema_info(self):
        """测试过滤schema信息"""
        # 设置模拟返回值
        self.mock_permission_filter.filter_schemas.return_value = ["schema1", "schema2"]
        
        schema_info = """
        Database Schema Information:
        - schema1.table1: User data
        - schema2.table2: Product data
        - schema3.table3: Admin data
        """
        
        # 执行测试
        result = self.integration.filter_schema_info("user123", schema_info)
        
        # 验证结果
        self.assertIn("schema1", result)
        self.assertIn("schema2", result)
        self.assertIn("您当前有权限访问以下schema: schema1, schema2", result)
    
    def test_validate_user_session_success(self):
        """测试成功验证用户会话"""
        # 设置模拟返回值
        session_result = Mock()
        session_result.valid = True
        session_result.user_id = "user123"
        session_result.message = "会话有效"
        session_result.expires_at = datetime.now() + timedelta(hours=1)
        self.mock_session_manager.validate_session.return_value = session_result
        
        # 执行测试
        result = self.integration.validate_user_session("valid_token")
        
        # 验证结果
        self.assertTrue(result["valid"])
        self.assertEqual(result["user_id"], "user123")
        self.assertEqual(result["message"], "会话有效")
        self.assertIsNotNone(result["expires_at"])
    
    def test_validate_user_session_invalid(self):
        """测试验证无效用户会话"""
        # 设置模拟返回值
        session_result = Mock()
        session_result.valid = False
        session_result.user_id = None
        session_result.message = "会话已过期"
        session_result.expires_at = None
        self.mock_session_manager.validate_session.return_value = session_result
        
        # 执行测试
        result = self.integration.validate_user_session("invalid_token")
        
        # 验证结果
        self.assertFalse(result["valid"])
        self.assertIsNone(result["user_id"])
        self.assertEqual(result["message"], "会话已过期")
        self.assertIsNone(result["expires_at"])
    
    def test_get_user_permissions(self):
        """测试获取用户权限信息"""
        # 创建测试权限
        permission1 = UserPermission(
            user_id="user123",
            schema_name="schema1",
            permission_level=PermissionLevel.READ,
            granted_at=datetime.now(),
            is_active=True
        )
        
        permission2 = UserPermission(
            user_id="user123",
            schema_name="schema2",
            permission_level=PermissionLevel.WRITE,
            granted_at=datetime.now(),
            is_active=True
        )
        
        # 设置模拟返回值
        self.mock_permission_manager.get_user_permissions.return_value = [permission1, permission2]
        
        # 执行测试
        result = self.integration.get_user_permissions("user123")
        
        # 验证结果
        self.assertEqual(result["user_id"], "user123")
        self.assertEqual(len(result["permissions"]), 2)
        self.assertEqual(len(result["accessible_schemas"]), 2)
        self.assertIn("schema1", result["accessible_schemas"])
        self.assertIn("schema2", result["accessible_schemas"])
    
    def test_extract_schemas_from_info(self):
        """测试从schema信息中提取schema名称"""
        schema_info = """
        Database contains the following schemas:
        - schema user_data with tables
        - schema product_info with tables
        - table admin_logs in schema system
        """
        
        # 执行测试
        result = self.integration._extract_schemas_from_info(schema_info)
        
        # 验证结果
        self.assertIn("user_data", result)
        self.assertIn("product_info", result)
        self.assertIn("system", result)
    
    def test_filter_schema_text(self):
        """测试过滤schema文本"""
        schema_info = """
        Schema: user_data
        - table: users
        - table: profiles
        
        Schema: admin_data
        - table: admin_logs
        - table: system_config
        
        General information about database
        """
        
        accessible_schemas = ["user_data"]
        
        # 执行测试
        result = self.integration._filter_schema_text(schema_info, accessible_schemas)
        
        # 验证结果
        self.assertIn("user_data", result)
        self.assertNotIn("admin_data", result)
        self.assertIn("General information", result)
        self.assertIn("您当前有权限访问以下schema: user_data", result)


class TestAuthenticatedOrchestrator(unittest.TestCase):
    """认证包装器测试类"""
    
    def setUp(self):
        """测试前置设置"""
        self.mock_base_orchestrator = Mock(spec=ChatBIOrchestrator)
        self.mock_permission_filter = Mock()
        
        # 创建认证包装器实例
        with patch('chatbi.auth.chatbi_integration.get_global_connector'), \
             patch('chatbi.auth.chatbi_integration.UserSpecificDatabaseConnector') as mock_connector:
            
            mock_user_connector = Mock()
            mock_user_connector.connect.return_value = True
            mock_connector.return_value = mock_user_connector
            
            self.auth_orchestrator = AuthenticatedOrchestrator(
                base_orchestrator=self.mock_base_orchestrator,
                user_id="user123",
                permission_filter=self.mock_permission_filter
            )
    
    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.auth_orchestrator)
        self.assertEqual(self.auth_orchestrator.user_id, "user123")
        self.assertEqual(self.auth_orchestrator.base_orchestrator, self.mock_base_orchestrator)
        self.assertEqual(self.auth_orchestrator.permission_filter, self.mock_permission_filter)
    
    def test_query_success(self):
        """测试成功执行查询"""
        # 设置模拟返回值
        base_result = QueryResult(
            success=True,
            question="测试问题",
            sql_query="SELECT * FROM test",
            data=[{"id": 1, "name": "test"}],
            execution_time=1.5
        )
        self.mock_base_orchestrator.query.return_value = base_result
        
        # 模拟用户可访问的schema
        with patch.object(self.auth_orchestrator, '_get_user_accessible_schemas', return_value=["test_schema"]):
            # 执行测试
            result = self.auth_orchestrator.query("测试问题")
        
        # 验证结果
        self.assertIsInstance(result, AuthenticatedQueryResult)
        self.assertTrue(result.success)
        self.assertEqual(result.question, "测试问题")
        self.assertEqual(result.user_id, "user123")
        self.assertEqual(result.accessible_schemas, ["test_schema"])
        self.assertTrue(result.permission_filtered)
    
    def test_query_failure(self):
        """测试查询失败"""
        # 设置模拟返回值
        base_result = QueryResult(
            success=False,
            question="测试问题",
            error="SQL执行失败"
        )
        self.mock_base_orchestrator.query.return_value = base_result
        
        # 模拟用户可访问的schema
        with patch.object(self.auth_orchestrator, '_get_user_accessible_schemas', return_value=["test_schema"]):
            # 执行测试
            result = self.auth_orchestrator.query("测试问题")
        
        # 验证结果
        self.assertIsInstance(result, AuthenticatedQueryResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error, "SQL执行失败")
        self.assertEqual(result.user_id, "user123")
    
    def test_query_stream_success(self):
        """测试成功执行流式查询"""
        # 设置模拟返回值
        def mock_query_stream(*args, **kwargs):
            yield {"step_info": "步骤1: 生成SQL"}
            yield {"step_info": "步骤2: 执行查询"}
            yield {"final_result": QueryResult(
                success=True,
                question="测试问题",
                sql_query="SELECT * FROM test",
                data=[{"id": 1}]
            )}
        
        self.mock_base_orchestrator.query_stream.side_effect = mock_query_stream
        
        # 模拟用户可访问的schema
        with patch.object(self.auth_orchestrator, '_get_user_accessible_schemas', return_value=["test_schema"]):
            # 执行测试
            results = list(self.auth_orchestrator.query_stream("测试问题"))
        
        # 验证结果
        self.assertTrue(len(results) > 0)
        
        # 检查权限验证步骤
        permission_steps = [r for r in results if "step_info" in r and "权限验证" in r["step_info"]]
        self.assertTrue(len(permission_steps) > 0)
        
        # 检查最终结果
        final_results = [r for r in results if "final_result" in r]
        self.assertEqual(len(final_results), 1)
        
        final_result = final_results[0]["final_result"]
        self.assertIsInstance(final_result, AuthenticatedQueryResult)
        self.assertTrue(final_result.success)
        self.assertEqual(final_result.user_id, "user123")
    
    def test_query_stream_no_permissions(self):
        """测试无权限的流式查询"""
        # 模拟用户没有任何权限
        with patch.object(self.auth_orchestrator, '_get_user_accessible_schemas', return_value=[]):
            # 执行测试
            results = list(self.auth_orchestrator.query_stream("测试问题"))
        
        # 验证结果
        final_results = [r for r in results if "final_result" in r]
        self.assertEqual(len(final_results), 1)
        
        final_result = final_results[0]["final_result"]
        self.assertFalse(final_result.success)
        self.assertIn("没有任何数据库访问权限", final_result.error)
    
    def test_get_schema_info(self):
        """测试获取schema信息"""
        # 设置模拟返回值
        base_schema_info = {
            "tables": ["table1", "table2"],
            "schema": "test_schema"
        }
        self.mock_base_orchestrator.get_schema_info.return_value = base_schema_info
        
        # 模拟过滤后的schema信息
        with patch.object(self.auth_orchestrator, '_filter_schema_info', return_value={"filtered": True}):
            # 执行测试
            result = self.auth_orchestrator.get_schema_info()
        
        # 验证结果
        self.assertEqual(result, {"filtered": True})
        self.mock_base_orchestrator.get_schema_info.assert_called_once_with(None)
    
    def test_add_positive_feedback(self):
        """测试添加正面反馈"""
        # 设置模拟返回值
        self.mock_base_orchestrator.add_positive_feedback.return_value = True
        
        # 执行测试
        result = self.auth_orchestrator.add_positive_feedback("问题", "SQL", "描述")
        
        # 验证结果
        self.assertTrue(result)
        self.mock_base_orchestrator.add_positive_feedback.assert_called_once_with("问题", "SQL", "描述")


class TestDecorators(unittest.TestCase):
    """装饰器测试类"""
    
    def test_require_authentication_success(self):
        """测试认证装饰器成功"""
        @require_authentication
        def test_function(session_token, user_id=None):
            return {"success": True, "user_id": user_id}
        
        # 模拟有效会话
        with patch('chatbi.auth.chatbi_integration.get_integration_adapter') as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.validate_user_session.return_value = {
                "valid": True,
                "user_id": "user123",
                "message": "会话有效"
            }
            mock_get_adapter.return_value = mock_adapter
            
            # 执行测试
            result = test_function("valid_token")
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["user_id"], "user123")
    
    def test_require_authentication_invalid_token(self):
        """测试认证装饰器无效令牌"""
        @require_authentication
        def test_function(session_token, user_id=None):
            return {"success": True, "user_id": user_id}
        
        # 模拟无效会话
        with patch('chatbi.auth.chatbi_integration.get_integration_adapter') as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.validate_user_session.return_value = {
                "valid": False,
                "user_id": None,
                "message": "会话已过期"
            }
            mock_get_adapter.return_value = mock_adapter
            
            # 执行测试
            result = test_function("invalid_token")
        
        # 验证结果
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_login"])
        self.assertIn("会话已过期", result["error"])
    
    def test_require_authentication_missing_token(self):
        """测试认证装饰器缺少令牌"""
        @require_authentication
        def test_function(session_token=None, user_id=None):
            return {"success": True, "user_id": user_id}
        
        # 执行测试
        result = test_function()
        
        # 验证结果
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_login"])
        self.assertIn("缺少会话令牌", result["error"])
    
    def test_require_schema_permission_success(self):
        """测试schema权限装饰器成功"""
        @require_schema_permission("test_schema", "read")
        def test_function(user_id=None):
            return {"success": True, "user_id": user_id}
        
        # 模拟有权限
        with patch('chatbi.auth.chatbi_integration.get_integration_adapter') as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.permission_filter.check_schema_access.return_value = True
            mock_get_adapter.return_value = mock_adapter
            
            # 执行测试
            result = test_function(user_id="user123")
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["user_id"], "user123")
    
    def test_require_schema_permission_denied(self):
        """测试schema权限装饰器权限被拒绝"""
        @require_schema_permission("test_schema", "write")
        def test_function(user_id=None):
            return {"success": True, "user_id": user_id}
        
        # 模拟无权限
        with patch('chatbi.auth.chatbi_integration.get_integration_adapter') as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.permission_filter.check_schema_access.return_value = False
            mock_get_adapter.return_value = mock_adapter
            
            # 执行测试
            result = test_function(user_id="user123")
        
        # 验证结果
        self.assertFalse(result["success"])
        self.assertTrue(result["permission_denied"])
        self.assertIn("没有权限访问schema 'test_schema'", result["error"])


class TestGlobalIntegrationAdapter(unittest.TestCase):
    """全局集成适配器测试类"""
    
    def test_get_integration_adapter(self):
        """测试获取全局集成适配器"""
        # 清除全局实例
        import chatbi.auth.chatbi_integration
        chatbi.auth.chatbi_integration._integration_adapter = None
        
        # 执行测试
        with patch('chatbi.auth.chatbi_integration.SessionManager'), \
             patch('chatbi.auth.chatbi_integration.PermissionManager'), \
             patch('chatbi.auth.chatbi_integration.AuthDatabase'), \
             patch('chatbi.auth.chatbi_integration.DatabasePermissionFilter'):
            
            adapter1 = get_integration_adapter()
            adapter2 = get_integration_adapter()
        
        # 验证结果
        self.assertIsNotNone(adapter1)
        self.assertIsInstance(adapter1, ChatBIAuthIntegration)
        self.assertIs(adapter1, adapter2)  # 应该是同一个实例


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)