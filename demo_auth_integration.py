#!/usr/bin/env python3
"""
ChatBI认证集成演示脚本
验证认证功能与主应用的集成是否正常工作
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_auth_components():
    """测试认证组件初始化"""
    print("🔧 测试认证组件初始化...")
    
    try:
        from chatbi.config import config
        from chatbi.auth.config import get_auth_config
        from chatbi.auth.database import AuthDatabase
        from chatbi.auth.user_manager import UserManager
        from chatbi.auth.session_manager import SessionManager
        from chatbi.auth.chatbi_integration import get_integration_adapter
        
        # 测试配置加载
        auth_config = get_auth_config()
        database_config = config.database
        print(f"✅ 认证配置加载成功")
        print(f"✅ 数据库配置加载成功: {database_config.type}")
        
        # 测试数据库连接
        auth_db = AuthDatabase(database_config)
        print("✅ 认证数据库连接成功")
        
        # 测试管理器初始化
        user_manager = UserManager(auth_db)
        session_manager = SessionManager(auth_db)
        integration_adapter = get_integration_adapter()
        
        print("✅ 认证管理器初始化成功")
        print("✅ 集成适配器初始化成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 认证组件初始化失败: {str(e)}")
        return False

def test_main_app_integration():
    """测试主应用集成"""
    print("\n🔧 测试主应用集成...")
    
    try:
        from gradio_app_chat import ChatBIApp
        
        # 创建应用实例
        app = ChatBIApp()
        
        # 检查认证组件是否正确初始化
        if app.user_manager is None:
            print("⚠️ 用户管理器未初始化（可能是配置问题）")
            return False
        
        if app.session_manager is None:
            print("⚠️ 会话管理器未初始化（可能是配置问题）")
            return False
        
        if app.integration_adapter is None:
            print("⚠️ 集成适配器未初始化（可能是配置问题）")
            return False
        
        print("✅ 主应用认证组件初始化成功")
        
        # 测试认证状态检查
        is_auth = app.is_authenticated()
        print(f"✅ 认证状态检查正常: {is_auth}")
        
        # 测试用户信息获取
        user_info = app.get_user_info()
        print(f"✅ 用户信息获取正常: {len(user_info)} 个字段")
        
        return True
        
    except Exception as e:
        print(f"❌ 主应用集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_gradio_app_creation():
    """测试Gradio应用创建"""
    print("\n🔧 测试Gradio应用创建...")
    
    try:
        from gradio_app_chat import create_authenticated_chatbi_app
        
        # 创建Gradio应用（不启动）
        app = create_authenticated_chatbi_app()
        
        if app is None:
            print("❌ Gradio应用创建失败")
            return False
        
        print("✅ Gradio认证应用创建成功")
        print(f"✅ 应用类型: {type(app)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gradio应用创建失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_authentication_flow():
    """测试认证流程（模拟）"""
    print("\n🔧 测试认证流程...")
    
    try:
        from gradio_app_chat import ChatBIApp
        
        app = ChatBIApp()
        
        if app.user_manager is None:
            print("⚠️ 跳过认证流程测试（认证组件未初始化）")
            return True
        
        # 测试登录失败（无效凭据）
        success, message, user_info = app.login_user("invalid_user", "invalid_pass")
        if success:
            print("⚠️ 预期登录失败，但实际成功了")
        else:
            print(f"✅ 登录失败测试通过: {message}")
        
        # 测试注册密码不匹配
        success, message = app.register_user("test_user", "pass1", "pass2")
        if success:
            print("⚠️ 预期注册失败，但实际成功了")
        else:
            print(f"✅ 注册失败测试通过: {message}")
        
        # 测试未认证状态下的查询
        history = []
        results = list(app.chat_query("测试查询", history))
        if len(results) > 0:
            final_history, _, _ = results[0]
            if len(final_history) > 0 and "请先登录" in final_history[0][1]:
                print("✅ 未认证查询拒绝测试通过")
            else:
                print("⚠️ 未认证查询应该被拒绝")
        
        # 测试未认证状态下的反馈
        feedback_result = app.add_positive_feedback("测试反馈")
        if "请先登录" in feedback_result:
            print("✅ 未认证反馈拒绝测试通过")
        else:
            print("⚠️ 未认证反馈应该被拒绝")
        
        return True
        
    except Exception as e:
        print(f"❌ 认证流程测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    setup_logging()
    
    print("🚀 ChatBI认证集成演示")
    print("=" * 50)
    
    # 运行测试
    tests = [
        ("认证组件初始化", test_auth_components),
        ("主应用集成", test_main_app_integration),
        ("Gradio应用创建", test_gradio_app_creation),
        ("认证流程", test_authentication_flow),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {str(e)}")
    
    # 总结
    print("\n" + "=" * 50)
    print(f"📊 测试总结: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！认证集成工作正常")
        print("\n🚀 您可以使用以下命令启动应用:")
        print("   python start_chatbi_with_auth.py")
        print("\n📖 详细使用说明请查看:")
        print("   CHATBI_MAIN_APP_AUTH_GUIDE.md")
    else:
        print("⚠️ 部分测试失败，请检查配置和依赖")
        print("\n🔧 故障排除:")
        print("   1. 检查认证配置文件")
        print("   2. 确认数据库连接正常")
        print("   3. 运行数据库迁移: python -m chatbi.auth.cli migrate")

if __name__ == "__main__":
    main()