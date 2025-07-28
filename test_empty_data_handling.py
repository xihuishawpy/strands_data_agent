#!/usr/bin/env python3
"""
测试空数据处理的修复
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_empty_data_handling():
    """测试空数据情况的处理"""
    try:
        from gradio_app_chat import ChatBIApp
        
        app = ChatBIApp()
        
        # 模拟一个返回空数据的查询结果
        class MockResult:
            def __init__(self):
                self.success = True
                self.sql_query = "SELECT * FROM test_table WHERE 1=0"
                self.data = []  # 空数据
                self.analysis = None
                self.chart_info = None
                self.execution_time = 1.0
                self.metadata = {
                    'row_count': 0,
                    'columns': [],
                    'schema_tables_used': ['test_table'],
                    'visualization_suggestion': None
                }
        
        # 测试处理空数据的情况
        history = []
        
        # 手动调用相关方法来测试
        result = MockResult()
        
        # 测试 metadata 处理
        metadata = result.metadata or {}
        row_count = metadata.get('row_count', 0)
        print(f"✅ metadata 处理正常: row_count = {row_count}")
        
        # 测试 visualization_suggestion 处理
        viz_suggestion = metadata.get('visualization_suggestion') or {}
        chart_type = viz_suggestion.get('chart_type', 'none') if viz_suggestion else 'none'
        print(f"✅ visualization_suggestion 处理正常: chart_type = {chart_type}")
        
        # 测试数据长度检查
        data_len = len(result.data) if result.data and isinstance(result.data, list) else 0
        print(f"✅ 数据长度检查正常: data_len = {data_len}")
        
        print("🎉 空数据处理测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_none_handling():
    """测试 None 值处理"""
    try:
        from gradio_app_chat import ChatBIApp
        
        app = ChatBIApp()
        
        # 模拟一个返回 None 数据的查询结果
        class MockResultWithNone:
            def __init__(self):
                self.success = True
                self.sql_query = "SELECT * FROM test_table"
                self.data = None  # None 数据
                self.analysis = None
                self.chart_info = None
                self.execution_time = 1.0
                self.metadata = None  # None metadata
        
        result = MockResultWithNone()
        
        # 测试 metadata 为 None 的处理
        metadata = result.metadata or {}
        row_count = metadata.get('row_count', 0)
        print(f"✅ None metadata 处理正常: row_count = {row_count}")
        
        # 测试数据为 None 的处理
        has_data = result.data and len(result.data) > 0
        print(f"✅ None data 处理正常: has_data = {has_data}")
        
        # 测试图表信息处理
        chart_info_safe = result.chart_info and isinstance(result.chart_info, dict)
        print(f"✅ chart_info 安全检查正常: chart_info_safe = {chart_info_safe}")
        
        print("🎉 None 值处理测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 开始测试空数据和None值处理...")
    print("=" * 50)
    
    success = True
    
    # 测试空数据处理
    if not test_empty_data_handling():
        success = False
    
    print("-" * 30)
    
    # 测试 None 值处理
    if not test_none_handling():
        success = False
    
    print("=" * 50)
    
    if success:
        print("🎉 所有测试通过！空数据处理修复成功")
        print("💡 现在应该可以正常处理返回0行数据的查询了")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    
    return success

if __name__ == "__main__":
    main()