"""
RAG错误处理集成测试
测试降级处理和数据一致性保护机制
"""

import unittest
import tempfile
import shutil
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from chatbi.knowledge_base.rag_fallback_handler import (
    RAGFallbackHandler, FailureType, FallbackConfig, get_fallback_handler
)
from chatbi.knowledge_base.data_consistency_guard import (
    DataConsistencyGuard, ValidationResult, get_consistency_guard
)


class TestRAGFallbackHandler(unittest.TestCase):
    """RAG降级处理器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = FallbackConfig(
            max_retry_attempts=2,
            retry_delay=0.1,  # 缩短测试时间
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=5
        )
        self.handler = RAGFallbackHandler(self.config)
    
    def test_failure_classification(self):
        """测试故障分类"""
        # ChromaDB连接错误
        chromadb_error = Exception("ChromaDB connection failed")
        failure_type = self.handler._classify_failure(chromadb_error)
        self.assertEqual(failure_type, FailureType.CHROMADB_CONNECTION)
        
        # Embedding服务错误
        embedding_error = Exception("Qwen API quota exceeded")
        failure_type = self.handler._classify_failure(embedding_error)
        self.assertEqual(failure_type, FailureType.EMBEDDING_SERVICE)
        
        # 搜索超时错误
        timeout_error = Exception("Search timeout occurred")
        failure_type = self.handler._classify_failure(timeout_error)
        self.assertEqual(failure_type, FailureType.VECTOR_SEARCH_TIMEOUT)
        
        # 数据损坏错误
        corruption_error = Exception("Invalid data format detected")
        failure_type = self.handler._classify_failure(corruption_error)
        self.assertEqual(failure_type, FailureType.DATA_CORRUPTION)
        
        # 内存溢出错误
        memory_error = Exception("Out of memory allocation failed")
        failure_type = self.handler._classify_failure(memory_error)
        self.assertEqual(failure_type, FailureType.MEMORY_OVERFLOW)
        
        # 未知错误
        unknown_error = Exception("Something went wrong")
        failure_type = self.handler._classify_failure(unknown_error)
        self.assertEqual(failure_type, FailureType.UNKNOWN_ERROR)
    
    def test_circuit_breaker_mechanism(self):
        """测试断路器机制"""
        failure_type = FailureType.CHROMADB_CONNECTION
        
        # 初始状态：断路器关闭
        self.assertFalse(self.handler._is_circuit_breaker_open(failure_type))
        
        # 触发多次故障
        for i in range(self.config.circuit_breaker_threshold):
            self.handler._update_circuit_breaker(failure_type)
        
        # 断路器应该开启
        self.assertTrue(self.handler._is_circuit_breaker_open(failure_type))
        
        # 重置断路器
        self.handler._reset_circuit_breaker(failure_type)
        self.assertFalse(self.handler._is_circuit_breaker_open(failure_type))
    
    def test_fallback_cache(self):
        """测试降级缓存"""
        # 添加缓存条目
        question = "查询用户数据"
        sql = "SELECT * FROM users"
        self.handler.add_to_fallback_cache(question, sql, 0.9)
        
        # 测试缓存命中
        cached_result = self.handler._try_cache_fallback(question)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result["sql"], sql)
        self.assertEqual(cached_result["confidence"], 0.9)
        
        # 测试相似问题匹配
        similar_question = "查询用户信息"
        cached_result = self.handler._try_cache_fallback(similar_question)
        self.assertIsNotNone(cached_result)  # 应该匹配到相似问题
        
        # 测试不匹配的问题
        different_question = "删除订单数据"
        cached_result = self.handler._try_cache_fallback(different_question)
        self.assertIsNone(cached_result)  # 不应该匹配
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_recovery_strategies(self, mock_sleep):
        """测试恢复策略"""
        from chatbi.knowledge_base.rag_fallback_handler import FailureRecord
        
        # 测试搜索超时恢复
        timeout_record = FailureRecord(
            failure_type=FailureType.VECTOR_SEARCH_TIMEOUT,
            timestamp=datetime.now(),
            error_message="Search timeout",
            context={}
        )
        
        result = self.handler._recover_search_timeout(timeout_record)
        self.assertTrue(result["success"])
        self.assertEqual(result["strategy"], "timeout_recovery")
        
        # 测试内存溢出恢复
        memory_record = FailureRecord(
            failure_type=FailureType.MEMORY_OVERFLOW,
            timestamp=datetime.now(),
            error_message="Out of memory",
            context={}
        )
        
        result = self.handler._recover_memory_overflow(memory_record)
        self.assertTrue(result["success"])
        self.assertEqual(result["strategy"], "memory_cleanup")
    
    def test_fallback_strategy_execution(self):
        """测试降级策略执行"""
        question = "测试问题"
        schema_info = "测试架构"
        
        # 测试缓存降级策略
        self.handler.add_to_fallback_cache(question, "SELECT 1", 0.8)
        
        result = self.handler._execute_fallback_strategy(
            question, schema_info, FailureType.CHROMADB_CONNECTION
        )
        
        self.assertTrue(result["success"])
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["strategy"], "cache_fallback")
        self.assertEqual(result["sql"], "SELECT 1")
        
        # 测试标准生成降级策略（无缓存匹配）
        different_question = "不同的问题"
        result = self.handler._execute_fallback_strategy(
            different_question, schema_info, FailureType.EMBEDDING_SERVICE
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["strategy"], "standard_generation")
        self.assertIsNone(result["sql"])
    
    def test_failure_statistics(self):
        """测试故障统计"""
        # 模拟一些故障
        errors = [
            Exception("ChromaDB error 1"),
            Exception("ChromaDB error 2"),
            Exception("Embedding service error"),
            Exception("Timeout error")
        ]
        
        for error in errors:
            self.handler.handle_rag_failure(error, "test question", "test schema")
        
        # 获取统计信息
        stats = self.handler.get_failure_statistics()
        
        self.assertEqual(stats["total_failures"], 4)
        self.assertIn("chromadb_connection", stats["failure_by_type"])
        self.assertIn("embedding_service", stats["failure_by_type"])
        self.assertIn("vector_search_timeout", stats["failure_by_type"])
        
        # 检查最近故障记录
        self.assertEqual(len(stats["recent_failures"]), 4)
    
    def test_global_handler_instance(self):
        """测试全局处理器实例"""
        handler1 = get_fallback_handler()
        handler2 = get_fallback_handler()
        
        # 验证返回同一个实例
        self.assertIs(handler1, handler2)
        self.assertIsInstance(handler1, RAGFallbackHandler)


class TestDataConsistencyGuard(unittest.TestCase):
    """数据一致性保护器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.guard = DataConsistencyGuard(backup_directory=self.temp_dir)
    
    def tearDown(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_knowledge_item_validation(self):
        """测试知识库条目验证"""
        # 有效条目
        valid_item = {
            "id": "test_1",
            "question": "查询用户数据",
            "sql": "SELECT * FROM users WHERE id = 1",
            "description": "查询单个用户",
            "tags": '["查询", "用户"]',
            "rating": 4.5,
            "usage_count": 10,
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T10:00:00"
        }
        
        result = self.guard.validate_knowledge_item(valid_item)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # 无效条目 - 缺少问题
        invalid_item = {
            "id": "test_2",
            "question": "",  # 空问题
            "sql": "SELECT * FROM users",
            "rating": 10.0,  # 超出范围
            "usage_count": -1  # 负数
        }
        
        result = self.guard.validate_knowledge_item(invalid_item)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_sql_syntax_validation(self):
        """测试SQL语法验证"""
        # 有效SQL
        valid_sql_item = {
            "question": "测试问题",
            "sql": "SELECT name, age FROM users WHERE active = 1"
        }
        self.assertTrue(self.guard._validate_sql_syntax(valid_sql_item))
        
        # 无效SQL - 缺少关键词
        invalid_sql_item = {
            "question": "测试问题",
            "sql": "name, age FROM users"
        }
        self.assertFalse(self.guard._validate_sql_syntax(invalid_sql_item))
        
        # 无效SQL - 括号不匹配
        unbalanced_sql_item = {
            "question": "测试问题",
            "sql": "SELECT COUNT( FROM users"
        }
        self.assertFalse(self.guard._validate_sql_syntax(unbalanced_sql_item))
    
    def test_timestamp_validation(self):
        """测试时间戳验证"""
        # 有效时间戳
        valid_timestamp_item = {
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T11:00:00"
        }
        self.assertTrue(self.guard._validate_timestamp(valid_timestamp_item))
        
        # 无效时间戳格式
        invalid_timestamp_item = {
            "created_at": "2024-13-01",  # 无效月份
            "updated_at": "not a timestamp"
        }
        self.assertFalse(self.guard._validate_timestamp(invalid_timestamp_item))
    
    def test_tags_format_validation(self):
        """测试标签格式验证"""
        # 有效标签 - JSON字符串
        valid_tags_item = {
            "tags": '["查询", "用户", "数据库"]'
        }
        self.assertTrue(self.guard._validate_tags_format(valid_tags_item))
        
        # 有效标签 - 列表
        valid_tags_list_item = {
            "tags": ["查询", "用户", "数据库"]
        }
        self.assertTrue(self.guard._validate_tags_format(valid_tags_list_item))
        
        # 无效标签 - 无效JSON
        invalid_tags_item = {
            "tags": '["查询", "用户"'  # 缺少闭合括号
        }
        self.assertFalse(self.guard._validate_tags_format(invalid_tags_item))
        
        # 无效标签 - 非列表类型
        invalid_tags_type_item = {
            "tags": "查询,用户"  # 字符串而非列表
        }
        self.assertFalse(self.guard._validate_tags_format(invalid_tags_type_item))
    
    def test_backup_and_restore(self):
        """测试备份和恢复功能"""
        # 创建模拟向量存储
        mock_vector_store = Mock()
        mock_vector_store.collection_name = "test_collection"
        mock_vector_store.collection.get.return_value = {
            "ids": ["test_1", "test_2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [
                {"question": "问题1", "sql": "SELECT 1"},
                {"question": "问题2", "sql": "SELECT 2"}
            ],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]]
        }
        
        # 测试备份
        backup_id = self.guard.backup_knowledge_base(
            vector_store=mock_vector_store,
            description="测试备份"
        )
        
        self.assertIsNotNone(backup_id)
        self.assertTrue(backup_id.startswith("backup_"))
        
        # 验证备份文件存在
        backup_file = os.path.join(self.temp_dir, f"{backup_id}.json")
        self.assertTrue(os.path.exists(backup_file))
        
        # 验证备份内容
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        self.assertEqual(backup_data["backup_id"], backup_id)
        self.assertEqual(backup_data["description"], "测试备份")
        self.assertEqual(len(backup_data["data"]["ids"]), 2)
        
        # 测试恢复
        mock_vector_store.client = Mock()
        mock_vector_store.client.delete_collection = Mock()
        mock_vector_store.client.create_collection = Mock()
        mock_vector_store.client.create_collection.return_value = Mock()
        mock_vector_store.collection = Mock()
        
        success = self.guard.restore_knowledge_base(backup_id, mock_vector_store)
        self.assertTrue(success)
        
        # 验证恢复过程中的调用
        mock_vector_store.client.delete_collection.assert_called_once()
        mock_vector_store.client.create_collection.assert_called_once()
        mock_vector_store.collection.add.assert_called_once()
    
    def test_corrupted_data_handling(self):
        """测试损坏数据处理"""
        # 创建模拟向量存储
        mock_vector_store = Mock()
        mock_vector_store.collection.get.return_value = {
            "metadatas": [{"question": "损坏的问题", "sql": "损坏的SQL"}],
            "documents": ["损坏的文档"]
        }
        mock_vector_store.collection.delete = Mock()
        
        # 测试处理损坏数据
        success = self.guard.handle_corrupted_data("corrupted_item_1", mock_vector_store)
        self.assertTrue(success)
        
        # 验证删除操作被调用
        mock_vector_store.collection.delete.assert_called_once_with(ids=["corrupted_item_1"])
        
        # 验证备份文件被创建
        backup_files = [f for f in os.listdir(self.temp_dir) if f.startswith("corrupted_data_")]
        self.assertGreater(len(backup_files), 0)
    
    def test_entire_knowledge_base_validation(self):
        """测试整个知识库验证"""
        # 创建模拟向量存储
        mock_vector_store = Mock()
        mock_vector_store.collection.get.return_value = {
            "ids": ["valid_1", "invalid_1", "valid_2"],
            "documents": ["doc1", "doc2", "doc3"],
            "metadatas": [
                {  # 有效条目
                    "question": "有效问题1",
                    "sql": "SELECT * FROM users",
                    "rating": 4.0,
                    "usage_count": 5
                },
                {  # 无效条目
                    "question": "",  # 空问题
                    "sql": "invalid sql",
                    "rating": 10.0,  # 超出范围
                    "usage_count": -1  # 负数
                },
                {  # 有效条目
                    "question": "有效问题2",
                    "sql": "SELECT COUNT(*) FROM orders",
                    "rating": 3.5,
                    "usage_count": 2
                }
            ]
        }
        
        # 执行验证
        result = self.guard.validate_entire_knowledge_base(mock_vector_store)
        
        # 验证结果
        self.assertFalse(result.is_valid)  # 有无效条目
        self.assertEqual(len(result.corrupted_items), 1)  # 一个损坏条目
        self.assertIn("invalid_1", result.corrupted_items)
        self.assertGreater(len(result.errors), 0)  # 有错误信息
    
    def test_backup_list_management(self):
        """测试备份列表管理"""
        # 创建多个备份
        mock_vector_store = Mock()
        mock_vector_store.collection_name = "test_collection"
        mock_vector_store.collection.get.return_value = {
            "ids": ["test_1"],
            "documents": ["doc1"],
            "metadatas": [{"question": "问题1", "sql": "SELECT 1"}],
            "embeddings": [[0.1, 0.2]]
        }
        
        backup_ids = []
        for i in range(3):
            backup_id = self.guard.backup_knowledge_base(
                vector_store=mock_vector_store,
                description=f"备份{i+1}"
            )
            backup_ids.append(backup_id)
        
        # 获取备份列表
        backup_list = self.guard.get_backup_list()
        
        self.assertEqual(len(backup_list), 3)
        
        # 验证备份按时间倒序排列
        timestamps = [backup["timestamp"] for backup in backup_list]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        
        # 验证备份信息完整
        for backup in backup_list:
            self.assertIn("backup_id", backup)
            self.assertIn("timestamp", backup)
            self.assertIn("description", backup)
            self.assertIn("size", backup)
            self.assertIn("checksum", backup)
    
    def test_global_guard_instance(self):
        """测试全局保护器实例"""
        guard1 = get_consistency_guard()
        guard2 = get_consistency_guard()
        
        # 验证返回同一个实例
        self.assertIs(guard1, guard2)
        self.assertIsInstance(guard1, DataConsistencyGuard)


class TestIntegratedErrorHandling(unittest.TestCase):
    """集成错误处理测试"""
    
    def setUp(self):
        """测试初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.fallback_handler = RAGFallbackHandler()
        self.consistency_guard = DataConsistencyGuard(backup_directory=self.temp_dir)
    
    def tearDown(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_integrated_failure_recovery(self):
        """测试集成故障恢复流程"""
        # 模拟ChromaDB连接失败
        chromadb_error = Exception("ChromaDB connection lost")
        
        # 处理故障
        result = self.fallback_handler.handle_rag_failure(
            error=chromadb_error,
            question="测试问题",
            schema_info="测试架构",
            context={"user_id": "test_user"}
        )
        
        # 验证降级处理结果
        self.assertTrue(result["fallback_used"])
        self.assertIn("strategy", result)
        
        # 验证故障被记录
        stats = self.fallback_handler.get_failure_statistics()
        self.assertGreater(stats["total_failures"], 0)
        self.assertIn("chromadb_connection", stats["failure_by_type"])
    
    def test_data_corruption_with_backup_recovery(self):
        """测试数据损坏与备份恢复的集成流程"""
        # 创建模拟向量存储
        mock_vector_store = Mock()
        mock_vector_store.collection_name = "test_collection"
        
        # 模拟正常数据用于备份
        mock_vector_store.collection.get.return_value = {
            "ids": ["item_1", "item_2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [
                {"question": "问题1", "sql": "SELECT 1"},
                {"question": "问题2", "sql": "SELECT 2"}
            ],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]]
        }
        
        # 创建备份
        backup_id = self.consistency_guard.backup_knowledge_base(
            vector_store=mock_vector_store,
            description="故障前备份"
        )
        self.assertIsNotNone(backup_id)
        
        # 模拟数据损坏错误
        corruption_error = Exception("Data corruption detected in vector store")
        
        # 处理数据损坏故障
        result = self.fallback_handler.handle_rag_failure(
            error=corruption_error,
            question="测试问题",
            schema_info="测试架构"
        )
        
        # 验证降级处理
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["failure_type"], FailureType.DATA_CORRUPTION.value)
        
        # 处理损坏的数据条目
        success = self.consistency_guard.handle_corrupted_data("corrupted_item", mock_vector_store)
        self.assertTrue(success)
        
        # 从备份恢复
        mock_vector_store.client = Mock()
        mock_vector_store.client.delete_collection = Mock()
        mock_vector_store.client.create_collection = Mock()
        mock_vector_store.client.create_collection.return_value = Mock()
        mock_vector_store.collection = Mock()
        
        restore_success = self.consistency_guard.restore_knowledge_base(backup_id, mock_vector_store)
        self.assertTrue(restore_success)


if __name__ == '__main__':
    unittest.main()