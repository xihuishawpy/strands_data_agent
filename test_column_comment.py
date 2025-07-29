#!/usr/bin/env python3
"""
测试字段备注更新功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from chatbi.database import get_global_connector

def test_column_comment_update():
    """测试字段备注更新功能"""
    print("🔧 测试字段备注更新功能")
    print("=" * 60)
    
    try:
        # 获取数据库连接器
        connector = get_global_connector()
        
        if not connector.is_connected:
            print("❌ 数据库连接失败")
            return False
        
        print("✅ 数据库连接成功")
        
        # 获取表列表
        tables = connector.get_tables()
        if not tables:
            print("❌ 没有找到任何表")
            return False
        
        print(f"📋 找到 {len(tables)} 个表: {', '.join(tables)}")
        
        # 选择第一个表进行测试
        test_table = tables[0]
        print(f"🎯 使用表 '{test_table}' 进行测试")
        
        # 获取表结构
        schema = connector.get_table_schema(test_table)
        columns = schema.get("columns", [])
        
        if not columns:
            print(f"❌ 表 {test_table} 没有字段")
            return False
        
        # 选择第一个字段进行测试
        test_column = columns[0]
        column_name = test_column["name"]
        original_comment = test_column.get("comment", "")
        
        print(f"🎯 测试字段: {column_name}")
        print(f"📝 原始备注: '{original_comment}'")
        
        # 更新字段备注
        new_comment = f"测试备注更新 - {original_comment}" if original_comment else "测试备注更新"
        print(f"🔄 更新备注为: '{new_comment}'")
        
        # 执行更新
        if hasattr(connector, 'update_column_comment'):
            success = connector.update_column_comment(test_table, column_name, new_comment)
            
            if success:
                print("✅ 字段备注更新成功")
                
                # 验证更新结果
                print("🔍 验证更新结果...")
                updated_schema = connector.get_table_schema(test_table)
                updated_columns = updated_schema.get("columns", [])
                
                for col in updated_columns:
                    if col["name"] == column_name:
                        updated_comment = col.get("comment", "")
                        print(f"📝 更新后备注: '{updated_comment}'")
                        
                        if updated_comment == new_comment:
                            print("✅ 备注更新验证成功")
                            return True
                        else:
                            print("❌ 备注更新验证失败")
                            return False
                
                print("❌ 未找到更新后的字段")
                return False
            else:
                print("❌ 字段备注更新失败")
                return False
        else:
            print("❌ 连接器不支持 update_column_comment 方法")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_column_comment_update()
    
    if success:
        print("\n🎉 字段备注更新功能测试通过")
    else:
        print("\n💥 字段备注更新功能测试失败")
        sys.exit(1)