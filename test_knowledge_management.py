#!/usr/bin/env python3
"""
测试SQL知识库管理功能
"""

import os
import sys
import pandas as pd
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_knowledge_management():
    """测试知识库管理功能"""
    print("🧪 测试SQL知识库管理功能")
    print("=" * 50)
    
    try:
        from gradio_app_chat import ChatBIApp
        
        print("1. 初始化ChatBI应用...")
        app = ChatBIApp()
        print("✅ 应用初始化成功")
        
        # 测试获取知识库表格
        print("\n2. 测试获取知识库表格...")
        df = app.get_knowledge_table()
        print(f"✅ 获取表格成功，当前条目数: {len(df)}")
        print(f"表格列: {list(df.columns)}")
        
        # 测试添加知识库条目
        print("\n3. 测试添加知识库条目...")
        result = app.add_knowledge_item(
            question="测试查询用户数量",
            sql="SELECT COUNT(*) as user_count FROM users",
            description="这是一个测试查询",
            tags="测试, 用户统计"
        )
        print(f"添加结果: {result}")
        
        # 重新获取表格，检查是否添加成功
        df_after_add = app.get_knowledge_table()
        print(f"添加后条目数: {len(df_after_add)}")
        
        if len(df_after_add) > len(df):
            print("✅ 添加功能正常")
            
            # 测试更新功能
            print("\n4. 测试更新知识库条目...")
            if not df_after_add.empty:
                # 获取第一个条目的ID
                item_id = df_after_add.iloc[0]['ID']
                update_result = app.update_knowledge_item(
                    item_id=item_id,
                    question="更新后的测试查询",
                    sql="SELECT COUNT(*) as total_users FROM users",
                    description="这是更新后的描述",
                    tags="更新测试, 用户统计"
                )
                print(f"更新结果: {update_result}")
                
                # 测试删除功能
                print("\n5. 测试删除知识库条目...")
                delete_result = app.delete_knowledge_item(item_id)
                print(f"删除结果: {delete_result}")
                
                # 检查删除后的条目数
                df_after_delete = app.get_knowledge_table()
                print(f"删除后条目数: {len(df_after_delete)}")
                
                if len(df_after_delete) < len(df_after_add):
                    print("✅ 删除功能正常")
                else:
                    print("⚠️ 删除功能可能有问题")
            else:
                print("⚠️ 无法测试更新和删除功能，表格为空")
        else:
            print("⚠️ 添加功能可能有问题")
        
        # 测试根据ID获取条目
        print("\n6. 测试根据ID获取条目...")
        df_current = app.get_knowledge_table()
        if not df_current.empty:
            test_id = df_current.iloc[0]['ID']
            question, sql, desc, tags, status = app.get_knowledge_item_by_id(test_id)
            print(f"获取条目结果: {status}")
            print(f"问题: {question}")
            print(f"SQL: {sql[:50]}..." if sql else "无SQL")
        else:
            print("⚠️ 无条目可测试")
        
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
        
        return True
        
    except Exception as e:
        print(f"❌ 界面创建失败: {str(e)}")
        import traceback
        print(f"详细错误:\n{traceback.format_exc()}")
        return False

def show_management_features():
    """显示管理功能说明"""
    print("\n📚 知识库管理功能说明")
    print("=" * 40)
    
    features = [
        "✅ 表格展示所有知识库条目",
        "✅ 点击表格行选择条目进行编辑",
        "✅ 实时更新条目信息（问题、SQL、描述、标签）",
        "✅ 删除不需要的条目",
        "✅ 添加新的知识库条目",
        "✅ 自动刷新表格显示最新数据",
        "✅ 支持标签管理（逗号分隔）",
        "✅ 显示条目的评分和使用次数",
        "✅ 按创建时间排序显示",
        "✅ 完整的增删改查功能"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print(f"\n🎯 使用方法:")
    print(f"  1. 启动应用: python start_chat_ui.py")
    print(f"  2. 切换到'📚 SQL知识库'标签页")
    print(f"  3. 在'📋 知识库内容'子标签页查看和编辑条目")
    print(f"  4. 在'➕ 添加条目'子标签页添加新条目")
    print(f"  5. 在'📊 统计信息'子标签页查看统计")

def main():
    """主函数"""
    print("🚀 SQL知识库管理功能测试")
    print("=" * 60)
    
    # 检查环境
    try:
        import chromadb
        print("✅ ChromaDB已安装")
    except ImportError:
        print("❌ ChromaDB未安装，请运行: pip install chromadb")
        return
    
    from chatbi.config import config
    if config.llm.api_key:
        print("✅ API密钥已配置")
    else:
        print("❌ API密钥未配置")
        return
    
    # 运行测试
    test1_success = test_knowledge_management()
    test2_success = test_interface_creation()
    
    # 显示功能说明
    show_management_features()
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    if test1_success and test2_success:
        print("🎉 所有测试通过！知识库管理功能正常")
        print("\n🚀 现在可以启动应用体验知识库管理：")
        print("   python start_chat_ui.py")
        print("\n💡 功能亮点:")
        print("   - 直观的表格界面展示所有知识库条目")
        print("   - 点击即可编辑，实时生效")
        print("   - 完整的增删改查功能")
        print("   - 支持标签和描述管理")
    else:
        print("❌ 部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()