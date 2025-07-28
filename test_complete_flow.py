#!/usr/bin/env python3
"""
测试完整的智能查询流程
测试: Schema获取 -> SQL生成 -> SQL执行 -> 数据分析 -> 可视化建议 -> 图表创建
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_complete_flow():
    """测试完整的查询流程"""
    try:
        print("🚀 开始测试完整的智能查询流程...")
        
        # 初始化主控制器
        from chatbi.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        print("✅ 主控制器初始化成功")
        
        # 测试用例
        test_cases = [
            {
                "question": "显示所有表的记录数",
                "description": "基础查询测试"
            },
            {
                "question": "统计每个表的数据量并按数量排序",
                "description": "聚合查询测试"
            },
            {
                "question": "查询前5条记录",
                "description": "限制结果数量测试"
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n{'='*60}")
            print(f"🧪 测试用例 {i}: {case['description']}")
            print(f"问题: {case['question']}")
            print('='*60)
            
            # 执行完整流程
            result = orchestrator.query(
                question=case['question'],
                auto_visualize=True,
                analysis_level="standard"
            )
            
            # 输出结果
            print(f"\n📊 查询结果:")
            print(f"  ✅ 成功: {result.success}")
            print(f"  ⏱️ 执行时间: {result.execution_time:.2f}秒")
            
            if result.success:
                print(f"\n🔧 SQL查询:")
                print(f"  {result.sql_query}")
                
                print(f"\n📈 数据结果:")
                print(f"  行数: {len(result.data) if result.data else 0}")
                if result.data and len(result.data) > 0:
                    print(f"  列数: {len(result.data[0]) if result.data[0] else 0}")
                    print(f"  字段: {list(result.data[0].keys()) if result.data[0] else []}")
                
                print(f"\n🔍 数据分析:")
                if result.analysis:
                    print(f"  分析长度: {len(result.analysis)} 字符")
                    print(f"  分析预览: {result.analysis[:200]}...")
                else:
                    print("  无分析结果")
                
                print(f"\n🎨 可视化:")
                if result.chart_info:
                    print(f"  图表创建: {'✅ 成功' if result.chart_info.get('success') else '❌ 失败'}")
                    if result.chart_info.get('success'):
                        print(f"  图表类型: {result.chart_info.get('chart_type', 'unknown')}")
                        print(f"  文件路径: {result.chart_info.get('file_path', 'N/A')}")
                    else:
                        print(f"  错误信息: {result.chart_info.get('error', 'unknown')}")
                else:
                    print("  无可视化结果")
                
                print(f"\n📋 元数据:")
                metadata = result.metadata or {}
                print(f"  涉及的表: {metadata.get('schema_tables_used', [])}")
                if metadata.get('visualization_suggestion'):
                    viz_suggestion = metadata['visualization_suggestion']
                    print(f"  可视化建议: {viz_suggestion.get('chart_type', 'none')}")
                    if viz_suggestion.get('reason'):
                        print(f"  建议理由: {viz_suggestion.get('reason')}")
            else:
                print(f"\n❌ 查询失败:")
                print(f"  错误信息: {result.error}")
                if result.sql_query:
                    print(f"  生成的SQL: {result.sql_query}")
        
        print(f"\n🎉 完整流程测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 完整流程测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_flow_components():
    """测试流程各个组件"""
    try:
        print("\n🔧 测试流程组件...")
        
        # 测试Schema管理器
        from chatbi.database import get_schema_manager
        schema_manager = get_schema_manager()
        print("✅ Schema管理器初始化成功")
        
        # 测试SQL生成器
        from chatbi.agents import get_sql_generator
        sql_generator = get_sql_generator()
        print("✅ SQL生成器初始化成功")
        
        # 测试SQL执行器
        from chatbi.database import get_sql_executor
        sql_executor = get_sql_executor()
        print("✅ SQL执行器初始化成功")
        
        # 测试数据分析师
        from chatbi.agents import get_data_analyst
        data_analyst = get_data_analyst()
        print("✅ 数据分析师初始化成功")
        
        # 测试SQL修复器
        from chatbi.agents import get_sql_fixer
        sql_fixer = get_sql_fixer()
        print("✅ SQL修复器初始化成功")
        
        # 测试可视化工具
        from chatbi.tools import get_visualizer
        visualizer = get_visualizer()
        print("✅ 可视化工具初始化成功")
        
        print("✅ 所有组件初始化成功")
        return True
        
    except Exception as e:
        print(f"❌ 组件测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 ChatBI 完整流程测试")
    print("="*60)
    
    # 测试组件
    components_ok = test_flow_components()
    
    if components_ok:
        # 测试完整流程
        flow_ok = test_complete_flow()
        
        if flow_ok:
            print("\n🎊 所有测试通过！ChatBI系统运行正常")
        else:
            print("\n❌ 流程测试失败")
            sys.exit(1)
    else:
        print("\n❌ 组件测试失败")
        sys.exit(1) 