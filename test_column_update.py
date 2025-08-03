#!/usr/bin/env python3
"""
测试字段备注更新功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_column_comment_update():
    """测试字段备注更新"""
    print("🔍 测试字段备注更新功能...")
    
    try:
        from chatbi.database import get_database_connector
        
        connector = get_database_connector()
        print(f"✅ 数据库连接器创建成功: {type(connector).__name__}")
        
        # 确保连接
        if not connector.is_connected:
            print("数据库未连接，尝试连接...")
            if not connector.connect():
                print("❌ 数据库连接失败")
                return False
        
        print("✅ 数据库已连接")
        
        # 获取表列表
        tables = connector.get_tables()
        if not tables:
            print("❌ 没有找到任何表")
            return False
        
        print(f"📋 找到 {len(tables)} 个表")
        
        # 选择一个测试表（使用dim_edd_budget）
        test_table = "dim_edd_budget"
        if test_table not in tables:
            test_table = tables[0]
        
        print(f"🎯 使用表 '{test_table}' 进行测试")
        
        # 获取表结构
        schema = connector.get_table_schema(test_table)
        columns = schema.get("columns", [])
        
        if not columns:
            print(f"❌ 表 {test_table} 没有字段信息")
            return False
        
        # 选择第一个字段进行测试
        test_column = columns[0]["name"]
        print(f"🎯 测试字段: {test_column}")
        
        # 显示原始备注
        original_comment = columns[0].get("comment", "")
        print(f"📝 原始备注: '{original_comment}'")
        
        # 测试更新备注
        test_comment = f"测试备注 - {test_column} 字段的业务含义"
        print(f"🔄 尝试更新备注为: '{test_comment}'")
        
        success = connector.update_column_comment(
            table_name=test_table,
            column_name=test_column,
            comment=test_comment
        )
        
        if success:
            print("✅ 字段备注更新成功")
            
            # 验证更新结果
            print("🔍 验证更新结果...")
            updated_schema = connector.get_table_schema(test_table)
            updated_columns = updated_schema.get("columns", [])
            
            for col in updated_columns:
                if col["name"] == test_column:
                    updated_comment = col.get("comment", "")
                    print(f"📝 更新后备注: '{updated_comment}'")
                    
                    if updated_comment == test_comment:
                        print("✅ 备注更新验证成功")
                        return True
                    else:
                        print("⚠️ 备注更新验证失败，内容不匹配")
                        return False
            
            print("❌ 找不到更新后的字段信息")
            return False
        else:
            print("❌ 字段备注更新失败")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_gradio_app_update():
    """测试Gradio应用的字段更新功能"""
    print("\n🔍 测试Gradio应用的字段更新功能...")
    
    try:
        from gradio_app_chat import ChatBIApp
        import pandas as pd
        
        app = ChatBIApp()
        print("✅ ChatBI应用创建成功")
        
        # 测试表
        test_table = "dim_edd_budget"
        
        # 获取字段信息
        df, status = app.get_columns_dataframe(test_table)
        print(f"📊 获取字段信息: {status}")
        
        if df.empty:
            print("❌ 没有获取到字段信息")
            return False
        
        print(f"📋 获取到 {len(df)} 个字段")
        
        # 修改第一个字段的描述
        if len(df) > 0:
            df.iloc[0, df.columns.get_loc("字段描述")] = "测试描述 - 通过Gradio应用更新"
            
            # 测试批量更新
            result = app.update_columns_from_dataframe(test_table, df)
            print(f"🔄 批量更新结果: {result}")
            
            if "成功" in result:
                print("✅ Gradio应用字段更新成功")
                return True
            else:
                print("❌ Gradio应用字段更新失败")
                return False
        else:
            print("❌ 没有字段可以测试")
            return False
        
    except Exception as e:
        print(f"❌ Gradio应用测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 开始测试字段备注更新功能...")
    print("=" * 60)
    
    # 1. 测试连接器的字段备注更新
    if test_column_comment_update():
        print("\n✅ 连接器字段备注更新测试通过")
    else:
        print("\n❌ 连接器字段备注更新测试失败")
        return
    
    # 2. 测试Gradio应用的字段更新
    if test_gradio_app_update():
        print("\n✅ Gradio应用字段更新测试通过")
    else:
        print("\n❌ Gradio应用字段更新测试失败")
        return
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！字段备注更新功能正常工作。")

if __name__ == "__main__":
    main()