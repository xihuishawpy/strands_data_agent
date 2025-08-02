#!/usr/bin/env python3
"""
测试迁移脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_migration_sql():
    """测试迁移SQL"""
    try:
        print("🔍 测试迁移SQL...")
        
        from chatbi.auth.migrations.create_auth_tables import create_migration_for_db_type
        
        # 测试MySQL迁移
        mysql_migration = create_migration_for_db_type("mysql")
        print("✅ MySQL迁移创建成功")
        print(f"   版本: {mysql_migration.version}")
        print(f"   名称: {mysql_migration.name}")
        
        # 检查SQL是否包含正确的MySQL语法
        if "ENGINE=InnoDB" in mysql_migration.up_sql:
            print("✅ MySQL SQL语法正确")
        else:
            print("❌ MySQL SQL语法可能有问题")
            return False
        
        # 检查是否不包含SQLite特有的语法
        if "CREATE INDEX IF NOT EXISTS" not in mysql_migration.up_sql:
            print("✅ 没有SQLite特有的语法")
        else:
            print("❌ 包含SQLite特有的语法")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 迁移SQL测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_migration_manager():
    """测试迁移管理器"""
    try:
        print("🔍 测试迁移管理器...")
        
        from chatbi.config import config
        from chatbi.auth.migrations.migration_manager import MigrationManager
        
        # 创建迁移管理器
        migration_manager = MigrationManager(config.database)
        print("✅ 迁移管理器创建成功")
        
        # 检查是否注册了迁移
        if "001" in migration_manager.migrations:
            print("✅ 迁移已注册")
            migration = migration_manager.migrations["001"]
            print(f"   迁移名称: {migration.name}")
            print(f"   数据库类型: {config.database.type}")
        else:
            print("❌ 迁移未注册")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 迁移管理器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试迁移脚本...")
    
    success = True
    success &= test_migration_sql()
    success &= test_migration_manager()
    
    if success:
        print("\n🎉 迁移测试通过！")
    else:
        print("\n❌ 迁移测试失败！")
    
    sys.exit(0 if success else 1)