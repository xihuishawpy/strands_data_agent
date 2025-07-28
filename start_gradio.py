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
    print("🚀 正在启动ChatBI Gradio界面...")
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查配置文件
    if not os.path.exists('.env'):
        print("⚠️  未找到.env配置文件")
        print("请确保已正确配置数据库连接和API密钥")
    
    # 启动Gradio应用
    try:
        from gradio_app import create_gradio_interface
        
        interface = create_gradio_interface()
        print("✅ 界面创建成功")
        print("🌐 访问地址: http://localhost:7860")
        
        interface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 