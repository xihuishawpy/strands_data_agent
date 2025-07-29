#!/usr/bin/env python3
"""
SQL知识库功能演示脚本
展示完整的RAG工作流程
"""

import os
import sys
import time
import logging
from typing import List, Dict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbi.orchestrator import get_orchestrator
from chatbi.knowledge_base.sql_knowledge_manager import get_knowledge_manager

# 配置日志
logging.basicConfig(level=logging.WARNING)  # 减少日志输出
logger = logging.getLogger(__name__)

class SQLKnowledgeBaseDemo:
    """SQL知识库演示类"""
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self.knowledge_manager = get_knowledge_manager()
        
    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "=" * 60)
        print(f"🎯 {title}")
        print("=" * 60)
    
    def print_step(self, step: str, description: str):
        """打印步骤"""
        print(f"\n📋 {step}: {description}")
        print("-" * 40)
    
    def demo_initial_setup(self):
        """演示初始设置"""
        self.print_header("第一阶段：初始化知识库")
        
        # 检查知识库状态
        stats = self.knowledge_manager.get_knowledge_stats()
        print(f"知识库状态: {'启用' if stats.get('enabled') else '禁用'}")
        print(f"当前条目数: {stats.get('total_items', 0)}")
        
        # 添加一些初始的高质量SQL示例
        self.print_step("步骤1", "添加初始SQL知识")
        
        initial_knowledge = [
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
                "question": "按月统计订单数量",
                "sql": "SELECT DATE_TRUNC('month', created_at) as month, COUNT(*) as order_count FROM orders GROUP BY month ORDER BY month",
                "description": "按月份分组统计订单数量趋势"
            },
            {
                "question": "查询最近7天销售额",
                "sql": "SELECT SUM(amount) as total_sales FROM orders WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'",
                "description": "计算最近7天的总销售额"
            },
            {
                "question": "查询高价值客户",
                "sql": "SELECT user_id, SUM(amount) as total_spent FROM orders GROUP BY user_id HAVING SUM(amount) > 10000 ORDER BY total_spent DESC",
                "description": "查找消费总额超过10000的高价值客户"
            }
        ]
        
        for i, knowledge in enumerate(initial_knowledge, 1):
            success = self.knowledge_manager.add_positive_feedback(
                question=knowledge["question"],
                sql=knowledge["sql"],
                description=knowledge["description"]
            )
            status = "✅" if success else "❌"
            print(f"  {i}. {status} {knowledge['question']}")
        
        # 显示更新后的统计
        updated_stats = self.knowledge_manager.get_knowledge_stats()
        print(f"\n📊 知识库更新后统计:")
        print(f"  - 总条目数: {updated_stats.get('total_items', 0)}")
        print(f"  - 平均评分: {updated_stats.get('avg_rating', 0):.2f}")
    
    def demo_rag_search(self):
        """演示RAG搜索功能"""
        self.print_header("第二阶段：RAG智能检索演示")
        
        test_queries = [
            {
                "query": "用户总数是多少",
                "expected": "应该匹配'查询用户总数'，相似度很高"
            },
            {
                "query": "有多少个活跃用户",
                "expected": "应该匹配'统计活跃用户数量'，相似度较高"
            },
            {
                "query": "每月的订单统计情况",
                "expected": "应该匹配'按月统计订单数量'，相似度中等"
            },
            {
                "query": "最近一周的销售情况",
                "expected": "应该匹配'查询最近7天销售额'，相似度较高"
            },
            {
                "query": "哪些是VIP客户",
                "expected": "应该匹配'查询高价值客户'，相似度中等"
            },
            {
                "query": "商品库存查询",
                "expected": "应该找不到匹配，需要常规生成"
            }
        ]
        
        for i, test in enumerate(test_queries, 1):
            self.print_step(f"测试{i}", f"查询: '{test['query']}'")
            print(f"预期: {test['expected']}")
            
            # 执行RAG搜索
            rag_result = self.knowledge_manager.search_knowledge(test["query"])
            
            if rag_result.found_match:
                best_match = rag_result.best_match
                print(f"✅ 找到匹配 (相似度: {rag_result.confidence:.3f})")
                print(f"📝 匹配问题: {best_match['question']}")
                print(f"💾 匹配SQL: {best_match['sql'][:60]}...")
                print(f"🎯 使用策略: {'直接使用缓存' if rag_result.should_use_cached else '示例辅助生成'}")
                
                if rag_result.similar_examples:
                    print(f"📚 相似示例数: {len(rag_result.similar_examples)}")
            else:
                print("❌ 未找到匹配，将使用常规生成流程")
            
            time.sleep(0.5)  # 避免API调用过快
    
    def demo_integrated_workflow(self):
        """演示集成工作流程"""
        self.print_header("第三阶段：完整工作流程演示")
        
        # 模拟用户查询场景
        user_scenarios = [
            {
                "question": "用户数量统计",
                "description": "用户想了解系统中的用户总数"
            },
            {
                "question": "活跃用户分析", 
                "description": "用户想分析活跃用户情况"
            },
            {
                "question": "销售数据查询",
                "description": "用户想查看最近的销售数据"
            }
        ]
        
        for i, scenario in enumerate(user_scenarios, 1):
            self.print_step(f"场景{i}", scenario["description"])
            print(f"用户问题: '{scenario['question']}'")
            
            # 这里我们只演示RAG部分，不实际执行SQL（因为可能没有真实数据库）
            rag_result = self.knowledge_manager.search_knowledge(scenario["question"])
            
            if rag_result.found_match and rag_result.should_use_cached:
                print("🎯 RAG策略: 直接使用缓存SQL")
                print(f"📋 缓存SQL: {rag_result.best_match['sql']}")
                print("⚡ 优势: 响应速度快，结果一致性高")
                
                # 模拟用户满意并点赞
                print("👍 用户满意，系统自动更新使用统计")
                self.knowledge_manager.update_usage_feedback(
                    scenario["question"], 
                    rag_result.best_match['sql'], 
                    0.1
                )
                
            elif rag_result.found_match:
                print("🔍 RAG策略: 使用相似示例辅助生成")
                print(f"📚 参考示例数: {len(rag_result.similar_examples or [])}")
                print("⚡ 优势: 生成质量高，符合历史模式")
                
            else:
                print("🆕 RAG策略: 常规生成流程")
                print("⚡ 说明: 这是新类型查询，将创建新的知识")
            
            print()
    
    def demo_feedback_loop(self):
        """演示反馈循环"""
        self.print_header("第四阶段：用户反馈循环演示")
        
        self.print_step("反馈场景", "用户对查询结果进行反馈")
        
        # 模拟用户满意的查询
        positive_feedback = {
            "question": "查询今日新增用户数",
            "sql": "SELECT COUNT(*) as new_users FROM users WHERE DATE(created_at) = CURRENT_DATE",
            "description": "统计今天新注册的用户数量"
        }
        
        print(f"用户问题: {positive_feedback['question']}")
        print(f"生成SQL: {positive_feedback['sql']}")
        print("用户反馈: 👍 满意")
        
        # 添加正面反馈
        success = self.knowledge_manager.add_positive_feedback(**positive_feedback)
        print(f"反馈处理: {'✅ 成功添加到知识库' if success else '❌ 添加失败'}")
        
        if success:
            print("📈 系统改进:")
            print("  - 知识库条目数 +1")
            print("  - 该类型查询准确性提升")
            print("  - 未来相似查询可直接使用缓存")
        
        # 显示最终统计
        final_stats = self.knowledge_manager.get_knowledge_stats()
        print(f"\n📊 最终知识库统计:")
        print(f"  - 总条目数: {final_stats.get('total_items', 0)}")
        print(f"  - 平均评分: {final_stats.get('avg_rating', 0):.2f}")
        print(f"  - 总使用次数: {final_stats.get('total_usage', 0)}")
    
    def demo_performance_benefits(self):
        """演示性能优势"""
        self.print_header("第五阶段：性能优势展示")
        
        print("🚀 RAG系统的核心优势:")
        print()
        print("1. 📈 准确性提升")
        print("   - 基于历史成功案例")
        print("   - 减少SQL语法错误")
        print("   - 符合业务逻辑模式")
        print()
        print("2. ⚡ 响应速度")
        print("   - 高相似度查询直接返回缓存")
        print("   - 避免重复的LLM调用")
        print("   - 降低API使用成本")
        print()
        print("3. 🎯 一致性保证")
        print("   - 相同问题返回相同SQL")
        print("   - 避免随机性差异")
        print("   - 提升用户体验")
        print()
        print("4. 📚 持续学习")
        print("   - 用户反馈驱动改进")
        print("   - 知识库自动扩展")
        print("   - 适应业务变化")
    
    def run_complete_demo(self):
        """运行完整演示"""
        print("🎬 SQL知识库功能完整演示")
        print("本演示将展示RAG技术如何提升SQL生成的准确性和效率")
        
        try:
            # 检查系统状态
            if not self.knowledge_manager.enabled:
                print("❌ 知识库功能未启用，请检查ChromaDB安装和配置")
                return
            
            # 运行各个演示阶段
            self.demo_initial_setup()
            self.demo_rag_search()
            self.demo_integrated_workflow()
            self.demo_feedback_loop()
            self.demo_performance_benefits()
            
            print("\n🎉 演示完成！")
            print("\n💡 下一步:")
            print("1. 启动Web界面: python gradio_app_with_feedback.py")
            print("2. 体验完整功能: 查询 → 反馈 → 改进")
            print("3. 查看详细文档: SQL_KNOWLEDGE_BASE_GUIDE.md")
            
        except Exception as e:
            print(f"❌ 演示过程中出现错误: {str(e)}")
            import traceback
            print(f"详细错误:\n{traceback.format_exc()}")

def main():
    """主函数"""
    print("🚀 启动SQL知识库功能演示")
    
    # 检查环境
    try:
        import chromadb
        print("✅ ChromaDB已安装")
    except ImportError:
        print("❌ ChromaDB未安装，请运行: pip install chromadb sentence-transformers")
        return
    
    # 检查API密钥
    from chatbi.config import config
    if not config.llm.api_key:
        print("❌ 未设置DASHSCOPE_API_KEY环境变量")
        return
    
    print(f"✅ API配置正常")
    
    # 运行演示
    demo = SQLKnowledgeBaseDemo()
    demo.run_complete_demo()

if __name__ == "__main__":
    main()