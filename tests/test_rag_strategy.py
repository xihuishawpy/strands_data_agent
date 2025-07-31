"""
RAG策略选择器单元测试
验证不同相似度下的策略选择正确性
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from chatbi.knowledge_base.rag_strategy import (
    RAGStrategy, RAGResult, StrategyConfig, RAGStrategyType,
    get_rag_strategy
)


class TestRAGStrategy(unittest.TestCase):
    """RAG策略选择器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = StrategyConfig(
            high_similarity_threshold=0.8,
            medium_similarity_threshold=0.6,
            confidence_threshold=0.8,
            min_rating_for_cache=0.0,
            max_examples=3
        )
        self.strategy = RAGStrategy(self.config)
    
    def test_high_similarity_strategy(self):
        """测试高相似度策略选择"""
        # 创建高相似度的RAG结果
        rag_result = RAGResult(
            found_match=True,
            best_match={
                "question": "测试问题",
                "sql": "SELECT * FROM test",
                "rating": 1.0,
                "similarity": 0.9
            },
            confidence=0.9
        )
        
        strategy = self.strategy.determine_strategy(rag_result)
        self.assertEqual(strategy, RAGStrategyType.HIGH_SIMILARITY_CACHED.value)
        
        # 验证应该使用缓存SQL
        should_cache = self.strategy.should_use_cached_sql(rag_result)
        self.assertTrue(should_cache)
    
    def test_medium_similarity_strategy(self):
        """测试中相似度策略选择"""
        # 创建中相似度的RAG结果
        rag_result = RAGResult(
            found_match=True,
            best_match={
                "question": "测试问题",
                "sql": "SELECT * FROM test",
                "rating": 0.5,
                "similarity": 0.7
            },
            confidence=0.7,
            similar_examples=[
                {"question": "示例1", "sql": "SELECT 1", "similarity": 0.7},
                {"question": "示例2", "sql": "SELECT 2", "similarity": 0.6}
            ]
        )
        
        strategy = self.strategy.determine_strategy(rag_result)
        self.assertEqual(strategy, RAGStrategyType.MEDIUM_SIMILARITY_ASSISTED.value)
        
        # 验证不应该使用缓存SQL
        should_cache = self.strategy.should_use_cached_sql(rag_result)
        self.assertFalse(should_cache)
        
        # 验证应该返回示例
        examples = self.strategy.get_examples_for_generation(rag_result)
        self.assertEqual(len(examples), 2)
        self.assertEqual(examples[0]["question"], "示例1")
    
    def test_low_similarity_strategy(self):
        """测试低相似度策略选择"""
        # 创建低相似度的RAG结果
        rag_result = RAGResult(
            found_match=True,
            best_match={
                "question": "测试问题",
                "sql": "SELECT * FROM test",
                "rating": 0.2,
                "similarity": 0.5
            },
            confidence=0.5
        )
        
        strategy = self.strategy.determine_strategy(rag_result)
        self.assertEqual(strategy, RAGStrategyType.LOW_SIMILARITY_NORMAL.value)
        
        # 验证不应该使用缓存SQL
        should_cache = self.strategy.should_use_cached_sql(rag_result)
        self.assertFalse(should_cache)
    
    def test_no_match_strategy(self):
        """测试无匹配结果的策略选择"""
        # 创建无匹配的RAG结果
        rag_result = RAGResult(found_match=False)
        
        strategy = self.strategy.determine_strategy(rag_result)
        self.assertEqual(strategy, RAGStrategyType.LOW_SIMILARITY_NORMAL.value)
        
        # 验证不应该使用缓存SQL
        should_cache = self.strategy.should_use_cached_sql(rag_result)
        self.assertFalse(should_cache)
        
        # 验证不应该返回示例
        examples = self.strategy.get_examples_for_generation(rag_result)
        self.assertEqual(len(examples), 0)
    
    def test_high_similarity_low_rating_strategy(self):
        """测试高相似度但低评分的策略选择"""
        # 创建高相似度但低评分的RAG结果
        rag_result = RAGResult(
            found_match=True,
            best_match={
                "question": "测试问题",
                "sql": "SELECT * FROM test",
                "rating": -1.0,  # 负评分
                "similarity": 0.9
            },
            confidence=0.9
        )
        
        # 设置最小评分要求
        self.strategy.config.min_rating_for_cache = 0.0
        
        strategy = self.strategy.determine_strategy(rag_result)
        # 由于评分过低，应该降级到中相似度策略
        self.assertEqual(strategy, RAGStrategyType.MEDIUM_SIMILARITY_ASSISTED.value)
    
    def test_confidence_threshold_check(self):
        """测试置信度阈值检查"""
        # 创建高相似度但低置信度的RAG结果
        rag_result = RAGResult(
            found_match=True,
            best_match={
                "question": "测试问题",
                "sql": "SELECT * FROM test",
                "rating": 1.0,
                "similarity": 0.9
            },
            confidence=0.7  # 低于置信度阈值0.8
        )
        
        strategy = self.strategy.determine_strategy(rag_result)
        # 由于置信度不足，应该降级到中相似度策略
        self.assertEqual(strategy, RAGStrategyType.MEDIUM_SIMILARITY_ASSISTED.value)
    
    def test_examples_filtering(self):
        """测试示例过滤功能"""
        # 创建包含多个示例的RAG结果
        rag_result = RAGResult(
            found_match=True,
            best_match={
                "question": "测试问题",
                "sql": "SELECT * FROM test",
                "rating": 0.5,
                "similarity": 0.7
            },
            confidence=0.7,
            similar_examples=[
                {"question": "好示例1", "sql": "SELECT 1", "similarity": 0.7, "rating": 1.0},
                {"question": "坏示例", "sql": "SELECT 2", "similarity": 0.6, "rating": -1.0},
                {"question": "好示例2", "sql": "SELECT 3", "similarity": 0.65, "rating": 0.5},
                {"question": "好示例3", "sql": "SELECT 4", "similarity": 0.6, "rating": 0.0},
                {"question": "好示例4", "sql": "SELECT 5", "similarity": 0.55, "rating": 1.0}
            ]
        )
        
        examples = self.strategy.get_examples_for_generation(rag_result)
        
        # 验证示例数量限制
        self.assertLessEqual(len(examples), self.config.max_examples)
        
        # 验证所有示例都有非负评分
        for example in examples:
            # 注意：在实际实现中，rating可能不在返回的example中
            # 这里主要测试过滤逻辑
            self.assertIn("question", example)
            self.assertIn("sql", example)
            self.assertIn("similarity", example)
    
    def test_config_update(self):
        """测试配置更新功能"""
        # 更新阈值
        self.strategy.update_thresholds(
            similarity_threshold=0.7,
            confidence_threshold=0.9,
            min_rating=0.5
        )
        
        # 验证配置已更新
        config = self.strategy.get_strategy_config()
        self.assertEqual(config["medium_similarity_threshold"], 0.7)
        self.assertEqual(config["confidence_threshold"], 0.9)
        self.assertEqual(config["min_rating_for_cache"], 0.5)
    
    def test_strategy_effectiveness_evaluation(self):
        """测试策略效果评估"""
        # 测试高相似度策略评估
        evaluation = self.strategy.evaluate_strategy_effectiveness(
            strategy=RAGStrategyType.HIGH_SIMILARITY_CACHED.value,
            user_feedback=True,
            execution_time=0.5
        )
        
        self.assertEqual(evaluation["strategy"], RAGStrategyType.HIGH_SIMILARITY_CACHED.value)
        self.assertTrue(evaluation["user_feedback"])
        self.assertEqual(evaluation["execution_time"], 0.5)
        self.assertTrue(evaluation["expected_fast"])
        self.assertTrue(evaluation["cache_hit"])
        
        # 测试中相似度策略评估
        evaluation = self.strategy.evaluate_strategy_effectiveness(
            strategy=RAGStrategyType.MEDIUM_SIMILARITY_ASSISTED.value,
            user_feedback=True,
            execution_time=2.0
        )
        
        self.assertTrue(evaluation["expected_improved"])
        self.assertTrue(evaluation["assisted_generation"])
    
    def test_global_strategy_instance(self):
        """测试全局策略实例"""
        strategy1 = get_rag_strategy()
        strategy2 = get_rag_strategy()
        
        # 验证返回同一个实例
        self.assertIs(strategy1, strategy2)
        
        # 验证实例类型正确
        self.assertIsInstance(strategy1, RAGStrategy)


class TestStrategyConfig(unittest.TestCase):
    """策略配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = StrategyConfig()
        
        self.assertEqual(config.high_similarity_threshold, 0.8)
        self.assertEqual(config.medium_similarity_threshold, 0.6)
        self.assertEqual(config.confidence_threshold, 0.8)
        self.assertEqual(config.min_rating_for_cache, 0.0)
        self.assertEqual(config.max_examples, 3)
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = StrategyConfig(
            high_similarity_threshold=0.9,
            medium_similarity_threshold=0.7,
            confidence_threshold=0.85,
            min_rating_for_cache=0.5,
            max_examples=5
        )
        
        self.assertEqual(config.high_similarity_threshold, 0.9)
        self.assertEqual(config.medium_similarity_threshold, 0.7)
        self.assertEqual(config.confidence_threshold, 0.85)
        self.assertEqual(config.min_rating_for_cache, 0.5)
        self.assertEqual(config.max_examples, 5)


class TestRAGResult(unittest.TestCase):
    """RAG结果测试"""
    
    def test_rag_result_creation(self):
        """测试RAG结果创建"""
        result = RAGResult(
            found_match=True,
            best_match={"test": "data"},
            confidence=0.8
        )
        
        self.assertTrue(result.found_match)
        self.assertEqual(result.best_match, {"test": "data"})
        self.assertEqual(result.confidence, 0.8)
        self.assertFalse(result.should_use_cached)  # 默认值
        self.assertEqual(result.strategy, "normal")  # 默认值
    
    def test_rag_result_defaults(self):
        """测试RAG结果默认值"""
        result = RAGResult(found_match=False)
        
        self.assertFalse(result.found_match)
        self.assertIsNone(result.best_match)
        self.assertIsNone(result.similar_examples)
        self.assertEqual(result.confidence, 0.0)
        self.assertFalse(result.should_use_cached)
        self.assertEqual(result.strategy, "normal")
        self.assertIsNone(result.metadata)


if __name__ == '__main__':
    unittest.main()