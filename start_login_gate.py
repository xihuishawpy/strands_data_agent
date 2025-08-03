#!/usr/bin/env python3
"""
启动登录门禁版ChatBI应用
用户必须通过登录门禁才能访问应用
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from gradio_app_login_gate import launch_login_gate_app


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动登录门禁版ChatBI应用")
    
    parser.add_argument(
        "--host", 
        default="127.0.0.1", 
        help="服务器地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=7861, 
        help="服务器端口 (默认: 7861)"
    )
    parser.add_argument(
        "--share", 
        action="store_true", 
        help="创建公共链接"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="启用调试模式"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 ChatBI 登录门禁版 - 完整功能集成")
    print("=" * 60)
    print("🔐 用户认证模型已放置在访问界面最前端")
    print("📱 用户必须先登录才能访问应用功能")
    print("🎨 采用全屏登录界面设计")
    print("📊 集成所有ChatBI功能模块：")
    print("   - 💬 智能数据查询和分析")
    print("   - 🐬 SQL知识库管理")
    print("   - 📝 表信息维护")
    print("   - ℹ️ 系统信息管理")
    print("=" * 60)
    print()
    
    try:
        launch_login_gate_app(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            debug=args.debug
        )
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在关闭应用...")
    except Exception as e:
        print(f"\n❌ 启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()