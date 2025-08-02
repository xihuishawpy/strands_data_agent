#!/usr/bin/env python3
"""
测试SQL解析逻辑
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_sql_parse():
    """测试SQL解析"""
    try:
        print("🔍 测试SQL解析...")
        
        from chatbi.config import config
        from chatbi.auth.migrations.migration_manager import MigrationManager
        from chatbi.auth.migrations.create_auth_tables import create_migration_for_db_type
        
        # 创建迁移管理器
        migration_manager = MigrationManager(config.database)
        
        # 获取MySQL迁移
        mysql_migration = create_migration_for_db_type("mysql")
        
        # 使用新的解析方法
        sql_statements = migration_manager._parse_sql_statements(mysql_migration.up_sql)
        
        print(f"✅ 解析出 {len(sql_statements)} 个有效SQL语句")
        
        # 检查每个语句
        for i, stmt in enumerate(sql_statements):
            print(f"   语句 {i+1}: {stmt[:80]}...")
            
            # 检查是否是有效的SQL语句
            if any(stmt.upper().startswith(keyword) for keyword in ['CREATE', 'DROP', 'INSERT', 'UPDATE', 'DELETE', 'ALTER']):
                print(f"     ✅ 有效的SQL语句")
            else:
                print(f"     ❌ 可能无效的SQL语句: {stmt[:100]}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ SQL解析测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试SQL解析...")
    
    success = test_sql_parse()
    
    if success:
        print("\n🎉 SQL解析测试通过！")
    else:
        print("\n❌ SQL解析测试失败！")
    
    sys.exit(0 if success else 1)