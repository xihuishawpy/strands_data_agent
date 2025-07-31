"""
SQL生成器提示词构建策略的单元测试
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chatbi.agents.sql_generator import SQLGeneratorAgent


class TestSQLGeneratorPromptBuilding(unittest.TestCase):
    """SQL生成器提示词构建测试"""
    
    def setUp(self):
        """测试初始化"""
        with patch('chatbi.agents.sql_generator.get_knowledge_manager'):
            self.generator = SQLGeneratorAgent()
    
    def test_select_optimal_examples_empty_list(self):
        """测试空示例列表的处理"""
        result = self.generator._select_optimal_examples("test question", [], max_examples=3)
        self.assertEqual(result, [])
    
    def test_select_optimal_examples_basic_selection(self):
        """测试基础示例选择"""
        examples = [
            {
                'question': '查询用户信息',
                'sql': 'SELECT * FROM users',
                'similarity': 0.9,
                'rating': 1.0,
                'usage_count': 5,
                'created_at': datetime.now().isoformat()
            },
            {
                'question': '统计订单数量',
                'sql': 'SELECT COUNT(*) FROM orders',
                'similarity': 0.7,
                'rating': 0.8,
                'usage_count': 3,
                'created_at': (datetime.now() - timedelta(days=30)).isoformat()
            },
            {
                'question': '复杂查询示例',
                'sql': 'SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name',
                'similarity': 0.6,
                'rating': 1.2,
                'usage_count': 10,
                'created_at': (datetime.now() - timedelta(days=7)).isoformat()
            }
        ]
        
        result = self.generator._select_optimal_examples("查询用户", examples, max_examples=2)
        
        # 应该选择2个示例
        self.assertEqual(len(result), 2)
        
        # 每个示例都应该有selection_score
        for example in result:
            self.assertIn('selection_score', example)
            self.assertIsInstance(example['selection_score'], float)
            self.assertGreaterEqual(example['selection_score'], 0.0)
            self.assertLessEqual(example['selection_score'], 1.0)
    
    def test_calculate_example_score(self):
        """测试示例评分计算"""
        example = {
            'similarity': 0.8,
            'rating': 1.0,
            'usage_count': 5,
            'sql': 'SELECT * FROM users WHERE id = 1',
            'created_at': datetime.now().isoformat()
        }
        
        score = self.generator._calculate_example_score("查询用户信息", example)
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    def test_calculate_sql_complexity_match(self):
        """测试SQL复杂度匹配计算"""
        # 简单查询匹配
        simple_score = self.generator._calculate_sql_complexity_match(
            "查询用户信息", 
            "SELECT * FROM users"
        )
        self.assertGreater(simple_score, 0.5)
        
        # 复杂查询匹配
        complex_score = self.generator._calculate_sql_complexity_match(
            "统计每个用户的订单数量",
            "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name"
        )
        self.assertGreater(complex_score, 0.5)
        
        # 不匹配的情况
        mismatch_score = self.generator._calculate_sql_complexity_match(
            "简单查询用户",
            "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name"
        )
        self.assertLess(mismatch_score, 0.8)
    
    def test_calculate_recency_score(self):
        """测试时效性分数计算"""
        # 最近的示例
        recent_example = {
            'created_at': datetime.now().isoformat()
        }
        recent_score = self.generator._calculate_recency_score(recent_example)
        self.assertEqual(recent_score, 1.0)
        
        # 一个月前的示例
        old_example = {
            'created_at': (datetime.now() - timedelta(days=30)).isoformat()
        }
        old_score = self.generator._calculate_recency_score(old_example)
        self.assertLess(old_score, 1.0)
        self.assertGreater(old_score, 0.0)
        
        # 没有时间信息的示例
        no_time_example = {}
        no_time_score = self.generator._calculate_recency_score(no_time_example)
        self.assertEqual(no_time_score, 0.5)
    
    def test_apply_diversity_filter(self):
        """测试多样性过滤"""
        examples = [
            {
                'question': '查询用户信息',
                'sql': 'SELECT * FROM users',
                'selection_score': 0.9
            },
            {
                'question': '查询用户数据',  # 与第一个相似
                'sql': 'SELECT name FROM users',
                'selection_score': 0.8
            },
            {
                'question': '统计订单数量',  # 不同类型
                'sql': 'SELECT COUNT(*) FROM orders',
                'selection_score': 0.7
            }
        ]
        
        result = self.generator._apply_diversity_filter(examples, max_examples=2)
        
        # 应该选择多样化的示例
        self.assertEqual(len(result), 2)
        
        # 第一个和第三个应该被选中（多样性更好）
        questions = [ex['question'] for ex in result]
        self.assertIn('查询用户信息', questions)
        self.assertIn('统计订单数量', questions)
    
    def test_calculate_text_similarity(self):
        """测试文本相似度计算"""
        # 相同文本
        same_similarity = self.generator._calculate_text_similarity("hello world", "hello world")
        self.assertEqual(same_similarity, 1.0)
        
        # 完全不同的文本
        diff_similarity = self.generator._calculate_text_similarity("hello", "world")
        self.assertLess(diff_similarity, 0.5)
        
        # 部分相似的文本
        partial_similarity = self.generator._calculate_text_similarity("hello world", "hello python")
        self.assertGreater(partial_similarity, 0.0)
        self.assertLess(partial_similarity, 1.0)
        
        # 空文本处理
        empty_similarity = self.generator._calculate_text_similarity("", "hello")
        self.assertEqual(empty_similarity, 0.0)
    
    def test_build_rag_prompt_basic(self):
        """测试基础RAG提示词构建"""
        question = "查询用户信息"
        schema_info = "CREATE TABLE users (id INT, name VARCHAR(50))"
        
        prompt = self.generator.build_rag_prompt(question, schema_info)
        
        # 检查基本组件
        self.assertIn("数据库Schema信息:", prompt)
        self.assertIn(schema_info, prompt)
        self.assertIn("用户问题:", prompt)
        self.assertIn(question, prompt)
        self.assertIn("请基于以上信息生成准确的SQL查询语句", prompt)
    
    def test_build_rag_prompt_with_examples(self):
        """测试包含示例的RAG提示词构建"""
        question = "查询用户信息"
        schema_info = "CREATE TABLE users (id INT, name VARCHAR(50))"
        
        # 模拟RAG结果
        rag_result = Mock()
        rag_result.found_match = True
        rag_result.similar_examples = [
            {
                'question': '获取用户数据',
                'sql': 'SELECT * FROM users',
                'similarity': 0.8,
                'description': '查询所有用户'
            }
        ]
        rag_result.strategy = "medium_similarity_assisted"
        
        prompt = self.generator.build_rag_prompt(question, schema_info, rag_result)
        
        # 检查示例相关内容
        self.assertIn("参考相似查询示例:", prompt)
        self.assertIn("获取用户数据", prompt)
        self.assertIn("SELECT * FROM users", prompt)
        self.assertIn("相似度: 0.800", prompt)
        self.assertIn("💡 提示: 以上示例与当前问题有一定相似性", prompt)
    
    def test_build_rag_prompt_length_control(self):
        """测试提示词长度控制"""
        question = "查询用户信息"
        schema_info = "CREATE TABLE users (id INT, name VARCHAR(50))"
        
        # 创建很多示例来测试长度控制
        rag_result = Mock()
        rag_result.found_match = True
        rag_result.similar_examples = []
        
        # 添加很多长示例
        for i in range(10):
            rag_result.similar_examples.append({
                'question': f'这是一个很长的问题描述，用来测试长度控制功能，问题编号{i}' * 10,
                'sql': f'SELECT * FROM very_long_table_name_{i} WHERE very_long_column_name = "very_long_value_{i}"' * 5,
                'similarity': 0.8 - i * 0.05,
                'description': f'这是一个很长的描述信息，用来测试长度控制，描述编号{i}' * 20
            })
        
        # 设置较小的长度限制
        prompt = self.generator.build_rag_prompt(
            question, schema_info, rag_result, max_prompt_length=2000
        )
        
        # 检查长度是否被控制
        self.assertLessEqual(len(prompt), 2000)
        
        # 仍然应该包含基本信息
        self.assertIn("用户问题:", prompt)
        self.assertIn("数据库Schema信息:", prompt)
    
    def test_truncate_prompt_intelligently(self):
        """测试智能提示词截断"""
        long_prompt = """数据库Schema信息:
CREATE TABLE users (id INT, name VARCHAR(50), email VARCHAR(100));
CREATE TABLE orders (id INT, user_id INT, amount DECIMAL(10,2));

参考相似查询示例:
示例 1:
问题: 查询用户信息
SQL: SELECT * FROM users WHERE id = 1
相似度: 0.900

示例 2:
问题: 统计订单数量
SQL: SELECT COUNT(*) FROM orders
相似度: 0.800

用户问题: 查询特定用户的订单信息

请基于以上信息生成准确的SQL查询语句。
要求:
1. 只输出SQL语句，不要包含解释
2. 确保语法正确且符合安全要求
3. 优先使用提供的Schema信息
4. 可以参考相似示例的查询思路，但要根据具体问题调整"""
        
        truncated = self.generator._truncate_prompt_intelligently(long_prompt, 500)
        
        # 检查长度
        self.assertLessEqual(len(truncated), 500)
        
        # 检查重要信息是否保留
        self.assertIn("用户问题:", truncated)
        self.assertIn("数据库Schema信息:", truncated)
    
    def test_build_rag_prompt_with_table_names(self):
        """测试包含表名的提示词构建"""
        question = "查询用户订单"
        schema_info = "CREATE TABLE users (id INT, name VARCHAR(50))"
        table_names = ["users", "orders", "products"]
        
        prompt = self.generator.build_rag_prompt(
            question, schema_info, table_names=table_names
        )
        
        # 检查表名是否包含
        self.assertIn("相关表名:", prompt)
        self.assertIn("users, orders, products", prompt)
    
    def test_pre_filter_examples(self):
        """测试示例预过滤功能"""
        examples = [
            # 有效示例
            {
                'question': '查询用户信息',
                'sql': 'SELECT * FROM users WHERE id = 1',
                'similarity': 0.8
            },
            # 无效示例：缺少问题
            {
                'sql': 'SELECT * FROM users',
                'similarity': 0.7
            },
            # 无效示例：缺少SQL
            {
                'question': '查询数据',
                'similarity': 0.6
            },
            # 无效示例：SQL太短
            {
                'question': '查询',
                'sql': 'SELECT',
                'similarity': 0.5
            },
            # 无效示例：相似度太低
            {
                'question': '查询用户',
                'sql': 'SELECT * FROM users',
                'similarity': 0.2
            },
            # 无效示例：评分太低
            {
                'question': '查询订单',
                'sql': 'SELECT * FROM orders',
                'similarity': 0.7,
                'rating': -2.0
            }
        ]
        
        filtered = self.generator._pre_filter_examples(examples)
        
        # 应该只保留第一个有效示例
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['question'], '查询用户信息')
    
    def test_finalize_example_selection(self):
        """测试最终示例选择优化"""
        examples = [
            {
                'question': '查询用户信息',
                'sql': 'SELECT * FROM users WHERE id = 1',
                'similarity': 0.9,
                'selection_score': 0.8
            },
            {
                'question': '统计订单',
                'sql': 'SELECT COUNT(*) FROM orders',
                'similarity': 0.7,
                'selection_score': 0.6
            },
            {
                'question': '无效查询',
                'sql': 'INVALID SQL STATEMENT',
                'similarity': 0.8,
                'selection_score': 0.7
            }
        ]
        
        finalized = self.generator._finalize_example_selection(examples, "查询用户")
        
        # 应该过滤掉无效SQL的示例
        self.assertEqual(len(finalized), 2)
        
        # 检查排序是否正确（高相似度优先）
        self.assertEqual(finalized[0]['similarity'], 0.9)
    
    def test_enhanced_select_optimal_examples(self):
        """测试增强的示例选择算法"""
        examples = [
            {
                'question': '查询用户信息',
                'sql': 'SELECT * FROM users WHERE id = 1',
                'similarity': 0.9,
                'rating': 1.0,
                'usage_count': 5,
                'created_at': datetime.now().isoformat()
            },
            {
                'question': '查询用户数据',  # 与第一个相似
                'sql': 'SELECT name FROM users WHERE id = 2',
                'similarity': 0.85,
                'rating': 0.8,
                'usage_count': 3,
                'created_at': datetime.now().isoformat()
            },
            {
                'question': '统计订单数量',  # 不同类型
                'sql': 'SELECT COUNT(*) FROM orders',
                'similarity': 0.7,
                'rating': 1.2,
                'usage_count': 10,
                'created_at': (datetime.now() - timedelta(days=7)).isoformat()
            },
            {
                'question': '无效示例',  # 应该被过滤
                'sql': 'SELECT',
                'similarity': 0.6
            }
        ]
        
        result = self.generator._select_optimal_examples("查询用户", examples, max_examples=2)
        
        # 应该选择2个有效示例
        self.assertEqual(len(result), 2)
        
        # 应该包含多样化的示例
        questions = [ex['question'] for ex in result]
        self.assertIn('查询用户信息', questions)
        self.assertIn('统计订单数量', questions)  # 多样性过滤应该选择不同类型的示例
    
    def test_enhanced_truncate_prompt_intelligently(self):
        """测试增强的智能提示词截断"""
        long_prompt = """数据库Schema信息:
CREATE TABLE users (id INT, name VARCHAR(50), email VARCHAR(100));
CREATE TABLE orders (id INT, user_id INT, amount DECIMAL(10,2));

相关表名:
users, orders, products

参考相似查询示例:
示例 1:
问题: 查询用户信息
SQL: SELECT * FROM users WHERE id = 1
相似度: 0.900
说明: 基础用户查询

示例 2:
问题: 统计订单数量
SQL: SELECT COUNT(*) FROM orders
相似度: 0.800
说明: 订单统计查询

示例 3:
问题: 复杂联合查询
SQL: SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name
相似度: 0.700
说明: 多表联合查询

💡 提示: 以上示例与当前问题有一定相似性，请参考其查询思路和SQL结构。

用户问题: 查询特定用户的订单信息

请基于以上信息生成准确的SQL查询语句。
要求:
1. 只输出SQL语句，不要包含解释
2. 确保语法正确且符合安全要求
3. 优先使用提供的Schema信息
4. 可以参考相似示例的查询思路，但要根据具体问题调整"""
        
        # 测试严格的长度限制
        truncated = self.generator._truncate_prompt_intelligently(long_prompt, 800)
        
        # 检查长度
        self.assertLessEqual(len(truncated), 800)
        
        # 检查重要信息是否保留
        self.assertIn("用户问题:", truncated)
        self.assertIn("数据库Schema信息:", truncated)
        self.assertIn("查询特定用户的订单信息", truncated)
        
        # 检查是否保留了最高质量的示例（相似度最高的）
        if "示例" in truncated:
            self.assertIn("相似度: 0.900", truncated)  # 最高相似度的示例应该被保留
    
    def test_prompt_length_control_with_max_examples(self):
        """测试提示词长度控制与最大示例数限制"""
        question = "查询用户信息"
        schema_info = "CREATE TABLE users (id INT, name VARCHAR(50))"
        
        # 创建多个示例
        rag_result = Mock()
        rag_result.found_match = True
        rag_result.similar_examples = []
        
        for i in range(5):  # 创建5个示例，但应该只选择最多3个
            rag_result.similar_examples.append({
                'question': f'查询示例{i}',
                'sql': f'SELECT * FROM table_{i} WHERE id = {i}',
                'similarity': 0.9 - i * 0.1,
                'rating': 1.0,
                'usage_count': 5 - i,
                'created_at': datetime.now().isoformat()
            })
        
        prompt = self.generator.build_rag_prompt(question, schema_info, rag_result)
        
        # 计算实际示例数量（通过计算"示例 X:"模式）
        import re
        example_pattern = r'示例 \d+:'
        example_matches = re.findall(example_pattern, prompt)
        example_count = len(example_matches)
        
        self.assertLessEqual(example_count, 3)  # 应该不超过3个示例
        
        # 验证确实包含了示例
        if example_count > 0:
            self.assertIn("参考相似查询示例:", prompt)
    
    def test_example_quality_scoring(self):
        """测试示例质量评分的准确性"""
        # 高质量示例
        high_quality_example = {
            'similarity': 0.9,
            'rating': 1.5,
            'usage_count': 10,
            'sql': 'SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name',
            'created_at': datetime.now().isoformat()
        }
        
        # 低质量示例
        low_quality_example = {
            'similarity': 0.5,
            'rating': -0.5,
            'usage_count': 1,
            'sql': 'SELECT * FROM users',
            'created_at': (datetime.now() - timedelta(days=365)).isoformat()
        }
        
        high_score = self.generator._calculate_example_score("复杂查询", high_quality_example)
        low_score = self.generator._calculate_example_score("复杂查询", low_quality_example)
        
        # 高质量示例应该得到更高的分数
        self.assertGreater(high_score, low_score)
        self.assertGreaterEqual(high_score, 0.0)
        self.assertLessEqual(high_score, 1.0)
        self.assertGreaterEqual(low_score, 0.0)
        self.assertLessEqual(low_score, 1.0)
    
    def test_diversity_filter_effectiveness(self):
        """测试多样性过滤的有效性"""
        # 创建相似的示例
        similar_examples = [
            {
                'question': '查询用户信息',
                'sql': 'SELECT * FROM users WHERE id = 1',
                'selection_score': 0.9
            },
            {
                'question': '查询用户数据',  # 非常相似
                'sql': 'SELECT name FROM users WHERE id = 2',
                'selection_score': 0.85
            },
            {
                'question': '获取用户详情',  # 也很相似
                'sql': 'SELECT * FROM users WHERE name = "test"',
                'selection_score': 0.8
            },
            {
                'question': '统计订单总数',  # 完全不同的类型
                'sql': 'SELECT COUNT(*) FROM orders',
                'selection_score': 0.7
            }
        ]
        
        result = self.generator._apply_diversity_filter(similar_examples, max_examples=3)
        
        # 应该选择多样化的示例
        self.assertLessEqual(len(result), 3)
        
        # 应该包含不同类型的查询
        questions = [ex['question'] for ex in result]
        self.assertIn('查询用户信息', questions)  # 最高分的应该被选中
        self.assertIn('统计订单总数', questions)  # 不同类型的应该被选中
    
    def test_prompt_structure_integrity(self):
        """测试提示词结构完整性"""
        question = "查询用户订单信息"
        schema_info = "CREATE TABLE users (id INT, name VARCHAR(50))"
        
        prompt = self.generator.build_rag_prompt(question, schema_info)
        
        # 检查基本结构
        sections = [
            "数据库Schema信息:",
            "用户问题:",
            "请基于以上信息生成准确的SQL查询语句",
            "要求:"
        ]
        
        for section in sections:
            self.assertIn(section, prompt)
        
        # 检查逻辑顺序
        schema_pos = prompt.find("数据库Schema信息:")
        question_pos = prompt.find("用户问题:")
        requirements_pos = prompt.find("要求:")
        
        self.assertLess(schema_pos, question_pos)
        self.assertLess(question_pos, requirements_pos)


if __name__ == '__main__':
    unittest.main()