#!/usr/bin/env python3
"""
快速启动登录门禁版ChatBI应用
包含完整的功能模块集成
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """快速启动主函数"""
    print("🚀 快速启动ChatBI登录门禁版")
    print("=" * 50)
    
    # 检查环境
    print("🔧 检查运行环境...")
    
    try:
        # 测试基础导入
        import gradio as gr
        print("✅ Gradio环境正常")
        
        from gradio_app_chat import ChatBIApp
        print("✅ ChatBI核心模块正常")
        
        from gradio_app_login_gate import launch_login_gate_app
        print("✅ 登录门禁模块正常")
        
    except ImportError as e:
        print(f"❌ 环境检查失败: {e}")
        print("\n💡 解决方案:")
        print("1. 确保已安装所有依赖: pip install gradio openai")
        print("2. 检查ChatBI项目结构是否完整")
        print("3. 确保在正确的项目目录中运行")
        return False
    
    print("\n🎯 启动配置:")
    print("  📍 服务器地址: 127.0.0.1")
    print("  🔌 端口: 7861")
    print("  🔐 认证: 必须登录")
    print("  📊 功能: 完整集成")
    
    print("\n📋 集成功能模块:")
    print("  💬 智能数据查询和分析")
    print("  🐬 SQL知识库管理")
    print("  📝 表信息维护")
    print("  ℹ️ 系统信息管理")
    
    print("\n🔑 使用说明:")
    print("  1. 首次访问会看到全屏登录界面")
    print("  2. 可以注册新账户或使用现有账户登录")
    print("  3. 登录成功后自动进入主应用界面")
    print("  4. 所有功能都在标签页中组织")
    
    print("\n" + "=" * 50)
    print("🌐 正在启动应用...")
    
    try:
        # 启动应用
        launch_login_gate_app(
            server_name="127.0.0.1",
            server_port=7861,
            share=False,
            debug=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在关闭应用...")
    except Exception as e:
        print(f"\n❌ 启动失败: {str(e)}")
        print("\n💡 故障排除:")
        print("1. 检查端口7861是否被占用")
        print("2. 确保数据库配置正确")
        print("3. 查看详细错误日志")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)