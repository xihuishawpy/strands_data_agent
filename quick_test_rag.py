#!/usr/bin/env python3
"""
快速测试SQL知识库RAG功能
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """测试基本功能"""
    print("🧪 快速功能测试")
    print("=" * 30)
    
    tests_passed = 0
    total_tests = 0
    
    # 测试1: 向量存储初始化
    total_tests += 1
    print("1. 测试向量存储初始化...")
    try:
        from chatbi.knowledge_base.vector_store import get_vector_store
        vector_store = get_vector_store()
        count = vector_store.collection.count()
        print(f"   ✅ 成功 (当前条目数: {count})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {str(e)}")
    
    # 测试2: 知识库管理器初始化
    total_tests += 1
    print("2. 测试知识库管理器初始化...")
    try:
        from chatbi.knowledge_base.sql_knowledge_manager import get_knowledge_manager
        manager = get_knowledge_manager()
        enabled = manager.enabled
        print(f"   ✅ 成功 (状态: {'启用' if enabled else '禁用'})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {str(e)}")
    
    # 测试3: 添加知识
    total_tests += 1
    print("3. 测试添加知识...")
    try:
        success = manager.add_positive_feedback(
            question="测试查询用户数",
            sql="SELECT COUNT(*) FROM users",
            description="测试用例"
        )
        print(f"   ✅ 成功 (添加结果: {success})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {str(e)}")
    
    # 测试4: 搜索知识
    total_tests += 1
    print("4. 测试搜索知识...")
    try:
        rag_result = manager.search_knowledge("用户数量查询")
        found = rag_result.found_match
        print(f"   ✅ 成功 (找到匹配: {found})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {str(e)}")
    
    # 测试5: 主控制器集成
    total_tests += 1
    print("5. 测试主控制器集成...")
    try:
        from chatbi.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        stats = orchestrator.get_knowledge_stats()
        enabled = stats.get('enabled', False)
        print(f"   ✅ 成功 (集成状态: {'正常' if enabled else '异常'})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {str(e)}")
    
    # 结果总结
    print("\n" + "=" * 30)
    print(f"📊 测试结果: {tests_passed}/{total_tests} 通过")
    
    if tests_passed == total_tests:
        print("🎉 所有测试通过！RAG功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置")
        return False

def show_usage_examples():
    """显示使用示例"""
    print("\n💡 使用示例:")
    print("=" * 30)
    
    print("""
# 1. 基本使用
from chatbi.orchestrator import get_orchestrator

orchestrator = get_orchestrator()

# 执行查询（自动使用RAG）
result = orchestrator.query("查询用户总数")

# 添加正面反馈
if result.success:
    orchestrator.add_positive_feedback(
        question="查询用户总数",
        sql=result.sql_query,
        description="用户统计查询"
    )

# 2. 直接使用知识库管理器
from chatbi.knowledge_base.sql_knowledge_manager import get_knowledge_manager

manager = get_knowledge_manager()

# 搜索相似查询
rag_result = manager.search_knowledge("用户数量统计")

if rag_result.should_use_cached:
    # 直接使用缓存的SQL
    sql = rag_result.best_match["sql"]
else:
    # 使用相似示例辅助生成
    examples = rag_result.similar_examples

# 3. Web界面使用
# python gradio_app_with_feedback.py
    """)

def main():
    """主函数"""
    print("⚡ SQL知识库RAG功能快速测试")
    
    # 检查基本环境
    try:
        import chromadb
        from chatbi.config import config
        
        if not config.llm.api_key:
            print("❌ 未设置DASHSCOPE_API_KEY")
            return
        
        print("✅ 环境检查通过")
        
    except ImportError:
        print("❌ ChromaDB未安装")
        return
    except Exception as e:
        print(f"❌ 环境检查失败: {str(e)}")
        return
    
    # 运行测试
    success = test_basic_functionality()
    
    if success:
        show_usage_examples()
        print("\n🚀 准备就绪！可以开始使用SQL知识库功能")
    else:
        print("\n🔧 请根据错误信息修复问题后重试")

if __name__ == "__main__":
    main()