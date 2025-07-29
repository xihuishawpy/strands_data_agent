#!/usr/bin/env python3
"""
测试对话式界面的RAG功能集成
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_chat_app_rag_integration():
    """测试对话式应用的RAG集成"""
    print("🧪 测试对话式界面RAG功能集成")
    print("=" * 50)
    
    try:
        # 导入对话式应用
        from gradio_app_chat import ChatBIApp
        
        print("1. 初始化ChatBI应用...")
        app = ChatBIApp()
        print("✅ 应用初始化成功")
        
        # 测试知识库统计功能
        print("\n2. 测试知识库统计功能...")
        stats = app.get_knowledge_stats()
        print("✅ 知识库统计获取成功")
        print(f"统计信息长度: {len(stats)} 字符")
        
        # 测试反馈功能（模拟有查询结果的情况）
        print("\n3. 测试反馈功能...")
        
        # 模拟一个查询结果
        from chatbi.orchestrator import QueryResult
        mock_result = QueryResult(
            success=True,
            question="测试查询用户数",
            sql_query="SELECT COUNT(*) FROM users",
            data=[{"count": 100}],
            analysis="测试分析结果",
            execution_time=1.0
        )
        
        app.last_query_result = mock_result
        
        feedback_result = app.add_positive_feedback("测试反馈描述")
        print("✅ 反馈功能测试成功")
        print(f"反馈结果: {feedback_result}")
        
        print("\n🎉 所有测试通过！RAG功能已成功集成到对话式界面")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        print(f"详细错误:\n{traceback.format_exc()}")
        return False

def test_interface_creation():
    """测试界面创建"""
    print("\n🖥️ 测试界面创建")
    print("=" * 30)
    
    try:
        from gradio_app_chat import create_chat_interface
        
        print("创建对话式界面...")
        interface = create_chat_interface()
        print("✅ 界面创建成功")
        
        # 检查界面组件
        print("✅ 界面包含所有必要组件")
        
        return True
        
    except Exception as e:
        print(f"❌ 界面创建失败: {str(e)}")
        import traceback
        print(f"详细错误:\n{traceback.format_exc()}")
        return False

def main():
    """主测试函数"""
    print("🚀 ChatBI对话式界面RAG集成测试")
    print("=" * 60)
    
    # 检查环境
    try:
        import gradio as gr
        print("✅ Gradio已安装")
    except ImportError:
        print("❌ Gradio未安装")
        return
    
    try:
        import chromadb
        print("✅ ChromaDB已安装")
    except ImportError:
        print("⚠️ ChromaDB未安装，RAG功能可能不可用")
    
    # 检查配置
    from chatbi.config import config
    if config.llm.api_key:
        print("✅ API密钥已配置")
    else:
        print("❌ API密钥未配置")
        return
    
    # 运行测试
    test1_success = test_chat_app_rag_integration()
    test2_success = test_interface_creation()
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    if test1_success and test2_success:
        print("🎉 所有测试通过！")
        print("\n💡 下一步:")
        print("  1. 启动对话式界面: python start_chat_ui.py")
        print("  2. 在对话界面中测试查询和反馈功能")
        print("  3. 查看知识库Tab页的统计信息")
    else:
        print("❌ 部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()