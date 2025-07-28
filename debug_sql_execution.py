#!/usr/bin/env python3
"""
调试SQL执行问题
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def debug_sql_execution():
    """调试SQL执行问题"""
    try:
        print("🔍 开始调试SQL执行...")
        
        # 1. 检查配置
        from chatbi.config import config
        print(f"✅ 配置加载成功")
        print(f"数据库类型: {config.database.type}")
        print(f"数据库连接字符串: {config.database.connection_string}")
        
        # 2. 检查数据库连接器
        from chatbi.database import get_database_connector
        connector = get_database_connector()
        print(f"✅ 数据库连接器创建: {type(connector).__name__}")
        
        # 3. 测试连接
        print("\n🔌 测试数据库连接...")
        is_connected = connector.connect()
        print(f"连接结果: {'✅ 成功' if is_connected else '❌ 失败'}")
        print(f"连接状态: {connector.is_connected}")
        
        if not is_connected:
            print("❌ 数据库连接失败，无法继续测试")
            return False
        
        # 4. 测试简单查询
        print("\n📋 测试简单查询...")
        try:
            # 尝试获取表列表
            tables = connector.get_tables()
            print(f"数据库表数量: {len(tables) if tables else 0}")
            if tables:
                print(f"表列表: {tables[:5]}{'...' if len(tables) > 5 else ''}")
            
            # 测试一个简单的SQL查询
            if tables:
                first_table = tables[0]
                test_sql = f"SELECT * FROM {first_table} LIMIT 1"
                print(f"\n🧪 测试SQL: {test_sql}")
                
                result = connector.execute_query(test_sql)
                print(f"查询结果: {result}")
                
                if result.get("success"):
                    print("✅ 直接SQL查询成功")
                else:
                    print(f"❌ 直接SQL查询失败: {result.get('error')}")
            
        except Exception as e:
            print(f"❌ 数据库查询测试失败: {e}")
        
        # 5. 测试SQL执行器
        print("\n⚙️ 测试SQL执行器...")
        from chatbi.database import get_sql_executor
        
        sql_executor = get_sql_executor()
        print(f"✅ SQL执行器创建成功")
        
        # 检查SQL执行器的连接器
        print(f"SQL执行器连接器类型: {type(sql_executor.connector).__name__}")
        print(f"SQL执行器连接状态: {sql_executor.connector.is_connected}")
        
        if tables:
            first_table = tables[0]
            test_sql = f"SELECT COUNT(*) as count FROM {first_table}"
            print(f"\n🧪 使用SQL执行器测试: {test_sql}")
            
            result = sql_executor.execute(test_sql)
            print(f"执行结果成功: {result.success}")
            print(f"执行结果数据: {result.data}")
            print(f"执行结果错误: {result.error}")
            
            if result.success:
                print("✅ SQL执行器测试成功")
            else:
                print(f"❌ SQL执行器测试失败: {result.error}")
        
        # 6. 测试主控制器
        print("\n🎯 测试主控制器查询...")
        from chatbi.orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        print(f"✅ 主控制器创建成功")
        
        # 测试一个简单的查询
        if tables:
            test_question = f"显示{tables[0]}表的记录数"
            print(f"\n💬 测试问题: {test_question}")
            
            result = orchestrator.query(test_question, auto_visualize=False, analysis_level="basic")
            print(f"查询成功: {result.success}")
            print(f"生成的SQL: {result.sql_query}")
            print(f"数据行数: {len(result.data) if result.data else 0}")
            print(f"错误信息: {result.error}")
            
            if result.success:
                print("✅ 完整查询流程测试成功")
            else:
                print(f"❌ 完整查询流程测试失败: {result.error}")
        
        print("\n✅ SQL执行调试完成")
        return True
        
    except Exception as e:
        print(f"❌ 调试过程失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    debug_sql_execution() 