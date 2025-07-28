#!/usr/bin/env python3
"""
测试SQL修复智能体功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_sql_fixer():
    """测试SQL修复功能"""
    try:
        from chatbi.agents import get_sql_fixer
        from chatbi.database import get_schema_manager
        
        print("🔧 开始测试SQL修复智能体...")
        
        # 初始化组件
        sql_fixer = get_sql_fixer()
        schema_manager = get_schema_manager()
        
        print("✅ SQL修复智能体创建成功")
        
        # 获取Schema信息
        schema_summary = schema_manager.get_schema_summary()
        print(f"📋 Schema信息长度: {len(schema_summary) if schema_summary else 0} 字符")
        
        # 测试用例
        test_cases = [
            {
                "name": "字段名错误",
                "sql": "SELECT user_id, user_name FROM users WHERE age > 18",
                "error": "Column 'user_name' doesn't exist. Did you mean 'username'?",
                "question": "查询年龄大于18的用户"
            },
            {
                "name": "表名错误", 
                "sql": "SELECT * FROM user_table WHERE id = 1",
                "error": "Table 'user_table' doesn't exist",
                "question": "查询ID为1的用户信息"
            },
            {
                "name": "语法错误",
                "sql": "SELECT * FROM users WHERE age > 18 AND",
                "error": "You have an error in your SQL syntax near 'AND'",
                "question": "查询年龄大于18的用户"
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n🧪 测试用例 {i}: {case['name']}")
            print(f"原始SQL: {case['sql']}")
            print(f"错误信息: {case['error']}")
            
            # 执行修复
            result = sql_fixer.analyze_and_fix_sql(
                original_sql=case['sql'],
                error_message=case['error'],
                schema_info=schema_summary or "暂无Schema信息",
                original_question=case['question']
            )
            
            print(f"修复结果:")
            print(f"  - 错误类型: {result.get('error_type', 'N/A')}")
            print(f"  - 置信度: {result.get('confidence', 0.0):.2f}")
            print(f"  - 修复后SQL: {result.get('fixed_sql', 'N/A')}")
            print(f"  - 错误分析: {result.get('error_analysis', 'N/A')[:100]}...")
            
            if result.get('validation_errors'):
                print(f"  - 验证错误: {result['validation_errors']}")
        
        # 测试SQL优化
        print(f"\n🚀 测试SQL优化功能...")
        
        test_sql = "SELECT * FROM users WHERE age > 18 ORDER BY created_at"
        optimization = sql_fixer.suggest_query_improvements(
            sql=test_sql,
            schema_info=schema_summary or "暂无Schema信息"
        )
        
        print(f"优化结果:")
        print(f"  - 性能评分: {optimization.get('performance_score', 0.0):.2f}")
        print(f"  - 优化建议数量: {len(optimization.get('optimizations', []))}")
        print(f"  - 优化后SQL: {optimization.get('optimized_sql', 'N/A')[:100]}...")
        
        print("\n✅ SQL修复功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ SQL修复功能测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_sql_fixer() 