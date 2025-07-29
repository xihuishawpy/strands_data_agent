#!/usr/bin/env python3
"""
简化版SQL知识库RAG功能演示
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.WARNING)

def main():
    """主演示函数"""
    print("🚀 SQL知识库RAG功能演示")
    print("=" * 50)
    
    try:
        # 1. 初始化知识库管理器
        print("📚 1. 初始化知识库管理器...")
        from chatbi.knowledge_base.sql_knowledge_manager import get_knowledge_manager
        
        knowledge_manager = get_knowledge_manager()
        
        if not knowledge_manager.enabled:
            print("❌ 知识库未启用")
            return
        
        print("✅ 知识库管理器初始化成功")
        
        # 2. 添加一些测试数据
        print("\n📝 2. 添加测试SQL知识...")
        
        test_data = [
            {
                "question": "查询用户总数",
                "sql": "SELECT COUNT(*) as user_count FROM users",
                "description": "统计用户表中的总用户数量"
            },
            {
                "question": "统计活跃用户数量", 
                "sql": "SELECT COUNT(*) as active_users FROM users WHERE status = 'active'",
                "description": "统计状态为活跃的用户数量"
            },
            {
                "question": "查询最近7天销售额",
                "sql": "SELECT SUM(amount) as total_sales FROM orders WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'",
                "description": "计算最近7天的总销售额"
            }
        ]
        
        for i, data in enumerate(test_data, 1):
            success = knowledge_manager.add_positive_feedback(
                question=data["question"],
                sql=data["sql"],
                description=data["description"]
            )
            print(f"  {i}. {'✅' if success else '❌'} {data['question']}")
        
        # 3. 测试搜索功能
        print("\n🔍 3. 测试相似问题搜索...")
        
        test_queries = [
            "用户总数是多少",
            "有多少活跃用户", 
            "最近一周销售情况",
            "商品库存查询"  # 这个应该找不到匹配
        ]
        
        for query in test_queries:
            print(f"\n查询: '{query}'")
            rag_result = knowledge_manager.search_knowledge(query)
            
            if rag_result.found_match:
                best_match = rag_result.best_match
                print(f"  ✅ 找到匹配 (相似度: {rag_result.confidence:.3f})")
                print(f"  📝 匹配问题: {best_match['question']}")
                print(f"  🎯 使用策略: {'直接使用缓存' if rag_result.should_use_cached else '示例辅助生成'}")
            else:
                print("  ❌ 未找到匹配")
        
        # 4. 显示知识库统计
        print("\n📊 4. 知识库统计信息...")
        stats = knowledge_manager.get_knowledge_stats()
        
        if stats.get("enabled"):
            print(f"  总条目数: {stats.get('total_items', 0)}")
            print(f"  平均评分: {stats.get('avg_rating', 0):.2f}")
            print(f"  总使用次数: {stats.get('total_usage', 0)}")
        else:
            print(f"  ❌ 统计获取失败")
        
        # 5. 测试主控制器集成
        print("\n🎛️ 5. 测试主控制器集成...")
        from chatbi.orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        
        # 测试添加反馈
        feedback_success = orchestrator.add_positive_feedback(
            question="查询今日新增用户",
            sql="SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE",
            description="统计今天新注册的用户数量"
        )
        
        print(f"  {'✅' if feedback_success else '❌'} 主控制器反馈功能")
        
        # 获取主控制器的知识库统计
        main_stats = orchestrator.get_knowledge_stats()
        print(f"  📊 主控制器知识库状态: {'启用' if main_stats.get('enabled') else '禁用'}")
        
        print("\n🎉 演示完成！")
        print("\n💡 下一步:")
        print("  1. 启动Web界面: python gradio_app_with_feedback.py")
        print("  2. 运行完整演示: python demo_sql_knowledge_base.py")
        print("  3. 查看使用指南: SQL_KNOWLEDGE_BASE_GUIDE.md")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {str(e)}")
        import traceback
        print(f"详细错误:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()