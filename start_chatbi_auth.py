#!/usr/bin/env python3
"""
ChatBI 带认证功能的应用启动脚本
启动带用户认证和权限管理的智能数据查询系统
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gradio_app_chat_auth import launch_authenticated_app
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install gradio pandas plotly")
    sys.exit(1)


def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("正在启动ChatBI认证应用...")
        
        print("=" * 60)
        print("🤖 ChatBI 智能数据查询系统 (认证版)")
        print("=" * 60)
        print("📋 系统功能:")
        print("  ✅ 用户注册和登录认证")
        print("  ✅ 基于权限的数据访问控制")
        print("  ✅ 自然语言智能查询")
        print("  ✅ 自动数据可视化")
        print("  ✅ 智能数据分析")
        print("  ✅ 查询反馈和优化")
        print("=" * 60)
        print("🔐 安全特性:")
        print("  ✅ Schema级别权限控制")
        print("  ✅ SQL查询权限验证")
        print("  ✅ 会话管理和超时")
        print("  ✅ 操作审计日志")
        print("=" * 60)
        print("📖 使用说明:")
        print("  1. 首次使用请先注册账户")
        print("  2. 注册需要在允许的工号白名单中")
        print("  3. 登录后即可进行智能查询")
        print("  4. 系统会根据权限自动过滤数据")
        print("=" * 60)
        
        # 启动应用
        launch_authenticated_app(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            debug=True
        )
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭应用...")
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()