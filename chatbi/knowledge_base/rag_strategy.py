"""
RAG策略选择器
根据相似度分数自动选择最优的SQL生成策略
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class RAGStrategyType(Enum):
    """RAG策略类型"""
    HIGH_SIMILARITY_CACHED = "high_similarity_cached"
    MEDIUM_SIMILARITY_ASSISTED = "medium_similarity_assisted"
    LOW_SIMILARITY_NORMAL = "low_similarity_normal"

@dataclass
class RAGResult:
    """RAG检索结果"""
    found_match: bool
    best_match: Optional[Dict[str, Any]] = None
    similar_examples: Optional[List[Dict[str, Any]]] = None
    confidence: float = 0.0
    should_use_cached: bool = False
    strategy: str = "normal"
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class StrategyConfig:
    """策略配置"""
    high_similarity_threshold: float = 0.8
    medium_similarity_threshold: float = 0.6
    confidence_threshold: float = 0.8
    min_rating_for_cache: float = 0.0
    max_examples: int = 3

class RAGStrategy:
    """RAG策略选择器"""
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        初始化策略选择器
        
        Args:
            config: 策略配置，如果为None则使用默认配置
        """
        self.config = config or StrategyConfig()
        logger.info(f"RAG策略选择器初始化完成，配置: {self.config}")
    
    def determine_strategy(self, rag_result: RAGResult) -> str:
        """
        确定RAG策略
        
        Args:
            rag_result: RAG检索结果
            
        Returns:
            str: 策略类型
                - "high_similarity_cached": 直接使用缓存SQL
                - "medium_similarity_assisted": 示例辅助生成
                - "low_similarity_normal": 常规生成流程
        """
        if not rag_result.found_match or not rag_result.best_match:
            logger.info("未找到匹配项，使用常规生成策略")
            return RAGStrategyType.LOW_SIMILARITY_NORMAL.value
        
        confidence = rag_result.confidence
        best_match = rag_result.best_match
        rating = best_match.get("rating", 0.0)
        
        # 高相似度策略：直接使用缓存SQL
        if (confidence >= self.config.high_similarity_threshold and 
            confidence >= self.config.confidence_threshold and
            rating >= self.config.min_rating_for_cache):
            
            logger.info(f"🎯 高相似度策略 (相似度: {confidence:.3f} >= {self.config.high_similarity_threshold}, "
                       f"置信度: {confidence:.3f} >= {self.config.confidence_threshold}, "
                       f"评分: {rating:.1f} >= {self.config.min_rating_for_cache})")
            return RAGStrategyType.HIGH_SIMILARITY_CACHED.value
        
        # 中相似度策略：使用相似示例辅助生成
        elif confidence >= self.config.medium_similarity_threshold:
            logger.info(f"🔍 中相似度策略 (相似度: {confidence:.3f} >= {self.config.medium_similarity_threshold})")
            return RAGStrategyType.MEDIUM_SIMILARITY_ASSISTED.value
        
        # 低相似度策略：常规生成流程
        else:
            logger.info(f"📝 低相似度策略 (相似度: {confidence:.3f} < {self.config.medium_similarity_threshold})")
            return RAGStrategyType.LOW_SIMILARITY_NORMAL.value
    
    def should_use_cached_sql(self, rag_result: RAGResult) -> bool:
        """
        判断是否应该使用缓存的SQL
        
        Args:
            rag_result: RAG检索结果
            
        Returns:
            bool: 是否使用缓存SQL
        """
        strategy = self.determine_strategy(rag_result)
        return strategy == RAGStrategyType.HIGH_SIMILARITY_CACHED.value
    
    def get_examples_for_generation(self, rag_result: RAGResult) -> List[Dict[str, Any]]:
        """
        获取用于SQL生成的示例
        
        Args:
            rag_result: RAG检索结果
            
        Returns:
            List[Dict]: 示例列表
        """
        if not rag_result.found_match or not rag_result.similar_examples:
            return []
        
        strategy = self.determine_strategy(rag_result)
        
        # 高相似度策略不需要示例（直接使用缓存）
        if strategy == RAGStrategyType.HIGH_SIMILARITY_CACHED.value:
            return []
        
        # 中低相似度策略返回示例
        examples = rag_result.similar_examples[:self.config.max_examples]
        
        # 过滤和格式化示例
        formatted_examples = []
        for example in examples:
            if example.get("rating", 0) >= 0:  # 只包含非负评分的示例
                formatted_examples.append({
                    "question": example.get("question", ""),
                    "sql": example.get("sql", ""),
                    "similarity": example.get("similarity", 0.0),
                    "description": example.get("description", "")
                })
        
        logger.info(f"为{strategy}策略提供 {len(formatted_examples)} 个示例")
        return formatted_examples
    
    def get_strategy_config(self) -> Dict[str, float]:
        """
        获取策略配置
        
        Returns:
            Dict[str, float]: 配置参数
        """
        return {
            "high_similarity_threshold": self.config.high_similarity_threshold,
            "medium_similarity_threshold": self.config.medium_similarity_threshold,
            "confidence_threshold": self.config.confidence_threshold,
            "min_rating_for_cache": self.config.min_rating_for_cache,
            "max_examples": self.config.max_examples
        }
    
    def update_thresholds(self, 
                         similarity_threshold: Optional[float] = None,
                         confidence_threshold: Optional[float] = None,
                         min_rating: Optional[float] = None):
        """
        更新阈值配置
        
        Args:
            similarity_threshold: 相似度阈值
            confidence_threshold: 置信度阈值
            min_rating: 最小评分要求
        """
        if similarity_threshold is not None:
            self.config.medium_similarity_threshold = similarity_threshold
            logger.info(f"更新相似度阈值: {similarity_threshold}")
        
        if confidence_threshold is not None:
            self.config.confidence_threshold = confidence_threshold
            logger.info(f"更新置信度阈值: {confidence_threshold}")
        
        if min_rating is not None:
            self.config.min_rating_for_cache = min_rating
            logger.info(f"更新最小评分要求: {min_rating}")
    
    def evaluate_strategy_effectiveness(self, 
                                      strategy: str, 
                                      user_feedback: bool,
                                      execution_time: float) -> Dict[str, Any]:
        """
        评估策略效果
        
        Args:
            strategy: 使用的策略
            user_feedback: 用户反馈（True为正面）
            execution_time: 执行时间
            
        Returns:
            Dict[str, Any]: 评估结果
        """
        evaluation = {
            "strategy": strategy,
            "user_feedback": user_feedback,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }
        
        # 根据策略类型评估效果
        if strategy == RAGStrategyType.HIGH_SIMILARITY_CACHED.value:
            evaluation["expected_fast"] = execution_time < 1.0
            evaluation["cache_hit"] = True
        elif strategy == RAGStrategyType.MEDIUM_SIMILARITY_ASSISTED.value:
            evaluation["expected_improved"] = user_feedback
            evaluation["assisted_generation"] = True
        else:
            evaluation["baseline_performance"] = True
        
        logger.info(f"策略效果评估: {evaluation}")
        return evaluation

# 全局策略选择器实例
_rag_strategy: Optional[RAGStrategy] = None

def get_rag_strategy() -> RAGStrategy:
    """获取全局RAG策略选择器实例"""
    global _rag_strategy
    
    if _rag_strategy is None:
        _rag_strategy = RAGStrategy()
    
    return _rag_strategy