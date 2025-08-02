#!/usr/bin/env python3
"""
清理认证系统数据库表
用于重新初始化认证系统
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from chatbi.config import config
from chatbi.auth import AuthDatabase

def cleanup_auth_tables():
    """清理认证系统表"""
    print("🧹 开始清理认证系统数据库表...")
    
    try:
        # 初始化认证数据库
        auth_database = AuthDatabase(config.database)
        
        # 获取数据库连接
        conn = auth_database.get_connection()
        cursor = conn.cursor()
        
        # 删除表的顺序很重要，需要先删除有外键依赖的表
        tables_to_drop = [
            "login_attempts",
            "audit_logs", 
            "user_sessions",
            "user_permissions",
            "allowed_employees",
            "users",
            "auth_migrations"  # 迁移记录表
        ]
        
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  ✅ 删除表: {table}")
            except Exception as e:
                print(f"  ⚠️ 删除表 {table} 失败: {str(e)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("🎉 认证系统数据库表清理完成！")
        print("💡 现在可以运行 python init_auth_system.py 重新初始化")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = cleanup_auth_tables()
    sys.exit(0 if success else 1)