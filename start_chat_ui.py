#!/usr/bin/env python3
"""
启动ChatBI对话式界面
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from gradio_app_chat import create_chat_interface
from chatbi.config import config

def main():
    """启动对话式界面"""
    print("🚀 启动ChatBI对话式界面...")
    print(f"📊 数据库类型: {config.database.type}")
    print(f"🤖 AI模型: {config.llm.model_name}")
    print("=" * 50)
    
    # 创建并启动界面
    interface = create_chat_interface()
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=False,
        show_error=True,
        inbrowser=True  # 自动打开浏览器
    )

if __name__ == "__main__":
    main()