#!/usr/bin/env python3
"""
测试Schema获取功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_schema():
    """测试Schema获取"""
    try:
        from chatbi.database import get_schema_manager
        
        print("🔍 开始测试Schema管理器...")
        
        schema_manager = get_schema_manager()
        print("✅ Schema管理器创建成功")
        
        # 测试获取表名
        print("\n📋 获取表名列表...")
        tables = schema_manager.get_all_tables()
        print(f"表名类型: {type(tables)}")
        print(f"表名列表: {tables}")
        
        if tables:
            # 测试获取单个表的Schema
            print(f"\n🔍 获取表 '{tables[0]}' 的Schema...")
            table_schema = schema_manager.get_table_schema(tables[0])
            print(f"表Schema类型: {type(table_schema)}")
            print(f"表Schema内容: {table_schema}")
            
            # 测试获取完整数据库Schema
            print(f"\n🗄️ 获取完整数据库Schema...")
            db_schema = schema_manager.get_database_schema()
            print(f"数据库Schema类型: {type(db_schema)}")
            print(f"数据库Schema键: {list(db_schema.keys()) if isinstance(db_schema, dict) else 'Not a dict'}")
            
            if isinstance(db_schema, dict) and "tables" in db_schema:
                print(f"包含的表: {list(db_schema['tables'].keys())}")
                if db_schema['tables']:
                    first_table = list(db_schema['tables'].keys())[0]
                    first_table_info = db_schema['tables'][first_table]
                    print(f"第一个表 '{first_table}' 信息类型: {type(first_table_info)}")
                    print(f"第一个表信息键: {list(first_table_info.keys()) if isinstance(first_table_info, dict) else 'Not a dict'}")
        
        print("\n✅ Schema测试完成")
        return True
        
    except Exception as e:
        print(f"❌ Schema测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_schema() 