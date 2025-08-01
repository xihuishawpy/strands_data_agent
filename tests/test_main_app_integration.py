#!/usr/bin/env python3
"""
测试主应用集成功能
验证认证功能与ChatBI主应用的集成是否正常工作
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from gradio_app_chat import ChatBIApp, create_authenticated_chatbi_app
    from chatbi.auth import UserManager, SessionManager, AuthDatabase
    from chatbi.auth.models import User, UserSession
    from chatbi.auth.database import AuthDatabase
    from chatbi.orchestrator import QueryResult
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖并正确配置环境")
    sys.exit(1)


class TestMainAppIntegration(unittest.TestCase):
    """测试主应用集成功能"""
    
    @patch('gradio_app_chat.config')
    @patch('gradio_app_chat.AuthDatabase')
    @patch('gradio_app_chat.UserManager')
    @patch('gradio_app_chat.SessionManager')
    @patch('gradio_app_chat.get_integration_adapter')
    def setUp(self, mock_get_adapter, mock_session_manager, mock_user_manager, 
              mock_auth_database, mock_config):
        """设置测试环境"""
        # Mock数据库配置
        mock_database_config = Mock()
        mock_config.database = mock_database_config
        
        # Mock认证组件
        self.mock_user_manager = Mock(spec=UserManager)
        self.mock_session_manager = Mock(spec=SessionManager)
        self.mock_auth_database = Mock(spec=AuthDatabase)
        self.mock_integration_adapter = Mock()
        
        mock_user_manager.return_value = self.mock_user_manager
        mock_session_manager.return_value = self.mock_session_manager
        mock_auth_database.return_value = self.mock_auth_database
        mock_get_adapter.return_value = self.mock_integration_adapter
        
        # 创建应用实例
        self.app = ChatBIApp()
        
        # Mock基础组件
        self.app.base_orchestrator = Mock()
        self.app.connector = Mock()
        self.app.schema_manager = Mock()
        self.app.metadata_manager = Mock()
    
    def test_user_login_success(self):
        """测试用户登录成功"""
        # 准备测试数据
        test_user = User(
            id="test-user-id",
            employee_id="EMP001",
            full_name="测试用户",
            email="test@example.com",
            is_admin=False,
            is_active=True
        )
        
        # Mock认证结果
        auth_result = Mock()
        auth_result.success = True
        auth_result.user = test_user
        self.mock_user_manager.authenticate_user.return_value = auth_result
        
        # Mock会话创建结果
        session_result = Mock()
        session_result.success = True
        session_result.token = "test-session-token"
        self.mock_session_manager.create_session.return_value = session_result
        
        # Mock集成适配器
        mock_orchestrator = Mock()
        self.mock_integration_adapter.wrap_orchestrator.return_value = mock_orchestrator
        
        # 执行登录
        success, message, user_info = self.app.login_user("EMP001", "password123")
        
        # 验证结果
        self.assertTrue(success)
        self.assertIn("欢迎", message)
        self.assertEqual(user_info["employee_id"], "EMP001")
        self.assertEqual(user_info["full_name"], "测试用户")
        self.assertEqual(user_info["email"], "test@example.com")
        self.assertFalse(user_info["is_admin"])
        
        # 验证应用状态
        self.assertEqual(self.app.current_user, test_user)
        self.assertEqual(self.app.current_session_token, "test-session-token")
        self.assertEqual(self.app.authenticated_orchestrator, mock_orchestrator)
        self.assertTrue(self.app.is_authenticated())
    
    def test_user_login_failure(self):
        """测试用户登录失败"""
        # Mock认证失败结果
        auth_result = Mock()
        auth_result.success = False
        auth_result.message = "用户名或密码错误"
        self.mock_user_manager.authenticate_user.return_value = auth_result
        
        # 执行登录
        success, message, user_info = self.app.login_user("EMP001", "wrong_password")
        
        # 验证结果
        self.assertFalse(success)
        self.assertIn("登录失败", message)
        self.assertEqual(user_info, {})
        
        # 验证应用状态
        self.assertIsNone(self.app.current_user)
        self.assertIsNone(self.app.current_session_token)
        self.assertIsNone(self.app.authenticated_orchestrator)
        self.assertFalse(self.app.is_authenticated())
    
    def test_user_logout(self):
        """测试用户登出"""
        # 设置已登录状态
        self.app.current_user = Mock()
        self.app.current_session_token = "test-token"
        self.app.authenticated_orchestrator = Mock()
        self.app.chat_history = [{"test": "data"}]
        self.app.last_query_result = Mock()
        
        # 执行登出
        success, message = self.app.logout_user()
        
        # 验证结果
        self.assertTrue(success)
        self.assertIn("成功登出", message)
        
        # 验证状态清除
        self.assertIsNone(self.app.current_user)
        self.assertIsNone(self.app.current_session_token)
        self.assertIsNone(self.app.authenticated_orchestrator)
        self.assertEqual(self.app.chat_history, [])
        self.assertIsNone(self.app.last_query_result)
        self.assertFalse(self.app.is_authenticated())
        
        # 验证会话销毁被调用
        self.mock_session_manager.invalidate_session.assert_called_once_with("test-token")
    
    def test_user_registration_success(self):
        """测试用户注册成功"""
        # Mock注册结果
        registration_result = Mock()
        registration_result.success = True
        registration_result.user_id = "new-user-id"
        self.mock_user_manager.register_user.return_value = registration_result
        
        # 执行注册
        success, message = self.app.register_user(
            "EMP002", "password123", "password123", "test2@example.com", "新用户"
        )
        
        # 验证结果
        self.assertTrue(success)
        self.assertIn("注册成功", message)
        self.assertIn("new-user-id", message)
        
        # 验证调用参数
        self.mock_user_manager.register_user.assert_called_once_with(
            employee_id="EMP002",
            password="password123",
            email="test2@example.com",
            full_name="新用户"
        )
    
    def test_user_registration_password_mismatch(self):
        """测试用户注册密码不匹配"""
        # 执行注册
        success, message = self.app.register_user(
            "EMP002", "password123", "different_password", "test2@example.com", "新用户"
        )
        
        # 验证结果
        self.assertFalse(success)
        self.assertIn("密码不一致", message)
        
        # 验证没有调用注册方法
        self.mock_user_manager.register_user.assert_not_called()
    
    def test_chat_query_without_authentication(self):
        """测试未认证用户进行查询"""
        # 确保未认证状态
        self.app.current_user = None
        self.app.current_session_token = None
        self.app.authenticated_orchestrator = None
        
        # 执行查询
        history = []
        results = list(self.app.chat_query("测试查询", history))
        
        # 验证结果
        self.assertEqual(len(results), 1)
        final_history, msg_input, plot_output = results[0]
        
        self.assertEqual(len(final_history), 1)
        self.assertEqual(final_history[0][0], "测试查询")
        self.assertIn("请先登录", final_history[0][1])
    
    def test_chat_query_with_authentication(self):
        """测试已认证用户进行查询"""
        # 设置已认证状态
        self.app.current_user = Mock()
        self.app.current_user.employee_id = "EMP001"
        self.app.current_session_token = "test-token"
        
        # Mock认证包装器
        mock_orchestrator = Mock()
        self.app.authenticated_orchestrator = mock_orchestrator
        
        # Mock查询结果
        mock_result = Mock(spec=QueryResult)
        mock_result.success = True
        mock_result.question = "测试查询"
        mock_result.sql_query = "SELECT * FROM test_table"
        mock_result.data = [{"id": 1, "name": "测试"}]
        mock_result.analysis = "测试分析"
        mock_result.chart_info = None
        mock_result.error = None
        mock_result.execution_time = 1.5
        mock_result.metadata = {"row_count": 1}
        mock_result.accessible_schemas = ["test_schema"]
        
        # Mock流式查询
        def mock_query_stream(*args, **kwargs):
            yield {"step_info": "正在处理..."}
            yield {"final_result": mock_result}
        
        mock_orchestrator.query_stream = mock_query_stream
        
        # 执行查询
        history = []
        results = list(self.app.chat_query("测试查询", history))
        
        # 验证有结果返回
        self.assertGreater(len(results), 0)
        
        # 验证最终结果
        final_history, msg_input, plot_output = results[-1]
        self.assertEqual(len(final_history), 1)
        self.assertEqual(final_history[0][0], "测试查询")
        self.assertIn("查询完成", final_history[0][1])
        self.assertIn("EMP001", final_history[0][1])
    
    def test_add_positive_feedback_without_authentication(self):
        """测试未认证用户添加反馈"""
        # 确保未认证状态
        self.app.current_user = None
        
        # 执行反馈
        result = self.app.add_positive_feedback("测试反馈")
        
        # 验证结果
        self.assertIn("请先登录", result)
    
    def test_add_positive_feedback_with_authentication(self):
        """测试已认证用户添加反馈"""
        # 设置已认证状态
        self.app.current_user = Mock()
        self.app.current_user.employee_id = "EMP001"
        self.app.authenticated_orchestrator = Mock()
        
        # 设置查询结果
        mock_result = Mock()
        mock_result.success = True
        mock_result.question = "测试查询"
        mock_result.sql_query = "SELECT * FROM test"
        self.app.last_query_result = mock_result
        
        # Mock反馈添加成功
        self.app.authenticated_orchestrator.add_positive_feedback.return_value = True
        
        # 执行反馈
        result = self.app.add_positive_feedback("很好的查询")
        
        # 验证结果
        self.assertIn("感谢反馈", result)
        
        # 验证调用参数
        self.app.authenticated_orchestrator.add_positive_feedback.assert_called_once_with(
            question="测试查询",
            sql="SELECT * FROM test",
            description="很好的查询"
        )
    
    def test_get_user_info(self):
        """测试获取用户信息"""
        # 设置用户
        from datetime import datetime
        test_user = Mock()
        test_user.employee_id = "EMP001"
        test_user.full_name = "测试用户"
        test_user.email = "test@example.com"
        test_user.is_admin = True
        test_user.is_active = True
        test_user.created_at = datetime(2024, 1, 1)
        
        self.app.current_user = test_user
        
        # 获取用户信息
        user_info = self.app.get_user_info()
        
        # 验证结果
        self.assertEqual(user_info["employee_id"], "EMP001")
        self.assertEqual(user_info["full_name"], "测试用户")
        self.assertEqual(user_info["email"], "test@example.com")
        self.assertTrue(user_info["is_admin"])
        self.assertTrue(user_info["is_active"])
        self.assertEqual(user_info["created_at"], "2024-01-01")
    
    def test_get_user_info_no_user(self):
        """测试未登录时获取用户信息"""
        self.app.current_user = None
        
        # 获取用户信息
        user_info = self.app.get_user_info()
        
        # 验证结果
        self.assertEqual(user_info, {})
    
    @patch('gradio_app_chat.gr.Blocks')
    def test_create_authenticated_app(self, mock_blocks):
        """测试创建认证应用"""
        # Mock Gradio组件
        mock_app = Mock()
        mock_blocks.return_value.__enter__.return_value = mock_app
        
        # 创建应用
        result = create_authenticated_chatbi_app()
        
        # 验证创建成功
        self.assertIsNotNone(result)
        mock_blocks.assert_called_once()


class TestAuthenticationFlow(unittest.TestCase):
    """测试认证流程"""
    
    @patch('gradio_app_chat.config')
    @patch('gradio_app_chat.AuthDatabase')
    @patch('gradio_app_chat.UserManager')
    @patch('gradio_app_chat.SessionManager')
    @patch('gradio_app_chat.get_integration_adapter')
    def test_complete_authentication_flow(self, mock_get_adapter, mock_session_manager, 
                                        mock_user_manager, mock_auth_db, mock_config):
        """测试完整的认证流程"""
        # Mock数据库配置
        mock_database_config = Mock()
        mock_config.database = mock_database_config
        
        # 设置Mock
        mock_user_mgr = Mock()
        mock_session_mgr = Mock()
        mock_auth_database = Mock()
        mock_adapter = Mock()
        
        mock_user_manager.return_value = mock_user_mgr
        mock_session_manager.return_value = mock_session_mgr
        mock_auth_db.return_value = mock_auth_database
        mock_get_adapter.return_value = mock_adapter
        
        # 创建新的应用实例
        app = ChatBIApp()
        
        # 验证组件初始化
        self.assertEqual(app.user_manager, mock_user_mgr)
        self.assertEqual(app.session_manager, mock_session_mgr)
        self.assertEqual(app.auth_database, mock_auth_database)
        self.assertEqual(app.integration_adapter, mock_adapter)
        
        # 验证初始状态
        self.assertIsNone(app.current_user)
        self.assertIsNone(app.current_session_token)
        self.assertIsNone(app.authenticated_orchestrator)
        self.assertFalse(app.is_authenticated())


if __name__ == '__main__':
    # 设置日志
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    unittest.main(verbosity=2)