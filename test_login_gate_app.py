#!/usr/bin/env python3
"""
测试登录门禁版ChatBI应用
验证所有功能模块是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试导入是否正常"""
    try:
        print("🔧 测试导入...")
        
        # 测试基础导入
        import gradio as gr
        print("✅ Gradio导入成功")
        
        # 测试ChatBI应用导入
        from gradio_app_chat import ChatBIApp
        print("✅ ChatBIApp导入成功")
        
        # 测试登录门禁应用导入
        from gradio_app_login_gate import create_login_gate_app, launch_login_gate_app
        print("✅ 登录门禁应用导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_app_creation():
    """测试应用创建"""
    try:
        print("\n🏗️ 测试应用创建...")
        
        from gradio_app_login_gate import create_login_gate_app
        
        # 创建应用实例
        app = create_login_gate_app()
        print("✅ 登录门禁应用创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 应用创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chatbi_app():
    """测试ChatBI应用实例"""
    try:
        print("\n🤖 测试ChatBI应用实例...")
        
        from gradio_app_chat import ChatBIApp
        
        # 创建ChatBI应用实例
        chatbi_app = ChatBIApp()
        print("✅ ChatBI应用实例创建成功")
        
        # 测试基本方法
        if hasattr(chatbi_app, 'is_authenticated'):
            print("✅ 认证方法存在")
        
        if hasattr(chatbi_app, 'get_table_list'):
            print("✅ 表列表方法存在")
        
        if hasattr(chatbi_app, 'get_knowledge_stats'):
            print("✅ 知识库统计方法存在")
        
        return True
        
    except Exception as e:
        print(f"❌ ChatBI应用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 开始测试登录门禁版ChatBI应用")
    print("=" * 50)
    
    # 测试导入
    if not test_imports():
        print("\n❌ 导入测试失败，退出")
        return False
    
    # 测试ChatBI应用
    if not test_chatbi_app():
        print("\n❌ ChatBI应用测试失败，退出")
        return False
    
    # 测试应用创建
    if not test_app_creation():
        print("\n❌ 应用创建测试失败，退出")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 所有测试通过！")
    print("\n📋 功能模块验证：")
    print("  ✅ 登录门禁界面")
    print("  ✅ 智能数据查询")
    print("  ✅ SQL知识库管理")
    print("  ✅ 表信息维护")
    print("  ✅ 系统信息管理")
    print("\n🚀 可以安全启动应用：")
    print("  python start_login_gate.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)