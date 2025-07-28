#!/usr/bin/env python3
"""
ChatBI Gradio界面启动脚本
"""

import subprocess
import sys
import os

def check_dependencies():
    """检查依赖包"""
    required_packages = ['gradio', 'openai', 'plotly', 'pandas']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    # 检查plotly.express
    try:
        import plotly.express as px
        import plotly.graph_objects as go
    except ImportError:
        if 'plotly' not in missing:
            missing.append('plotly')
    
    if missing:
        print(f"❌ 缺少依赖包: {', '.join(missing)}")
        print(f"请运行: pip install {' '.join(missing)}")
        return False
    
    print("✅ 所有依赖包检查通过")
    return True

def main():
    """主函数"""
    print("🚀 ChatBI Gradio界面启动器")
    print("=" * 40)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查配置文件
    if not os.path.exists('.env'):
        print("⚠️  未找到.env配置文件")
        print("请确保已正确配置数据库连接和API密钥")
    
    # 选择界面类型
    print("\n请选择界面类型:")
    print("1. 💬 对话式界面 (推荐) - 人机交互式对话体验")
    print("2. 📋 传统界面 - 多标签页功能界面")
    
    while True:
        choice = input("\n请输入选择 (1/2): ").strip()
        
        if choice == "1":
            print("🚀 启动对话式界面...")
            try:
                from gradio_app_chat import create_chat_interface
                interface = create_chat_interface()
                interface_type = "对话式"
                break
            except Exception as e:
                print(f"❌ 对话式界面启动失败: {e}")
                sys.exit(1)
                
        elif choice == "2":
            print("🚀 启动传统界面...")
            try:
                from gradio_app import create_gradio_interface
                interface = create_gradio_interface()
                interface_type = "传统"
                break
            except Exception as e:
                print(f"❌ 传统界面启动失败: {e}")
                sys.exit(1)
        else:
            print("❌ 无效选择，请输入 1 或 2")
    
    print(f"✅ {interface_type}界面创建成功")
    print("🌐 访问地址: http://localhost:7860")
    print("📖 使用说明请查看对应的README文件")
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True
    )

if __name__ == "__main__":
    main() 