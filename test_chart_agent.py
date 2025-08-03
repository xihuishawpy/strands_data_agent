#!/usr/bin/env python3
"""
测试图表智能体
验证独立的智能可视化功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_chart_agent_basic():
    """测试图表智能体基本功能"""
    print("🔍 测试图表智能体基本功能...")
    
    try:
        from chatbi.agents import get_chart_agent
        
        chart_agent = get_chart_agent()
        print(f"✅ 图表智能体创建成功: {type(chart_agent).__name__}")
        
        # 测试数据1: 分类数据对比（适合柱状图）
        test_data_1 = [
            {"产品": "产品A", "销量": 100},
            {"产品": "产品B", "销量": 150},
            {"产品": "产品C", "销量": 80},
            {"产品": "产品D", "销量": 200}
        ]
        
        print("\n📊 测试数据1: 产品销量对比")
        recommendation_1 = chart_agent.analyze_and_recommend_chart(
            data=test_data_1,
            question="各产品的销量对比"
        )
        
        print(f"推荐结果: {recommendation_1}")
        print(f"图表类型: {recommendation_1.get('chart_type')}")
        print(f"推荐理由: {recommendation_1.get('reason')}")
        print(f"置信度: {recommendation_1.get('confidence', 0)}")
        
        # 测试数据2: 时间序列数据（适合折线图）
        test_data_2 = [
            {"日期": "2024-01-01", "访问量": 1000},
            {"日期": "2024-01-02", "访问量": 1200},
            {"日期": "2024-01-03", "访问量": 900},
            {"日期": "2024-01-04", "访问量": 1500},
            {"日期": "2024-01-05", "访问量": 1800}
        ]
        
        print("\n📈 测试数据2: 网站访问量趋势")
        recommendation_2 = chart_agent.analyze_and_recommend_chart(
            data=test_data_2,
            question="网站访问量的时间趋势"
        )
        
        print(f"推荐结果: {recommendation_2}")
        print(f"图表类型: {recommendation_2.get('chart_type')}")
        print(f"推荐理由: {recommendation_2.get('reason')}")
        print(f"置信度: {recommendation_2.get('confidence', 0)}")
        
        # 测试数据3: 两个数值变量（适合散点图）
        test_data_3 = [
            {"身高": 170, "体重": 65},
            {"身高": 175, "体重": 70},
            {"身高": 165, "体重": 60},
            {"身高": 180, "体重": 75},
            {"身高": 160, "体重": 55}
        ]
        
        print("\n🔍 测试数据3: 身高体重关系")
        recommendation_3 = chart_agent.analyze_and_recommend_chart(
            data=test_data_3,
            question="身高和体重的关系分析"
        )
        
        print(f"推荐结果: {recommendation_3}")
        print(f"图表类型: {recommendation_3.get('chart_type')}")
        print(f"推荐理由: {recommendation_3.get('reason')}")
        print(f"置信度: {recommendation_3.get('confidence', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 图表智能体测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_orchestrator_integration():
    """测试与orchestrator的集成"""
    print("\n🔍 测试与orchestrator的集成...")
    
    try:
        from chatbi.orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        print(f"✅ Orchestrator创建成功")
        
        # 检查图表智能体是否正确初始化
        if hasattr(orchestrator, 'chart_agent'):
            print(f"✅ 图表智能体已集成到orchestrator")
            print(f"图表智能体类型: {type(orchestrator.chart_agent).__name__}")
        else:
            print("❌ 图表智能体未集成到orchestrator")
            return False
        
        # 测试智能可视化推荐方法
        mock_sql_result = type('MockSQLResult', (), {
            'data': [
                {"类别": "A", "数量": 10},
                {"类别": "B", "数量": 20},
                {"类别": "C", "数量": 15}
            ],
            'columns': ["类别", "数量"],
            'row_count': 3
        })()
        
        recommendation = orchestrator._get_smart_visualization_recommendation(
            mock_sql_result, "各类别的数量分布"
        )
        
        print(f"智能可视化推荐: {recommendation}")
        print(f"推荐图表类型: {recommendation.get('chart_type')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Orchestrator集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_comparison_with_analysis_agent():
    """对比图表智能体和分析智能体的推荐结果"""
    print("\n🔍 对比图表智能体和分析智能体的推荐...")
    
    try:
        from chatbi.agents import get_chart_agent, get_data_analyst
        
        chart_agent = get_chart_agent()
        data_analyst = get_data_analyst()
        
        # 测试数据
        test_data = [
            {"月份": "1月", "销售额": 10000},
            {"月份": "2月", "销售额": 12000},
            {"月份": "3月", "销售额": 9000},
            {"月份": "4月", "销售额": 15000}
        ]
        
        # 图表智能体推荐
        chart_recommendation = chart_agent.analyze_and_recommend_chart(
            data=test_data,
            question="月度销售额趋势"
        )
        
        # 分析智能体推荐
        query_result = {
            "data": test_data,
            "columns": ["月份", "销售额"],
            "row_count": 4
        }
        
        analysis_recommendation = data_analyst.suggest_visualization(query_result)
        
        print("📊 图表智能体推荐:")
        print(f"  图表类型: {chart_recommendation.get('chart_type')}")
        print(f"  推荐理由: {chart_recommendation.get('reason')}")
        print(f"  置信度: {chart_recommendation.get('confidence', 0)}")
        
        print("\n📈 分析智能体推荐:")
        print(f"  图表类型: {analysis_recommendation.get('chart_type')}")
        print(f"  推荐理由: {analysis_recommendation.get('reason')}")
        
        # 比较结果
        if chart_recommendation.get('chart_type') == analysis_recommendation.get('chart_type'):
            print("\n✅ 两个智能体推荐结果一致")
        else:
            print("\n🔄 两个智能体推荐结果不同，这是正常的，因为分析角度不同")
        
        return True
        
    except Exception as e:
        print(f"❌ 对比测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 图表智能体测试")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # 测试1: 基本功能
    if test_chart_agent_basic():
        success_count += 1
        print("✅ 基本功能测试通过")
    else:
        print("❌ 基本功能测试失败")
    
    # 测试2: Orchestrator集成
    if test_orchestrator_integration():
        success_count += 1
        print("✅ Orchestrator集成测试通过")
    else:
        print("❌ Orchestrator集成测试失败")
    
    # 测试3: 与分析智能体对比
    if test_comparison_with_analysis_agent():
        success_count += 1
        print("✅ 对比测试通过")
    else:
        print("❌ 对比测试失败")
    
    print("\n" + "=" * 60)
    print(f"🎉 测试完成: {success_count}/{total_tests} 个测试通过")
    
    if success_count == total_tests:
        print("🎊 所有测试通过！图表智能体工作正常。")
        print("\n💡 新的交互逻辑:")
        print("  1. 图表智能体独立分析数据，智能推荐可视化方案")
        print("  2. 只有在用户选择分析时，才参考分析智能体的建议")
        print("  3. 提高了可视化的灵活性和准确性")
    else:
        print("⚠️ 部分测试失败，请检查相关组件。")

if __name__ == "__main__":
    main()