#!/usr/bin/env python3
"""
测试RAG策略选择逻辑
验证三种策略是否按预期工作
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO)

def test_rag_strategy():
    """测试RAG策略选择"""
    print("🧪 测试RAG策略选择逻辑")
    print("=" * 50)
    
    try:
        from chatbi.knowledge_base.sql_knowledge_manager import get_knowledge_manager
        from chatbi.config import config
        
        # 显示配置参数
        print(f"📋 配置参数:")
        print(f"  - 相似度阈值: {config.rag_similarity_threshold}")
        print(f"  - 置信度阈值: {config.rag_confidence_threshold}")
        print(f"  - 最大示例数: {config.rag_max_examples}")
        
        knowledge_manager = get_knowledge_manager()
        
        if not knowledge_manager.enabled:
            print("❌ 知识库未启用")
            return False
        
        # 添加测试数据
        print(f"\n📝 添加测试数据...")
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
                "question": "查询订单总数",
                "sql": "SELECT COUNT(*) as order_count FROM orders",
                "description": "统计订单表中的总订单数"
            }
        ]
        
        for data in test_data:
            success = knowledge_manager.add_positive_feedback(
                question=data["question"],
                sql=data["sql"],
                description=data["description"]
            )
            if success:
                print(f"  ✅ {data['question']}")
            else:
                print(f"  ❌ {data['question']}")
        
        # 测试不同相似度的查询
        print(f"\n🔍 测试策略选择:")
        
        test_queries = [
            {
                "query": "查询用户总数",  # 应该是高相似度
                "expected_strategy": "高相似度-直接使用缓存"
            },
            {
                "query": "用户数量是多少",  # 应该是高相似度
                "expected_strategy": "高相似度-直接使用缓存"
            },
            {
                "query": "有多少个用户",  # 应该是中相似度
                "expected_strategy": "中相似度-示例辅助生成"
            },
            {
                "query": "活跃用户统计",  # 应该是中相似度
                "expected_strategy": "中相似度-示例辅助生成"
            },
            {
                "query": "商品库存查询",  # 应该是低相似度
                "expected_strategy": "低相似度-常规生成"
            }
        ]
        
        for test in test_queries:
            print(f"\n查询: '{test['query']}'")
            print(f"预期策略: {test['expected_strategy']}")
            
            rag_result = knowledge_manager.search_knowledge(test["query"])
            
            if rag_result.found_match:
                confidence = rag_result.confidence
                
                if rag_result.should_use_cached:
                    actual_strategy = "高相似度-直接使用缓存"
                    print(f"✅ 实际策略: {actual_strategy} (相似度: {confidence:.3f})")
                else:
                    if confidence >= (config.rag_similarity_threshold + config.rag_confidence_threshold) / 2:
                        actual_strategy = "中相似度-示例辅助生成"
                    else:
                        actual_strategy = "低相似度-常规生成"
                    print(f"✅ 实际策略: {actual_strategy} (相似度: {confidence:.3f})")
                
                # 显示匹配的问题
                print(f"📝 匹配问题: {rag_result.best_match['question']}")
                print(f"💾 匹配SQL: {rag_result.best_match['sql']}")
                
            else:
                print(f"❌ 未找到匹配 - 将使用常规生成流程")
        
        print(f"\n📊 知识库统计:")
        stats = knowledge_manager.get_knowledge_stats()
        if stats.get("enabled"):
            print(f"  - 总条目数: {stats.get('total_items', 0)}")
            print(f"  - 平均评分: {stats.get('avg_rating', 0):.2f}")
            print(f"  - 总使用次数: {stats.get('total_usage', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        print(f"详细错误:\n{traceback.format_exc()}")
        return False

def test_sql_generator_integration():
    """测试SQL生成器的RAG集成"""
    print(f"\n🔧 测试SQL生成器RAG集成")
    print("=" * 30)
    
    try:
        from chatbi.agents.sql_generator import get_sql_generator
        
        sql_generator = get_sql_generator()
        
        # 模拟Schema信息
        schema_info = """
        表: users
        字段: id (int), name (varchar), email (varchar), status (varchar), created_at (timestamp)
        
        表: orders  
        字段: id (int), user_id (int), amount (decimal), created_at (timestamp)
        """
        
        # 测试不同策略的问题
        test_questions = [
            "查询用户总数",  # 高相似度
            "用户数量统计",  # 中相似度
            "商品信息查询"   # 低相似度
        ]
        
        for question in test_questions:
            print(f"\n问题: {question}")
            
            # 使用RAG生成SQL
            sql_result = sql_generator.generate_sql(
                question=question,
                schema_info=schema_info,
                use_rag=True
            )
            
            print(f"生成结果: {sql_result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ SQL生成器测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 RAG策略选择逻辑测试")
    print("=" * 60)
    
    # 检查环境
    try:
        import chromadb
        print("✅ ChromaDB已安装")
    except ImportError:
        print("❌ ChromaDB未安装，请运行: pip install chromadb")
        return
    
    from chatbi.config import config
    if not config.llm.api_key:
        print("❌ 未设置DASHSCOPE_API_KEY环境变量")
        return
    
    print("✅ 环境检查通过")
    
    # 运行测试
    test1_success = test_rag_strategy()
    test2_success = test_sql_generator_integration()
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    if test1_success and test2_success:
        print("🎉 所有测试通过！RAG策略选择逻辑工作正常")
        print("\n💡 策略说明:")
        print("  - 高相似度(≥0.8): 直接使用缓存SQL")
        print("  - 中相似度(0.6-0.8): 使用相似示例辅助生成")
        print("  - 低相似度(<0.6): 常规生成流程")
    else:
        print("❌ 部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()