"""
RAG降级和错误处理集成测试
验证ChromaDB连接失败、Embedding服务异常等情况的处理
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime, timedelta

from chatbi.knowledge_base.rag_fallback_handler import (
    RAGFallbackHandler, FallbackLevel, ErrorType, ErrorRecord,
    FallbackConfig, HealthStatus, get_fallback_handler
)
from chatbi.knowledge_base.data_consistency_guard import (
    DataConsistencyGuard, ValidationLevel, DataIssueType, ValidationIssue,
    ValidationResult, get_consistency_guard
)


class TestRAGFallbackHandler(unittest.TestCase):
    """RAG降级处理器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = FallbackConfig(
            max_retries=2,
            retry_delay=0.1,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=5
        )
        self.handler = RAGFallbackHandler(self.config)
    
    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.handler.config.max_retries, 2)
        self.assertTrue(self.handler.health_status.is_healthy)
        self.assertEqual(self.handler.health_status.fallback_level, FallbackLevel.NONE)
        self.assertFalse(self.handler._circuit_breaker_open)
    
    def test_error_classification(self):
        """测试错误分类"""
        # 连接错误
        conn_error = Exception("Connection failed")
        self.assertEqual(
            self.handler._classify_error(conn_error), 
            ErrorType.CONNECTION_ERROR
        )
        
        # 嵌入错误
        embed_error = Exception("Embedding service error")
        self.assertEqual(
            self.handler._classify_error(embed_error), 
            ErrorType.EMBEDDING_ERROR
        )
        
        # 向量存储错误
        vector_error = Exception("ChromaDB error")
        self.assertEqual(
            self.handler._classify_error(vector_error), 
            ErrorType.VECTOR_STORE_ERROR
        )
        
        # 超时错误
        timeout_error = Exception("Request timeout")
        self.assertEqual(
            self.handler._classify_error(timeout_error), 
            ErrorType.TIMEOUT_ERROR
        )
        
        # 内存错误
        memory_error = Exception("Out of memory")
        self.assertEqual(
            self.handler._classify_error(memory_error), 
            ErrorType.MEMORY_ERROR
        )
        
        # 未知错误
        unknown_error = Exception("Unknown error")
        self.assertEqual(
            self.handler._classify_error(unknown_error), 
            ErrorType.UNKNOWN_ERROR
        )
    
    def test_should_retry_logic(self):
        """测试重试逻辑"""
        # 应该重试的错误
        self.assertTrue(self.handler._should_retry(ErrorType.CONNECTION_ERROR))
        self.assertTrue(self.handler._should_retry(ErrorType.TIMEOUT_ERROR))
        
        # 不应该重试的错误
        self.assertFalse(self.handler._should_retry(ErrorType.MEMORY_ERROR))
    
    def test_error_handling_success(self):
        """测试错误处理（成功情况）"""
        success_count = 0
        
        def mock_operation():
            nonlocal success_count
            success_count += 1
            return "success"
        
        result = self.handler.handle_operation("test_operation", mock_operation)
        
        self.assertEqual(result, "success")
        self.assertEqual(success_count, 1)
        self.assertTrue(self.handler.health_status.is_healthy)
        self.assertEqual(self.handler.health_status.consecutive_failures, 0)
    
    def test_error_handling_with_retry(self):
        """测试错误处理（重试情况）"""
        attempt_count = 0
        
        def mock_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise Exception("Connection failed")
            return "success"
        
        result = self.handler.handle_operation("test_operation", mock_operation)
        
        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 2)
        self.assertTrue(self.handler.health_status.is_healthy)
    
    def test_error_handling_with_fallback(self):
        """测试错误处理（降级情况）"""
        def mock_operation():
            raise Exception("Connection failed")
        
        def mock_fallback():
            return "fallback_result"
        
        result = self.handler.handle_operation("test_operation", mock_operation, mock_fallback)
        
        self.assertEqual(result, "fallback_result")
        self.assertFalse(self.handler.health_status.is_healthy)
        self.assertGreater(self.handler.health_status.consecutive_failures, 0)
    
    def test_circuit_breaker(self):
        """测试熔断器"""
        def failing_operation():
            raise Exception("Connection failed")
        
        # 触发多次失败以开启熔断器
        for i in range(self.config.circuit_breaker_threshold):
            try:
                self.handler.handle_operation("test_operation", failing_operation)
            except:
                pass
        
        # 验证熔断器已开启
        self.assertTrue(self.handler._circuit_breaker_open)
        
        # 测试熔断器阻止操作
        with self.assertRaises(Exception):
            self.handler.handle_operation("test_operation", failing_operation)
    
    def test_circuit_breaker_timeout(self):
        """测试熔断器超时"""
        # 手动开启熔断器
        self.handler._open_circuit_breaker()
        self.handler._circuit_breaker_open_time = datetime.now() - timedelta(seconds=10)
        
        # 验证熔断器因超时而关闭
        self.assertFalse(self.handler._is_circuit_breaker_open())
    
    def test_cache_operations(self):
        """测试缓存操作"""
        # 添加到缓存
        test_data = {"question": "test", "sql": "SELECT 1"}
        self.handler.add_to_cache("test_key", test_data)
        
        # 从缓存获取
        cached_data = self.handler.get_from_cache("test_key")
        self.assertEqual(cached_data, test_data)
        
        # 获取不存在的键
        missing_data = self.handler.get_from_cache("missing_key")
        self.assertIsNone(missing_data)
    
    def test_fallback_search_results(self):
        """测试降级搜索结果"""
        # 设置降级级别为缓存模式
        self.handler.health_status.fallback_level = FallbackLevel.CACHE_ONLY
        
        # 添加测试数据到缓存
        test_data = {
            "question": "查询用户信息",
            "sql": "SELECT * FROM users",
            "similarity": 0.8
        }
        self.handler.add_to_cache("test_key", test_data)
        
        # 执行降级搜索
        results = self.handler.get_fallback_search_results("查询用户")
        
        # 验证结果
        self.assertGreater(len(results), 0)
        self.assertIn("source", results[0])
        self.assertEqual(results[0]["source"], "cache")
    
    def test_health_status_reporting(self):
        """测试健康状态报告"""
        # 记录一些错误
        self.handler._record_error(
            ErrorType.CONNECTION_ERROR, 
            "Test error", 
            "test_operation", 
            1
        )
        
        # 获取健康状态
        status = self.handler.get_health_status()
        
        # 验证状态信息
        self.assertIn("is_healthy", status)
        self.assertIn("error_count", status)
        self.assertIn("consecutive_failures", status)
        self.assertIn("fallback_level", status)
        self.assertIn("circuit_breaker_open", status)
        self.assertIn("cache_size", status)
    
    def test_error_summary(self):
        """测试错误摘要"""
        # 记录不同类型的错误
        self.handler._record_error(
            ErrorType.CONNECTION_ERROR, 
            "Connection failed", 
            "test_op1", 
            1
        )
        self.handler._record_error(
            ErrorType.EMBEDDING_ERROR, 
            "Embedding failed", 
            "test_op2", 
            1
        )
        
        # 获取错误摘要
        summary = self.handler.get_error_summary(hours=1)
        
        # 验证摘要信息
        self.assertEqual(summary["total_errors"], 2)
        self.assertIn("connection_error", summary["error_by_type"])
        self.assertIn("embedding_error", summary["error_by_type"])
        self.assertIsNotNone(summary["most_recent_error"])
    
    def test_reset_health_status(self):
        """测试重置健康状态"""
        # 设置不健康状态
        self.handler.health_status.is_healthy = False
        self.handler.health_status.consecutive_failures = 5
        self.handler._open_circuit_breaker()
        
        # 重置健康状态
        self.handler.reset_health_status()
        
        # 验证状态已重置
        self.assertTrue(self.handler.health_status.is_healthy)
        self.assertEqual(self.handler.health_status.consecutive_failures, 0)
        self.assertFalse(self.handler._circuit_breaker_open)
    
    def test_global_instance(self):
        """测试全局实例"""
        handler1 = get_fallback_handler()
        handler2 = get_fallback_handler()
        
        # 验证返回同一个实例
        self.assertIs(handler1, handler2)
        self.assertIsInstance(handler1, RAGFallbackHandler)


class TestDataConsistencyGuard(unittest.TestCase):
    """数据一致性保护器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.guard = DataConsistencyGuard(ValidationLevel.STANDARD)
    
    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.guard.validation_level, ValidationLevel.STANDARD)
        self.assertIsInstance(self.guard._field_schemas, dict)
        self.assertIn("question", self.guard._field_schemas)
        self.assertIn("sql", self.guard._field_schemas)
    
    def test_validate_valid_data(self):
        """测试验证有效数据"""
        valid_data = {
            "question": "查询用户信息",
            "sql": "SELECT * FROM users WHERE id = 1",
            "description": "获取用户详细信息",
            "tags": ["查询", "用户"],
            "rating": 1.0,
            "usage_count": 5
        }
        
        result = self.guard.validate_knowledge_item(valid_data)
        
        self.assertTrue(result.is_valid)
        # 可能会有警告，但不应该有错误
        error_issues = [issue for issue in result.issues if issue.severity == "error"]
        self.assertEqual(len(error_issues), 0)
    
    def test_validate_missing_required_fields(self):
        """测试验证缺少必需字段"""
        invalid_data = {
            "description": "缺少问题和SQL"
        }
        
        result = self.guard.validate_knowledge_item(invalid_data)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.issues), 0)
        
        # 检查是否有缺少字段的错误
        missing_field_issues = [
            issue for issue in result.issues 
            if issue.issue_type == DataIssueType.MISSING_FIELD
        ]
        self.assertGreater(len(missing_field_issues), 0)
    
    def test_validate_invalid_types(self):
        """测试验证无效类型"""
        invalid_data = {
            "question": "测试问题",
            "sql": "SELECT 1",
            "rating": "invalid_rating",  # 应该是数字
            "usage_count": "invalid_count",  # 应该是整数
            "tags": "invalid_tags"  # 应该是列表
        }
        
        result = self.guard.validate_knowledge_item(invalid_data)
        
        # 应该有类型错误或已修正
        type_issues = [
            issue for issue in result.issues 
            if issue.issue_type == DataIssueType.INVALID_TYPE
        ]
        self.assertGreater(len(type_issues), 0)
    
    def test_validate_field_values(self):
        """测试验证字段值"""
        invalid_data = {
            "question": "ab",  # 太短
            "sql": "SELECT " + "x" * 20000,  # 太长
            "rating": 100.0,  # 超出范围
            "usage_count": -5  # 负数
        }
        
        result = self.guard.validate_knowledge_item(invalid_data)
        
        # 应该有值错误
        value_issues = [
            issue for issue in result.issues 
            if issue.issue_type == DataIssueType.INVALID_VALUE
        ]
        self.assertGreater(len(value_issues), 0)
        
        # 检查是否有修正数据
        if result.corrected_data:
            self.assertLessEqual(result.corrected_data["rating"], 10.0)
            self.assertGreaterEqual(result.corrected_data["usage_count"], 0)
    
    def test_validate_sql_safety(self):
        """测试SQL安全性验证"""
        dangerous_data = {
            "question": "危险SQL",
            "sql": "DROP TABLE users; DELETE FROM orders;",
            "description": "包含危险操作的SQL"
        }
        
        result = self.guard.validate_knowledge_item(dangerous_data)
        
        self.assertFalse(result.is_valid)
        
        # 检查是否检测到危险操作
        sql_issues = [
            issue for issue in result.issues 
            if issue.field_name == "sql" and "危险操作" in issue.description
        ]
        self.assertGreater(len(sql_issues), 0)
    
    def test_validate_data_consistency(self):
        """测试数据一致性验证"""
        inconsistent_data = {
            "question": "测试问题",
            "sql": "SELECT 1",
            "created_at": "2023-12-01T10:00:00",
            "updated_at": "2023-11-01T10:00:00",  # 更新时间早于创建时间
            "rating": 0,
            "usage_count": 10  # 有使用但评分为0
        }
        
        result = self.guard.validate_knowledge_item(inconsistent_data)
        
        # 检查是否检测到不一致问题
        consistency_issues = [
            issue for issue in result.issues 
            if issue.issue_type == DataIssueType.INCONSISTENT_DATA
        ]
        self.assertGreater(len(consistency_issues), 0)
    
    def test_check_duplicate_data(self):
        """测试重复数据检查"""
        data1 = {
            "question": "查询用户",
            "sql": "SELECT * FROM users"
        }
        
        data2 = {
            "question": "查询用户",
            "sql": "SELECT * FROM users"
        }
        
        # 第一次验证应该成功
        result1 = self.guard.validate_knowledge_item(data1)
        self.assertTrue(result1.is_valid)
        
        # 第二次验证应该检测到重复
        result2 = self.guard.validate_knowledge_item(data2)
        
        duplicate_issues = [
            issue for issue in result2.issues 
            if issue.issue_type == DataIssueType.DUPLICATE_DATA
        ]
        self.assertGreater(len(duplicate_issues), 0)
    
    def test_sanitize_data(self):
        """测试数据清理"""
        dirty_data = {
            "question": "测试问题",
            "sql": "SELECT 1",
            "rating": "5.0",  # 字符串，应该转换为数字
            "tags": '["标签1", "标签2"]',  # JSON字符串，应该转换为列表
            "description": "x" * 6000  # 过长，应该截断
        }
        
        cleaned_data = self.guard.sanitize_data(dirty_data)
        
        # 验证数据已清理
        if cleaned_data.get("rating") != dirty_data["rating"]:
            # 如果有修正数据，验证类型转换
            self.assertIsInstance(cleaned_data["rating"], (int, float))
        
        if cleaned_data.get("tags") != dirty_data["tags"]:
            # 如果有修正数据，验证类型转换
            self.assertIsInstance(cleaned_data["tags"], list)
        
        # 描述长度应该被限制
        self.assertLessEqual(len(cleaned_data["description"]), 5000)
    
    def test_validation_stats(self):
        """测试验证统计"""
        stats = self.guard.get_validation_stats()
        
        self.assertIn("validation_level", stats)
        self.assertIn("known_hashes_count", stats)
        self.assertIn("field_schemas_count", stats)
        self.assertEqual(stats["validation_level"], "standard")
    
    def test_clear_known_hashes(self):
        """测试清空已知哈希"""
        # 添加一些数据以生成哈希
        data = {
            "question": "测试问题",
            "sql": "SELECT 1"
        }
        self.guard.validate_knowledge_item(data)
        
        # 验证哈希已添加
        self.assertGreater(len(self.guard._known_hashes), 0)
        
        # 清空哈希
        self.guard.clear_known_hashes()
        
        # 验证哈希已清空
        self.assertEqual(len(self.guard._known_hashes), 0)
    
    def test_global_instance(self):
        """测试全局实例"""
        guard1 = get_consistency_guard()
        guard2 = get_consistency_guard()
        
        # 验证返回同一个实例
        self.assertIs(guard1, guard2)
        self.assertIsInstance(guard1, DataConsistencyGuard)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """测试初始化"""
        self.fallback_handler = RAGFallbackHandler()
        self.consistency_guard = DataConsistencyGuard()
    
    def test_integrated_error_handling_and_validation(self):
        """测试集成的错误处理和数据验证"""
        # 模拟一个包含数据验证和错误处理的操作
        def risky_operation(data):
            # 首先验证数据
            validation_result = self.consistency_guard.validate_knowledge_item(data)
            if not validation_result.is_valid:
                raise ValueError("数据验证失败")
            
            # 模拟可能失败的操作
            if data.get("should_fail", False):
                raise Exception("Connection failed")
            
            return "success"
        
        def fallback_operation(data):
            # 降级操作：使用基本验证
            if "question" in data and "sql" in data:
                return "fallback_success"
            raise Exception("降级也失败")
        
        # 测试正常情况
        valid_data = {
            "question": "查询用户信息",
            "sql": "SELECT * FROM users"
        }
        
        result = self.fallback_handler.handle_operation(
            "integrated_test", 
            lambda: risky_operation(valid_data),
            lambda: fallback_operation(valid_data)
        )
        
        self.assertEqual(result, "success")
        
        # 测试错误情况
        invalid_data = {
            "question": "查询用户信息",
            "sql": "SELECT * FROM users",
            "should_fail": True
        }
        
        result = self.fallback_handler.handle_operation(
            "integrated_test", 
            lambda: risky_operation(invalid_data),
            lambda: fallback_operation(invalid_data)
        )
        
        self.assertEqual(result, "fallback_success")


if __name__ == '__main__':
    unittest.main()