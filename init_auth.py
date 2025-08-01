#!/usr/bin/env python3
"""
认证模块初始化脚本
用于快速初始化认证数据库和创建管理员用户
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbi.auth.cli import main

if __name__ == '__main__':
    main()