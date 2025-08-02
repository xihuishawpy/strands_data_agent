#!/usr/bin/env python3
"""
清除权限缓存脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from chatbi.config import config
from chatbi.auth import AuthDatabase, PermissionManager

def clear_cache():
    """清除权限缓存"""
    try:
        print("🧹 清除权限缓存...")
        
        # 初始化组件
        auth_database = AuthDatabase(config.database)
        permission_manager = PermissionManager(auth_database)
        
        # 清除缓存
        permission_manager._permission_cache.clear()
        print("✅ 权限缓存已清除")
        
        # 显示缓存状态
        print(f"📊 当前缓存大小: {len(permission_manager._permission_cache)}")
        
    except Exception as e:
        print(f"❌ 清除缓存时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clear_cache()