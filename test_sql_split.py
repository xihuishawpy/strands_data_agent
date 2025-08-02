#!/usr/bin/env python3
"""
测试SQL语句分割
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_sql_split():
    """测试SQL语句分割"""
    try:
        print("🔍 测试SQL语句分割...")
        
        from chatbi.auth.migrations.create_auth_tables import create_migration_for_db_type
        
        # 获取MySQL迁移
        mysql_migration = create_migration_for_db_type("mysql")
        
        # 分割SQL语句
        sql_statements = []
        for sql_statement in mysql_migration.up_sql.split(';'):
            sql_statement = sql_statement.strip()
            # 跳过空语句和注释
            if sql_statement and not sql_statement.startswith('--') and not sql_statement.startswith('#'):
                sql_statements.append(sql_statement)
        
        print(f"✅ 分割出 {len(sql_statements)} 个SQL语句")
        
        # 检查每个语句
        for i, stmt in enumerate(sql_statements):
            print(f"   语句 {i+1}: {stmt[:50]}...")
            
            # 检查是否是有效的SQL语句
            if any(stmt.upper().startswith(keyword) for keyword in ['CREATE', 'DROP', 'INSERT', 'UPDATE', 'DELETE', 'ALTER']):
                print(f"     ✅ 有效的SQL语句")
            else:
                print(f"     ❌ 可能无效的SQL语句")
                return False
        
        return True
    except Exception as e:
        print(f"❌ SQL分割测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试SQL语句分割...")
    
    success = test_sql_split()
    
    if success:
        print("\n🎉 SQL分割测试通过！")
    else:
        print("\n❌ SQL分割测试失败！")
    
    sys.exit(0 if success else 1)