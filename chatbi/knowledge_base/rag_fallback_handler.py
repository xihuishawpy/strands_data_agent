"""
RAG降级和错误处理器
处理ChromaDB连接失败、Embedding服务异常等情况
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)

class FallbackLevel(Enum):
    """降级级别"""
    NONE = "none"                    # 无降级
    CACHE_ONLY = "cache_only"        # 仅使用缓存
    SIMPLE_MATCH = "simple_match"    # 简单文本匹配
    DISABLED = "disabled"            # 完全禁用

class ErrorType(Enum):
    """错误类型"""
    CONNECTION_ERROR = "connection_error"      # 连接错误
    EMBEDDING_ERROR = "embedding_error"        # 嵌入服务错误
    VECTOR_STORE_ERROR = "vector_store_error"  # 向量存储错误
    TIMEOUT_ERROR = "timeout_error"            # 超时错误
    MEMORY_ERROR = "memory_error"              # 内存错误
    UNKNOWN_ERROR = "unknown_error"            # 未知错误

@dataclass
class ErrorRecord:
    """错误记录"""
    error_type: ErrorType
    error_message: str
    timestamp: datetime
    operation: str
    retry_count: int = 0
    resolved: bool = False

@dataclass
class FallbackConfig:
    """降级配置"""
    max_retries: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300  # 5分钟
    enable_simple_cache: bool = True
    cache_size: int = 1000
    health_check_interval: int = 60  # 1分钟

@dataclass
class HealthStatus:
    """健康状态"""
    is_healthy: bool
    last_check: datetime
    error_count: int
    consecutive_failures: int
    fallback_level: FallbackLevel

class RAGFallbackHandler:
    """RAG降级和错误处理器"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        """
        初始化降级处理器
        
        Args:
            config: 降级配置
        """
        self.config = config or FallbackConfig()
        self.error_history: List[ErrorRecord] = []
        self.health_status = HealthStatus(
            is_healthy=True,
            last_check=datetime.now(),
            error_count=0,
            consecutive_failures=0,
            fallback_level=FallbackLevel.NONE
        )
        
        # 简单缓存（当向量数据库不可用时使用）
        self._simple_cache: Dict[str, Any] = {}
        self._cache_access_times: Dict[str, datetime] = {}
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 熔断器状态
        self._circuit_breaker_open = False
        self._circuit_breaker_open_time: Optional[datetime] = None
        
        logger.info("RAG降级处理器初始化完成")
    
    def handle_operation(self, operation: str, operation_func: Callable, 
                        fallback_func: Optional[Callable] = None):
        """
        处理操作，包含重试和降级逻辑
        
        Args:
            operation: 操作名称
            operation_func: 操作函数
            fallback_func: 降级函数
            
        Returns:
            操作结果
        """
        retry_count = 0
        
        while retry_count <= self.config.max_retries:
            try:
                # 检查熔断器状态
                if self._is_circuit_breaker_open():
                    logger.warning(f"熔断器开启，跳过操作: {operation}")
                    if fallback_func:
                        return fallback_func()
                    else:
                        raise Exception("服务暂时不可用，熔断器已开启")
                
                # 执行操作
                result = operation_func()
                
                # 操作成功，重置连续失败计数
                self._on_success(operation)
                return result
                
            except Exception as e:
                retry_count += 1
                error_type = self._classify_error(e)
                
                # 记录错误
                self._record_error(error_type, str(e), operation, retry_count)
                
                # 判断是否需要重试
                if retry_count <= self.config.max_retries and self._should_retry(error_type):
                    logger.warning(f"操作失败，准备重试 ({retry_count}/{self.config.max_retries}): {operation}")
                    time.sleep(self.config.retry_delay * retry_count)  # 指数退避
                    continue
                else:
                    # 重试次数用完或不应重试，执行降级
                    logger.error(f"操作最终失败，执行降级: {operation}")
                    self._on_failure(operation, error_type)
                    
                    if fallback_func:
                        try:
                            return fallback_func()
                        except Exception as fallback_error:
                            logger.error(f"降级操作也失败: {str(fallback_error)}")
                    
                    raise e
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        error_str = str(error).lower()
        
        if "connection" in error_str or "connect" in error_str:
            return ErrorType.CONNECTION_ERROR
        elif "embedding" in error_str or "embed" in error_str:
            return ErrorType.EMBEDDING_ERROR
        elif "vector" in error_str or "chroma" in error_str:
            return ErrorType.VECTOR_STORE_ERROR
        elif "timeout" in error_str:
            return ErrorType.TIMEOUT_ERROR
        elif "memory" in error_str:
            return ErrorType.MEMORY_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _should_retry(self, error_type: ErrorType) -> bool:
        """判断是否应该重试"""
        # 某些错误类型不应重试
        no_retry_errors = {ErrorType.MEMORY_ERROR}
        return error_type not in no_retry_errors
    
    def _record_error(self, error_type: ErrorType, error_message: str, 
                     operation: str, retry_count: int):
        """记录错误"""
        with self._lock:
            error_record = ErrorRecord(
                error_type=error_type,
                error_message=error_message,
                timestamp=datetime.now(),
                operation=operation,
                retry_count=retry_count
            )
            
            self.error_history.append(error_record)
            
            # 限制错误历史记录数量
            if len(self.error_history) > 1000:
                self.error_history = self.error_history[-500:]
            
            # 更新健康状态
            self.health_status.error_count += 1
            self.health_status.consecutive_failures += 1
            
            # 检查是否需要开启熔断器
            if self.health_status.consecutive_failures >= self.config.circuit_breaker_threshold:
                self._open_circuit_breaker()
    
    def _on_success(self, operation: str):
        """操作成功时的处理"""
        with self._lock:
            self.health_status.consecutive_failures = 0
            self.health_status.is_healthy = True
            self.health_status.last_check = datetime.now()
            
            # 关闭熔断器
            if self._circuit_breaker_open:
                self._close_circuit_breaker()
    
    def _on_failure(self, operation: str, error_type: ErrorType):
        """操作失败时的处理"""
        with self._lock:
            self.health_status.is_healthy = False
            self.health_status.last_check = datetime.now()
            
            # 根据错误类型和失败次数确定降级级别
            if self.health_status.consecutive_failures >= 10:
                self.health_status.fallback_level = FallbackLevel.DISABLED
            elif self.health_status.consecutive_failures >= 5:
                self.health_status.fallback_level = FallbackLevel.SIMPLE_MATCH
            elif self.health_status.consecutive_failures >= 3:
                self.health_status.fallback_level = FallbackLevel.CACHE_ONLY
            else:
                self.health_status.fallback_level = FallbackLevel.NONE
    
    def _open_circuit_breaker(self):
        """开启熔断器"""
        self._circuit_breaker_open = True
        self._circuit_breaker_open_time = datetime.now()
        logger.warning("熔断器已开启")
    
    def _close_circuit_breaker(self):
        """关闭熔断器"""
        self._circuit_breaker_open = False
        self._circuit_breaker_open_time = None
        logger.info("熔断器已关闭")
    
    def _is_circuit_breaker_open(self) -> bool:
        """检查熔断器是否开启"""
        if not self._circuit_breaker_open:
            return False
        
        # 检查是否超过超时时间
        if (self._circuit_breaker_open_time and 
            datetime.now() - self._circuit_breaker_open_time > 
            timedelta(seconds=self.config.circuit_breaker_timeout)):
            
            logger.info("熔断器超时，尝试半开状态")
            return False
        
        return True
    
    def get_fallback_search_results(self, question: str, **kwargs) -> List[Dict[str, Any]]:
        """
        降级搜索结果
        
        Args:
            question: 查询问题
            **kwargs: 其他参数
            
        Returns:
            List[Dict]: 降级搜索结果
        """
        fallback_level = self.health_status.fallback_level
        
        if fallback_level == FallbackLevel.DISABLED:
            logger.warning("RAG功能已完全禁用")
            return []
        
        elif fallback_level == FallbackLevel.CACHE_ONLY:
            return self._search_from_cache(question)
        
        elif fallback_level == FallbackLevel.SIMPLE_MATCH:
            return self._simple_text_match(question)
        
        else:
            return []
    
    def _search_from_cache(self, question: str) -> List[Dict[str, Any]]:
        """从缓存中搜索"""
        results = []
        question_lower = question.lower()
        
        with self._lock:
            for cache_key, cache_data in self._simple_cache.items():
                if isinstance(cache_data, dict) and "question" in cache_data:
                    cached_question = cache_data["question"].lower()
                    
                    # 简单的文本相似度匹配
                    similarity = self._calculate_simple_similarity(question_lower, cached_question)
                    
                    if similarity > 0.3:  # 降低相似度阈值
                        result = cache_data.copy()
                        result["similarity"] = similarity
                        result["source"] = "cache"
                        results.append(result)
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:5]  # 返回前5个结果
    
    def _simple_text_match(self, question: str) -> List[Dict[str, Any]]:
        """简单文本匹配"""
        # 这里可以实现基于关键词的简单匹配逻辑
        # 作为演示，返回空结果
        logger.info(f"执行简单文本匹配: {question}")
        return []
    
    def _calculate_simple_similarity(self, text1: str, text2: str) -> float:
        """计算简单文本相似度"""
        # 简单的Jaccard相似度
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        jaccard_sim = intersection / union if union > 0 else 0.0
        
        # 也检查子字符串匹配
        substring_sim = 0.0
        if text1 in text2 or text2 in text1:
            substring_sim = 0.5
        
        # 返回较高的相似度
        return max(jaccard_sim, substring_sim)
    
    def add_to_cache(self, key: str, data: Any):
        """添加数据到简单缓存"""
        with self._lock:
            # 检查缓存大小
            if len(self._simple_cache) >= self.config.cache_size:
                # 删除最旧的条目
                oldest_key = min(self._cache_access_times.keys(), 
                               key=lambda k: self._cache_access_times[k])
                del self._simple_cache[oldest_key]
                del self._cache_access_times[oldest_key]
            
            self._simple_cache[key] = data
            self._cache_access_times[key] = datetime.now()
    
    def get_from_cache(self, key: str) -> Optional[Any]:
        """从简单缓存获取数据"""
        with self._lock:
            if key in self._simple_cache:
                self._cache_access_times[key] = datetime.now()
                return self._simple_cache[key]
            return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        with self._lock:
            return {
                "is_healthy": self.health_status.is_healthy,
                "last_check": self.health_status.last_check.isoformat(),
                "error_count": self.health_status.error_count,
                "consecutive_failures": self.health_status.consecutive_failures,
                "fallback_level": self.health_status.fallback_level.value,
                "circuit_breaker_open": self._circuit_breaker_open,
                "cache_size": len(self._simple_cache)
            }
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_errors = [
                error for error in self.error_history 
                if error.timestamp > cutoff_time
            ]
            
            # 按错误类型统计
            error_counts = {}
            for error in recent_errors:
                error_type = error.error_type.value
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            return {
                "total_errors": len(recent_errors),
                "error_by_type": error_counts,
                "time_range_hours": hours,
                "most_recent_error": (
                    recent_errors[-1].error_message if recent_errors else None
                )
            }
    
    def reset_health_status(self):
        """重置健康状态（用于手动恢复）"""
        with self._lock:
            self.health_status = HealthStatus(
                is_healthy=True,
                last_check=datetime.now(),
                error_count=0,
                consecutive_failures=0,
                fallback_level=FallbackLevel.NONE
            )
            self._close_circuit_breaker()
            logger.info("健康状态已重置")
    
    def clear_error_history(self):
        """清空错误历史"""
        with self._lock:
            self.error_history.clear()
            logger.info("错误历史已清空")

# 全局降级处理器实例
_fallback_handler: Optional[RAGFallbackHandler] = None

def get_fallback_handler() -> RAGFallbackHandler:
    """获取全局降级处理器实例"""
    global _fallback_handler
    
    if _fallback_handler is None:
        _fallback_handler = RAGFallbackHandler()
    
    return _fallback_handler