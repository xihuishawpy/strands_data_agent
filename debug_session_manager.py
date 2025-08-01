#!/usr/bin/env python3
"""
调试SessionManager初始化问题
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def debug_session_manager():
    """调试SessionManager初始化"""
    try:
        from chatbi.config import config
        from chatbi.auth.database import AuthDatabase
        from chatbi.auth.session_manager import SessionManager
        
        print("1. 导入成功")
        
        # 检查SessionManager类
        print(f"2. SessionManager类: {SessionManager}")
        print(f"3. SessionManager.__init__: {SessionManager.__init__}")
        
        # 检查__init__方法的签名
        import inspect
        sig = inspect.signature(SessionManager.__init__)
        print(f"4. __init__方法签名: {sig}")
        
        # 创建数据库实例
        database_config = config.database
        auth_db = AuthDatabase(database_config)
        print("5. AuthDatabase创建成功")
        
        # 尝试创建SessionManager
        session_manager = SessionManager(auth_db)
        print("6. SessionManager创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_session_manager()