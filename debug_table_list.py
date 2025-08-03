#!/usr/bin/env python3
"""
调试表信息获取问题
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_database_connection():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")
    
    try:
        from chatbi.database import get_database_connector
        
        connector = get_database_connector()
        print(f"✅ 数据库连接器创建成功: {type(connector).__name__}")
        
        # 检查连接状态
        if connector.is_connected:
            print("✅ 数据库已连接")
        else:
            print("❌ 数据库未连接，尝试连接...")
            if connector.connect():
                print("✅ 数据库连接成功")
            else:
                print("❌ 数据库连接失败")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_get_tables():
    """测试获取表列表"""
    print("\n🔍 测试获取表列表...")
    
    try:
        from chatbi.database import get_database_connector
        
        connector = get_database_connector()
        
        # 确保连接
        if not connector.is_connected:
            connector.connect()
        
        # 直接从连接器获取表列表
        tables = connector.get_tables()
        print(f"📋 从连接器获取到 {len(tables)} 个表:")
        for i, table in enumerate(tables[:10]):  # 只显示前10个
            print(f"  {i+1}. {table}")
        
        if len(tables) > 10:
            print(f"  ... 还有 {len(tables) - 10} 个表")
        
        return tables
        
    except Exception as e:
        print(f"❌ 获取表列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_schema_manager():
    """测试Schema管理器"""
    print("\n🔍 测试Schema管理器...")
    
    try:
        from chatbi.database import get_schema_manager
        
        schema_manager = get_schema_manager()
        print(f"✅ Schema管理器创建成功: {type(schema_manager).__name__}")
        
        # 检查Schema管理器的连接器
        print(f"🔗 Schema管理器连接器类型: {type(schema_manager.connector).__name__}")
        print(f"🔗 Schema管理器连接器状态: {schema_manager.connector.is_connected}")
        
        # 测试Schema管理器的连接器是否能获取表
        print("\n🔍 测试Schema管理器的连接器...")
        try:
            direct_tables = schema_manager.connector.get_tables()
            print(f"📋 Schema管理器连接器直接获取到 {len(direct_tables)} 个表:")
            for i, table in enumerate(direct_tables[:5]):
                print(f"  {i+1}. {table}")
        except Exception as e:
            print(f"❌ Schema管理器连接器获取表失败: {str(e)}")
        
        # 测试获取所有表（带调试）
        print("\n🔍 测试get_all_tables方法...")
        try:
            tables = schema_manager.get_all_tables(force_refresh=True)
            print(f"📋 从Schema管理器获取到 {len(tables)} 个表:")
            for i, table in enumerate(tables[:10]):
                print(f"  {i+1}. {table}")
            
            if len(tables) > 10:
                print(f"  ... 还有 {len(tables) - 10} 个表")
        except Exception as e:
            print(f"❌ get_all_tables失败: {str(e)}")
            import traceback
            traceback.print_exc()
            tables = []
        
        # 测试获取数据库Schema
        print("\n🔍 测试获取数据库Schema...")
        try:
            schema = schema_manager.get_database_schema(force_refresh=True)
            print(f"📊 Schema信息:")
            print(f"  - 数据库类型: {schema.get('database_type', '未知')}")
            print(f"  - 表数量: {len(schema.get('tables', {}))}")
            print(f"  - 关系数量: {len(schema.get('relationships', []))}")
            print(f"  - 用户ID: {schema.get('user_id', 'None')}")
            print(f"  - 权限过滤: {schema.get('permission_filtered', False)}")
            
            # 显示表名
            table_names = list(schema.get('tables', {}).keys())
            print(f"  - 表名列表: {table_names[:5]}{'...' if len(table_names) > 5 else ''}")
        except Exception as e:
            print(f"❌ get_database_schema失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return tables
        
    except Exception as e:
        print(f"❌ Schema管理器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_gradio_app():
    """测试Gradio应用的表列表获取"""
    print("\n🔍 测试Gradio应用的表列表获取...")
    
    try:
        from gradio_app_chat import ChatBIApp
        
        app = ChatBIApp()
        print("✅ ChatBI应用创建成功")
        
        # 测试获取表列表
        tables = app.get_table_list()
        print(f"📋 从Gradio应用获取到 {len(tables)} 个表:")
        for i, table in enumerate(tables[:10]):
            print(f"  {i+1}. {table}")
        
        if len(tables) > 10:
            print(f"  ... 还有 {len(tables) - 10} 个表")
        
        # 检查schema_manager是否正确初始化
        if app.schema_manager:
            print("✅ Schema管理器已初始化")
        else:
            print("❌ Schema管理器未初始化")
        
        return tables
        
    except Exception as e:
        print(f"❌ Gradio应用测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_config():
    """测试配置"""
    print("\n🔍 测试配置...")
    
    try:
        from chatbi.config import config
        
        print(f"📊 数据库配置:")
        print(f"  - 类型: {config.database.type}")
        print(f"  - 主机: {config.database.host}")
        print(f"  - 端口: {config.database.port}")
        print(f"  - 数据库: {config.database.database}")
        print(f"  - 用户: {config.database.username}")
        print(f"  - 连接字符串: {config.database.connection_string[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 开始调试表信息获取问题...")
    print("=" * 60)
    
    # 1. 测试配置
    if not test_config():
        print("\n❌ 配置测试失败，请检查环境变量配置")
        return
    
    # 2. 测试数据库连接
    if not test_database_connection():
        print("\n❌ 数据库连接失败，请检查数据库配置和连接")
        return
    
    # 3. 测试直接获取表列表
    tables_from_connector = test_get_tables()
    if not tables_from_connector:
        print("\n❌ 无法从数据库连接器获取表列表")
        return
    
    # 4. 测试Schema管理器
    tables_from_schema_manager = test_schema_manager()
    if not tables_from_schema_manager:
        print("\n❌ 无法从Schema管理器获取表列表")
        return
    
    # 5. 测试Gradio应用
    tables_from_gradio = test_gradio_app()
    if not tables_from_gradio:
        print("\n❌ 无法从Gradio应用获取表列表")
        return
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print(f"📊 结果对比:")
    print(f"  - 连接器获取: {len(tables_from_connector)} 个表")
    print(f"  - Schema管理器获取: {len(tables_from_schema_manager)} 个表")
    print(f"  - Gradio应用获取: {len(tables_from_gradio)} 个表")
    
    if len(tables_from_connector) == len(tables_from_schema_manager) == len(tables_from_gradio):
        print("✅ 所有方法获取的表数量一致")
    else:
        print("⚠️ 不同方法获取的表数量不一致，可能存在问题")

if __name__ == "__main__":
    main()