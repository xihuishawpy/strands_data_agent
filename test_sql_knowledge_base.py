#!/usr/bin/env python3
"""
测试SQL知识库功能
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbi.knowledge_base.sql_knowledge_manager import get_knowledge_manager
from chatbi.orchestrator import get_orchestrator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_embedding_service():
    """测试embedding服务"""
    print("🧪 测试Embedding服务")
    print("=" * 60)
    
    try:
        from chatbi.knowledge_base.embedding_service import get_embedding_service
        
        embedding_service = get_embedding_service()
        
        # 测试单个文本embedding
        test_text = "查询用户总数"
        print(f"测试文本: {test_text}")
        
        embedding = embedding_service.embed_text(test_text)
        print(f"✅ Embedding成功，维度: {len(embedding)}")
        print(f"前5个值: {embedding[:5]}")
        
        # 测试批量embedding
        test_texts = ["查询用户总数", "统计活跃用户", "按月统计订单"]
        embeddings = embedding_service.embed_texts(test_texts)
        print(f"✅ 批量Embedding成功，数量: {len(embeddings)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding测试失败: {str(e)}")
        return False

def test_knowledge_base():
    """测试SQL知识库功能"""
    print("🚀 开始测试SQL知识库功能")
    print("=" * 60)
    
    try:
        # 1. 初始化知识库管理器
        print("\n📚 1. 初始化知识库管理器")
        knowledge_manager = get_knowledge_manager()
        
        if not knowledge_manager.enabled:
            print("❌ 知识库未启用，请安装ChromaDB: pip install chromadb")
            return
        
        print("✅ 知识库管理器初始化成功")
        
        # 2. 添加一些测试数据
        print("\n📝 2. 添加测试SQL知识")
        
        test_data = [
            {
                "question": "查询用户总数",
                "sql": "SELECT COUNT(*) as user_count FROM users",
                "description": "统计用户表中的总用户数"
            },
            {
                "question": "查询活跃用户数量",
                "sql": "SELECT COUNT(*) as active_users FROM users WHERE status = 'active'",
                "description": "统计状态为活跃的用户数量"
            },
            {
                "question": "按月统计订单数量",
                "sql": "SELECT DATE_TRUNC('month', created_at) as month, COUNT(*) as order_count FROM orders GROUP BY month ORDER BY month",
                "description": "按月份分组统计订单数量"
            },
            {
                "question": "查询最近7天的销售额",
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
        
        # 3. 测试相似问题搜索
        print("\n🔍 3. 测试相似问题搜索")
        
        test_queries = [
            "用户总数是多少",
            "有多少活跃用户",
            "每月订单统计",
            "最近一周销售情况",
            "查询商品库存"  # 这个应该找不到匹配
        ]
        
        for query in test_queries:
            print(f"\n查询: {query}")
            rag_result = knowledge_manager.search_knowledge(query)
            
            if rag_result.found_match:
                best_match = rag_result.best_match
                print(f"  ✅ 找到匹配 (相似度: {rag_result.confidence:.3f})")
                print(f"  📝 匹配问题: {best_match['question']}")
                print(f"  💾 SQL: {best_match['sql']}")
                print(f"  🎯 是否使用缓存: {rag_result.should_use_cached}")
                
                # 显示所有相似项
                if rag_result.similar_examples:
                    print(f"  📚 相似示例数量: {len(rag_result.similar_examples)}")
                    for i, example in enumerate(rag_result.similar_examples[:3]):
                        print(f"    {i+1}. {example['question']} (相似度: {example['similarity']:.3f})")
            else:
                print("  ❌ 未找到匹配")
                
                # 尝试直接调用向量存储进行调试
                try:
                    similar_items = knowledge_manager.vector_store.search_similar_questions(
                        question=query,
                        top_k=3,
                        similarity_threshold=0.3  # 降低阈值进行调试
                    )
                    print(f"  🔍 调试搜索结果: 找到 {len(similar_items)} 个项目")
                    for item in similar_items:
                        print(f"    - {item['question']} (相似度: {item['similarity']:.3f})")
                except Exception as e:
                    print(f"  ❌ 调试搜索失败: {str(e)}")
        
        # 4. 测试知识库统计
        print("\n📊 4. 知识库统计信息")
        stats = knowledge_manager.get_knowledge_stats()
        
        if stats.get("enabled"):
            print(f"  总条目数: {stats.get('total_items', 0)}")
            print(f"  平均评分: {stats.get('avg_rating', 0):.2f}")
            print(f"  总使用次数: {stats.get('total_usage', 0)}")
            print(f"  高评分条目: {stats.get('top_rated_count', 0)}")
        else:
            print(f"  ❌ 统计获取失败: {stats.get('error', '未知错误')}")
        
        # 5. 测试集成到主控制器
        print("\n🎛️ 5. 测试主控制器集成")
        orchestrator = get_orchestrator()
        
        # 模拟添加正面反馈
        feedback_success = orchestrator.add_positive_feedback(
            question="查询今日新增用户",
            sql="SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE",
            description="统计今天新注册的用户数量"
        )
        
        print(f"  {'✅' if feedback_success else '❌'} 添加反馈到主控制器")
        
        # 获取主控制器的知识库统计
        main_stats = orchestrator.get_knowledge_stats()
        print(f"  📊 主控制器知识库状态: {'启用' if main_stats.get('enabled') else '禁用'}")
        
        print("\n🎉 SQL知识库功能测试完成！")
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        print(f"❌ 测试失败: {str(e)}")

def test_rag_integration():
    """测试RAG集成到SQL生成流程"""
    print("\n🔧 测试RAG集成到SQL生成流程")
    print("=" * 60)
    
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
        
        # 测试问题
        test_questions = [
            "查询用户总数",  # 应该能找到缓存
            "统计活跃用户",  # 应该能找到相似示例
            "查询商品信息"   # 应该找不到匹配，正常生成
        ]
        
        for question in test_questions:
            print(f"\n问题: {question}")
            
            # 使用RAG生成SQL
            sql_result = sql_generator.generate_sql(
                question=question,
                schema_info=schema_info,
                use_rag=True
            )
            
            print(f"生成结果: {sql_result}")
            
            # 如果生成成功，模拟添加正面反馈
            if not sql_result.startswith("ERROR"):
                feedback_success = sql_generator.add_positive_feedback(
                    question=question,
                    sql=sql_result,
                    description=f"RAG测试生成的SQL: {question}"
                )
                print(f"反馈添加: {'✅' if feedback_success else '❌'}")
        
        print("\n✅ RAG集成测试完成")
        
    except Exception as e:
        logger.error(f"RAG集成测试失败: {str(e)}")
        print(f"❌ RAG集成测试失败: {str(e)}")

if __name__ == "__main__":
    print("🧪 SQL知识库功能测试")
    print("=" * 60)
    
    # 检查ChromaDB是否安装
    try:
        import chromadb
        print("✅ ChromaDB已安装")
    except ImportError:
        print("❌ ChromaDB未安装，请运行: pip install chromadb sentence-transformers")
        sys.exit(1)
    
    # 测试embedding服务
    if not test_embedding_service():
        print("❌ Embedding服务测试失败，跳过后续测试")
        sys.exit(1)
    
    # 运行测试
    test_knowledge_base()
    test_rag_integration()
    
    print("\n🏁 所有测试完成！")