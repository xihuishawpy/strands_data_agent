"""
增强版SQL知识库管理器单元测试
验证性能优化、批量操作、数据验证和版本管理功能
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import json
from datetime import datetime

from chatbi.knowledge_base.enhanced_sql_knowledge_manager import (
    EnhancedSQLKnowledgeManager, ValidationResult, BatchOperationResult,
    KnowledgeVersion, performance_monitor, get_enhanced_knowledge_manager
)
from chatbi.knowledge_base.rag_strategy import RAGResult


class TestEnhancedSQLKnowledgeManager(unittest.TestCase):
    """增强版SQL知识库管理器测试"""
    
    def setUp(self):
        """测试初始化"""
        with patch('chatbi.knowledge_base.enhanced_sql_knowledge_manager.CHROMADB_AVAILABLE', True):
            with patch('chatbi.knowledge_base.enhanced_sql_knowledge_manager.get_vector_store'):
                with patch('chatbi.knowledge_base.enhanced_sql_knowledge_manager.get_rag_strategy'):
                    self.manager = EnhancedSQLKnowledgeManager()
                    self.manager.vector_store = Mock()
                    self.manager.rag_strategy = Mock()
    
    def test_initialization(self):
        """测试初始化"""
        self.assertTrue(self.manager.enabled)
        self.assertIsNotNone(self.manager.vector_store)
        self.assertIsNotNone(self.manager.rag_strategy)
        self.assertEqual(self.manager._cache_ttl, 300)
        self.assertIn("search_count", self.manager._performance_stats)
    
    def test_input_validation_valid_data(self):
        """测试有效数据验证"""
        result = self.manager._validate_input_data(
            question="查询用户信息",
            sql="SELECT * FROM users WHERE id = 1",
            description="获取用户详细信息"
        )
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_input_validation_invalid_question(self):
        """测试无效问题验证"""
        # 空问题
        result = self.manager._validate_input_data("", "SELECT 1")
        self.assertFalse(result.is_valid)
        self.assertIn("问题不能为空", result.errors)
        
        # 问题过短
        result = self.manager._validate_input_data("ab", "SELECT 1")
        self.assertFalse(result.is_valid)
        self.assertIn("问题长度至少3个字符", result.errors)
    
    def test_input_validation_invalid_sql(self):
        """测试无效SQL验证"""
        # 空SQL
        result = self.manager._validate_input_data("测试问题", "")
        self.assertFalse(result.is_valid)
        self.assertIn("SQL不能为空", result.errors)
        
        # 非SELECT语句
        result = self.manager._validate_input_data("测试问题", "DROP TABLE users")
        self.assertFalse(result.is_valid)
        # 检查错误信息包含SQL语法错误
        error_found = any("只支持SELECT查询" in error for error in result.errors)
        self.assertTrue(error_found)
    
    def test_sql_syntax_validation(self):
        """测试SQL语法验证"""
        # 有效SQL
        result = self.manager._validate_sql_syntax("SELECT * FROM users")
        self.assertTrue(result["is_valid"])
        
        # 括号不匹配
        result = self.manager._validate_sql_syntax("SELECT * FROM (users")
        self.assertFalse(result["is_valid"])
        self.assertIn("括号不匹配", result["error"])
        
        # 引号不匹配
        result = self.manager._validate_sql_syntax("SELECT * FROM users WHERE name = 'test")
        self.assertFalse(result["is_valid"])
        self.assertIn("单引号不匹配", result["error"])
    
    def test_cache_operations(self):
        """测试缓存操作"""
        # 设置缓存
        cache_key = self.manager._get_cache_key("test_question")
        test_data = {"test": "data"}
        self.manager._set_cache(cache_key, test_data)
        
        # 获取缓存
        cached_data = self.manager._get_from_cache(cache_key)
        self.assertEqual(cached_data, test_data)
        
        # 缓存过期测试
        self.manager._cache_ttl = 0  # 设置为立即过期
        time.sleep(0.1)
        cached_data = self.manager._get_from_cache(cache_key)
        self.assertIsNone(cached_data)
    
    def test_search_knowledge_enhanced_with_cache(self):
        """测试增强搜索功能（使用缓存）"""
        # 模拟向量存储搜索结果
        mock_results = [
            {
                "question": "查询用户",
                "sql": "SELECT * FROM users",
                "similarity": 0.9,
                "rating": 1.0,
                "usage_count": 5
            }
        ]
        self.manager.vector_store.search_similar_questions.return_value = mock_results
        
        # 模拟RAG策略
        self.manager.rag_strategy.determine_strategy.return_value = "high_similarity_cached"
        self.manager.rag_strategy.should_use_cached_sql.return_value = True
        
        # 第一次搜索
        result1 = self.manager.search_knowledge_enhanced("查询用户信息")
        self.assertTrue(result1.found_match)
        self.assertEqual(result1.strategy, "high_similarity_cached")
        
        # 第二次搜索（应该使用缓存）
        result2 = self.manager.search_knowledge_enhanced("查询用户信息")
        self.assertTrue(result2.found_match)
        
        # 验证缓存命中
        self.assertEqual(self.manager._performance_stats["cache_hits"], 1)
    
    def test_batch_add_knowledge_success(self):
        """测试批量添加知识库条目（成功）"""
        # 准备测试数据
        items = [
            {
                "question": "查询用户1",
                "sql": "SELECT * FROM users WHERE id = 1",
                "description": "查询用户1"
            },
            {
                "question": "查询用户2", 
                "sql": "SELECT * FROM users WHERE id = 2",
                "description": "查询用户2"
            }
        ]
        
        # 模拟成功添加
        self.manager.vector_store.add_sql_knowledge.return_value = "test_id"
        
        # 执行批量添加
        result = self.manager.batch_add_knowledge(items, max_workers=2)
        
        # 验证结果
        self.assertEqual(result.total_items, 2)
        self.assertEqual(result.successful_items, 2)
        self.assertEqual(result.failed_items, 0)
        self.assertEqual(result.success_rate, 1.0)
    
    def test_batch_add_knowledge_with_validation_errors(self):
        """测试批量添加知识库条目（包含验证错误）"""
        # 准备测试数据（包含无效数据）
        items = [
            {
                "question": "查询用户1",
                "sql": "SELECT * FROM users WHERE id = 1",
                "description": "查询用户1"
            },
            {
                "question": "",  # 无效问题
                "sql": "DROP TABLE users",  # 无效SQL
                "description": "无效条目"
            }
        ]
        
        # 模拟成功添加
        self.manager.vector_store.add_sql_knowledge.return_value = "test_id"
        
        # 执行批量添加
        result = self.manager.batch_add_knowledge(items, validate=True)
        
        # 验证结果
        self.assertEqual(result.total_items, 2)
        self.assertEqual(result.successful_items, 1)
        self.assertEqual(result.failed_items, 1)
        self.assertEqual(len(result.errors), 1)
    
    def test_create_knowledge_version(self):
        """测试创建知识库版本"""
        # 模拟现有条目
        mock_metadata = {
            "question": "查询用户",
            "sql": "SELECT * FROM users",
            "description": "用户查询",
            "tags": "[]",
            "rating": 1.0,
            "versions": "[]"
        }
        
        self.manager.vector_store.collection.get.return_value = {
            "metadatas": [mock_metadata]
        }
        
        # 创建版本
        version_id = self.manager.create_knowledge_version(
            item_id="test_item",
            change_reason="优化SQL查询",
            created_by="test_user"
        )
        
        # 验证结果
        self.assertIsNotNone(version_id)
        self.assertTrue(version_id.startswith("v_test_item_"))
        
        # 验证更新调用
        self.manager.vector_store.collection.update.assert_called_once()
    
    def test_get_knowledge_versions(self):
        """测试获取知识库版本"""
        # 模拟版本数据
        version_data = {
            "version_id": "v_test_123",
            "item_id": "test_item",
            "question": "查询用户",
            "sql": "SELECT * FROM users",
            "description": "用户查询",
            "tags": "[]",
            "rating": 1.0,
            "created_at": datetime.now().isoformat(),
            "created_by": "test_user",
            "change_reason": "初始版本"
        }
        
        mock_metadata = {
            "versions": f'[{json.dumps(version_data)}]'
        }
        
        self.manager.vector_store.collection.get.return_value = {
            "metadatas": [mock_metadata]
        }
        
        # 获取版本
        versions = self.manager.get_knowledge_versions("test_item")
        
        # 验证结果
        self.assertEqual(len(versions), 1)
        self.assertIsInstance(versions[0], KnowledgeVersion)
        self.assertEqual(versions[0].version_id, "v_test_123")
        self.assertEqual(versions[0].created_by, "test_user")
    
    def test_performance_stats(self):
        """测试性能统计"""
        # 模拟一些搜索操作
        self.manager._performance_stats["search_count"] = 10
        self.manager._performance_stats["cache_hits"] = 3
        self.manager._performance_stats["avg_search_time"] = 0.5
        
        # 添加一些缓存数据
        self.manager._set_cache("key1", "data1")
        self.manager._set_cache("key2", "data2")
        
        # 获取统计信息
        stats = self.manager.get_performance_stats()
        
        # 验证统计信息
        self.assertEqual(stats["search_count"], 10)
        self.assertEqual(stats["cache_hits"], 3)
        self.assertEqual(stats["cache_hit_rate"], 0.3)
        self.assertEqual(stats["avg_search_time"], 0.5)
        self.assertEqual(stats["cache_size"], 2)
        self.assertTrue(stats["enabled"])
    
    def test_clear_cache(self):
        """测试清空缓存"""
        # 添加缓存数据
        self.manager._set_cache("key1", "data1")
        self.manager._set_cache("key2", "data2")
        self.assertEqual(len(self.manager._cache), 2)
        
        # 清空缓存
        self.manager.clear_cache()
        self.assertEqual(len(self.manager._cache), 0)
    
    def test_optimize_search_algorithm(self):
        """测试优化搜索算法"""
        # 模拟基础搜索结果
        mock_results = [
            {
                "question": "查询用户信息",
                "sql": "SELECT * FROM users WHERE id = ?",
                "similarity": 0.8,
                "rating": 1.0,
                "usage_count": 5
            },
            {
                "question": "获取用户数据",
                "sql": "SELECT name, email FROM users",
                "similarity": 0.7,
                "rating": 0.5,
                "usage_count": 2
            }
        ]
        
        self.manager.vector_store.search_similar_questions.return_value = mock_results
        
        # 执行优化搜索
        results = self.manager.optimize_search_algorithm("查询用户信息", top_k=2)
        
        # 验证结果
        self.assertEqual(len(results), 2)
        self.assertIn("enhanced_similarity", results[0])
        self.assertIn("original_similarity", results[0])
        
        # 验证结果按增强相似度排序
        self.assertGreaterEqual(results[0]["enhanced_similarity"], 
                               results[1]["enhanced_similarity"])
    
    def test_keyword_similarity_calculation(self):
        """测试关键词相似度计算"""
        # 相似问题
        similarity1 = self.manager._calculate_keyword_similarity(
            "查询用户信息", "获取用户数据"
        )
        self.assertGreater(similarity1, 0)
        
        # 不相似问题
        similarity2 = self.manager._calculate_keyword_similarity(
            "查询用户信息", "删除订单记录"
        )
        self.assertLess(similarity2, similarity1)
    
    def test_complexity_similarity_calculation(self):
        """测试复杂度相似度计算"""
        # 简单查询匹配简单SQL
        similarity1 = self.manager._calculate_complexity_similarity(
            "查询用户", "SELECT * FROM users"
        )
        
        # 复杂查询匹配复杂SQL
        similarity2 = self.manager._calculate_complexity_similarity(
            "统计用户关联订单数量", 
            "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id"
        )
        
        # 复杂度匹配应该有合理的分数
        self.assertGreater(similarity1, 0.5)
        self.assertGreater(similarity2, 0.5)
    
    def test_global_instance(self):
        """测试全局实例"""
        with patch('chatbi.knowledge_base.enhanced_sql_knowledge_manager.CHROMADB_AVAILABLE', True):
            with patch('chatbi.knowledge_base.enhanced_sql_knowledge_manager.get_vector_store'):
                with patch('chatbi.knowledge_base.enhanced_sql_knowledge_manager.get_rag_strategy'):
                    manager1 = get_enhanced_knowledge_manager()
                    manager2 = get_enhanced_knowledge_manager()
                    
                    # 验证返回同一个实例
                    self.assertIs(manager1, manager2)
                    self.assertIsInstance(manager1, EnhancedSQLKnowledgeManager)


class TestPerformanceMonitor(unittest.TestCase):
    """性能监控装饰器测试"""
    
    def test_performance_monitor_success(self):
        """测试性能监控装饰器（成功情况）"""
        @performance_monitor
        def test_function():
            time.sleep(0.1)
            return "success"
        
        with patch('chatbi.knowledge_base.enhanced_sql_knowledge_manager.logger') as mock_logger:
            result = test_function()
            
            self.assertEqual(result, "success")
            # 验证日志记录
            mock_logger.info.assert_called()
            log_message = mock_logger.info.call_args[0][0]
            self.assertIn("test_function 执行时间", log_message)
    
    def test_performance_monitor_exception(self):
        """测试性能监控装饰器（异常情况）"""
        @performance_monitor
        def test_function():
            raise ValueError("测试异常")
        
        with patch('chatbi.knowledge_base.enhanced_sql_knowledge_manager.logger') as mock_logger:
            with self.assertRaises(ValueError):
                test_function()
            
            # 验证错误日志记录
            mock_logger.error.assert_called()
            log_message = mock_logger.error.call_args[0][0]
            self.assertIn("test_function 执行失败", log_message)


class TestDataClasses(unittest.TestCase):
    """数据类测试"""
    
    def test_validation_result(self):
        """测试验证结果数据类"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 添加错误
        result.add_error("测试错误")
        self.assertFalse(result.is_valid)
        self.assertIn("测试错误", result.errors)
        
        # 添加警告
        result.add_warning("测试警告")
        self.assertIn("测试警告", result.warnings)
    
    def test_batch_operation_result(self):
        """测试批量操作结果数据类"""
        result = BatchOperationResult(
            total_items=10,
            successful_items=8,
            failed_items=2,
            errors=[],
            execution_time=1.5
        )
        
        self.assertEqual(result.success_rate, 0.8)
        
        # 测试零除法保护
        empty_result = BatchOperationResult(
            total_items=0,
            successful_items=0,
            failed_items=0,
            errors=[],
            execution_time=0.0
        )
        self.assertEqual(empty_result.success_rate, 0.0)
    
    def test_knowledge_version(self):
        """测试知识库版本数据类"""
        version = KnowledgeVersion(
            version_id="v_test_123",
            item_id="test_item",
            question="测试问题",
            sql="SELECT 1",
            description="测试描述",
            tags=["测试"],
            rating=1.0,
            created_at=datetime.now(),
            created_by="test_user",
            change_reason="测试变更"
        )
        
        self.assertEqual(version.version_id, "v_test_123")
        self.assertEqual(version.created_by, "test_user")
        self.assertIsInstance(version.created_at, datetime)


if __name__ == '__main__':
    # 需要导入json模块用于测试
    import json
    unittest.main()