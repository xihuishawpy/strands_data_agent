#!/usr/bin/env python3
"""
测试对话式界面的基本功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_chat_app():
    """测试ChatBIApp基本功能"""
    try:
        from gradio_app_chat import ChatBIApp
        print("✅ ChatBIApp 导入成功")
        
        app = ChatBIApp()
        print("✅ ChatBIApp 初始化成功")
        
        # 测试基本方法
        test_history = []
        
        # 测试空消息
        result = app.chat_query("", test_history)
        print(f"✅ 空消息测试: {len(result)} 个返回值")
        
        # 测试系统管理功能
        conn_result = app.test_connection()
        print(f"✅ 连接测试: {len(conn_result)} 个返回值")
        
        schema_result = app.get_schema_info()
        print(f"✅ Schema获取: {len(schema_result)} 个返回值")
        
        print("🎉 ChatBIApp 基本功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_interface_creation():
    """测试界面创建"""
    try:
        from gradio_app_chat import create_chat_interface
        print("✅ create_chat_interface 导入成功")
        
        # 注意：这里不实际创建界面，只测试导入
        print("✅ 界面创建函数可用")
        return True
        
    except Exception as e:
        print(f"❌ 界面创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 开始测试ChatBI对话式界面...")
    print("=" * 50)
    
    success = True
    
    # 测试应用类
    if not test_chat_app():
        success = False
    
    print("-" * 30)
    
    # 测试界面创建
    if not test_interface_creation():
        success = False
    
    print("=" * 50)
    
    if success:
        print("🎉 所有测试通过！对话式界面应该可以正常使用")
        print("💡 运行 'python start_chat_ui.py' 启动界面")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    
    return success

if __name__ == "__main__":
    main()