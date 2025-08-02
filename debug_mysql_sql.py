#!/usr/bin/env python3
"""
调试MySQL SQL脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def debug_mysql_sql():
    """调试MySQL SQL脚本"""
    try:
        print("🔍 调试MySQL SQL脚本...")
        
        from chatbi.auth.migrations.create_auth_tables import create_migration_for_db_type
        
        # 获取MySQL迁移
        mysql_migration = create_migration_for_db_type("mysql")
        
        print(f"迁移名称: {mysql_migration.name}")
        print(f"迁移版本: {mysql_migration.version}")
        print(f"SQL长度: {len(mysql_migration.up_sql)} 字符")
        
        # 显示SQL的前500个字符
        print("\nSQL内容预览:")
        print("=" * 50)
        print(mysql_migration.up_sql[:500])
        print("=" * 50)
        
        # 按分号分割并显示每个部分
        parts = mysql_migration.up_sql.split(';')
        print(f"\n按分号分割后有 {len(parts)} 个部分:")
        
        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                print(f"\n部分 {i+1} (长度: {len(part)}):")
                print(f"开始: {part[:50]}...")
                print(f"结束: ...{part[-50:]}")
                
                # 检查是否是注释
                if part.startswith('--') or part.startswith('#'):
                    print("  -> 这是注释")
                elif any(part.upper().startswith(keyword) for keyword in ['CREATE', 'DROP', 'INSERT', 'UPDATE', 'DELETE', 'ALTER']):
                    print("  -> 这是有效的SQL语句")
                else:
                    print("  -> 这可能不是有效的SQL语句")
        
        return True
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_mysql_sql()