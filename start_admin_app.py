#!/usr/bin/env python3
"""
ChatBI 权限管理系统启动脚本
为管理员提供用户权限管理的Web界面
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from chatbi.auth.gradio_admin_app import launch_admin_app
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install gradio pandas")
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
        logger.info("正在启动ChatBI权限管理系统...")
        
        # 启动管理员应用
        launch_admin_app(
            server_name="127.0.0.1",
            server_port=7861,
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