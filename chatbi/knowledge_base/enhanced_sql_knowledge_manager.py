"""
增强版SQL知识库管理器
包含性能优化、批量操作、数据验证和版本管理功能
"""

import logging
import json
import time
import hashlib
import re
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from contextlib import contextmanager

from .vector_store import SQLVectorStore, get_vector_store, CHROMADB_AVAILABLE
from .rag_strategy import RAGStrategy, RAGResult, get_rag_strategy
from ..config import config

logger = logging.getLogger(__name__)

# 性能监控装饰器
def performance_monitor(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} 执行时间: {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败 (耗时: {execution_time:.3f}s): {str(e)}")
            raise
    return wrapper

@dataclass
class ValidationResult:
    """数据验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)

@dataclass
class BatchOperationResult:
    """批量操作结果"""
    total_items: int
    successful_items: int
    failed_items: int
    errors: List[Dict[str, Any]]
    execution_time: float
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.successful_items / self.total_items if self.total_items > 0 else 0.0

@dataclass
class KnowledgeVersion:
    """知识库版本信息"""
    version_id: str
    item_id: str
    question: str
    sql: str
    description: str
    tags: List[str]
    rating: float
    created_at: datetime
    created_by: str
    change_reason: str

class EnhancedSQLKnowledgeManager:
    """增强版SQL知识库管理器"""
    
    def __init__(self):
        """初始化知识库管理器"""
        self.vector_store = None
        self.enabled = CHROMADB_AVAILABLE
        self.rag_strategy = None
        self._cache = {}  # 简单缓存
        self._cache_ttl = 300  # 缓存5分钟
        self._performance_stats = {
            "search_count": 0,
            "cache_hits": 0,
            "avg_search_time": 0.0,
            "total_search_time": 0.0
        }
        
        if self.enabled:
            try:
                self.vector_store = get_vector_store()
                self.rag_strategy = get_rag_strategy()
                logger.info("增强版SQL知识库管理器初始化成功")
            except Exception as e:
                logger.error(f"SQL知识库初始化失败: {str(e)}")
                self.enabled = False
                self._handle_initialization_error(e)
        else:
            logger.warning("SQL知识库功能已禁用（ChromaDB未安装）")
    
    def _handle_initialization_error(self, error: Exception):
        """处理初始化错误"""
        error_type = type(error).__name__
        if "Connection" in str(error):
            logger.error("数据库连接失败，请检查ChromaDB服务状态")
        elif "Permission" in str(error):
            logger.error("权限不足，请检查数据目录访问权限")
        else:
            logger.error(f"未知初始化错误: {error_type} - {str(error)}")
    
    @contextmanager
    def _error_handling(self, operation_name: str):
        """统一错误处理上下文管理器"""
        try:
            yield
        except Exception as e:
            logger.error(f"{operation_name} 操作失败: {str(e)}")
            # 根据错误类型进行不同处理
            if "timeout" in str(e).lower():
                logger.warning("操作超时，建议检查网络连接或数据库性能")
            elif "memory" in str(e).lower():
                logger.warning("内存不足，建议优化查询或增加系统内存")
            raise
    
    def _validate_input_data(self, question: str, sql: str, description: str = None) -> ValidationResult:
        """验证输入数据"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 验证问题
        if not question or not question.strip():
            result.add_error("问题不能为空")
        elif len(question.strip()) < 3:
            result.add_error("问题长度至少3个字符")
        elif len(question) > 1000:
            result.add_warning("问题过长，可能影响搜索效果")
        
        # 验证SQL
        if not sql or not sql.strip():
            result.add_error("SQL不能为空")
        else:
            sql_validation = self._validate_sql_syntax(sql)
            if not sql_validation["is_valid"]:
                result.add_error(f"SQL语法错误: {sql_validation['error']}")
            
            # 检查危险SQL操作
            dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER"]
            sql_upper = sql.upper()
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    result.add_warning(f"检测到潜在危险操作: {keyword}")
        
        # 验证描述
        if description and len(description) > 2000:
            result.add_warning("描述过长，建议简化")
        
        return result
    
    def _validate_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """基础SQL语法验证"""
        try:
            sql = sql.strip()
            if not sql:
                return {"is_valid": False, "error": "SQL为空"}
            
            # 基本语法检查
            if not sql.upper().startswith(("SELECT", "WITH", "(")):
                return {"is_valid": False, "error": "只支持SELECT查询"}
            
            # 括号匹配检查
            if sql.count("(") != sql.count(")"):
                return {"is_valid": False, "error": "括号不匹配"}
            
            # 引号匹配检查
            single_quotes = sql.count("'") - sql.count("\\'")
            double_quotes = sql.count('"') - sql.count('\\"')
            if single_quotes % 2 != 0:
                return {"is_valid": False, "error": "单引号不匹配"}
            if double_quotes % 2 != 0:
                return {"is_valid": False, "error": "双引号不匹配"}
            
            return {"is_valid": True, "error": None}
            
        except Exception as e:
            return {"is_valid": False, "error": f"验证异常: {str(e)}"}
    
    def _get_cache_key(self, question: str, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{question}_{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self._performance_stats["cache_hits"] += 1
                return cached_data
            else:
                # 缓存过期，删除
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any):
        """设置缓存"""
        self._cache[cache_key] = (data, time.time())
        
        # 简单的缓存清理：如果缓存过多，清理最旧的
        if len(self._cache) > 100:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
    
    @performance_monitor
    def search_knowledge_enhanced(self, 
                                question: str,
                                similarity_threshold: float = None,
                                confidence_threshold: float = None,
                                use_cache: bool = True) -> RAGResult:
        """
        增强版知识库搜索
        
        Args:
            question: 用户问题
            similarity_threshold: 相似度阈值
            confidence_threshold: 置信度阈值
            use_cache: 是否使用缓存
            
        Returns:
            RAGResult: 检索结果
        """
        if not self.enabled or not self.vector_store:
            return RAGResult(found_match=False)
        
        # 更新性能统计
        self._performance_stats["search_count"] += 1
        search_start = time.time()
        
        try:
            with self._error_handling("知识库搜索"):
                # 检查缓存
                cache_key = self._get_cache_key(
                    question, 
                    similarity_threshold=similarity_threshold,
                    confidence_threshold=confidence_threshold
                )
                
                if use_cache:
                    cached_result = self._get_from_cache(cache_key)
                    if cached_result:
                        logger.info("使用缓存结果")
                        return cached_result
                
                # 使用配置文件中的默认值
                if similarity_threshold is None:
                    similarity_threshold = config.rag.similarity_threshold
                if confidence_threshold is None:
                    confidence_threshold = config.rag.confidence_threshold
                
                # 搜索相似问题
                similar_items = self.vector_store.search_similar_questions(
                    question=question,
                    top_k=5,
                    similarity_threshold=similarity_threshold
                )
                
                if not similar_items:
                    logger.info("未找到相似的SQL知识")
                    result = RAGResult(found_match=False)
                    if use_cache:
                        self._set_cache(cache_key, result)
                    return result
                
                # 使用RAG策略选择器
                rag_result = RAGResult(
                    found_match=True,
                    best_match=similar_items[0],
                    similar_examples=similar_items[:3],
                    confidence=similar_items[0]["similarity"]
                )
                
                # 使用策略选择器确定策略
                strategy = self.rag_strategy.determine_strategy(rag_result)
                rag_result.should_use_cached = self.rag_strategy.should_use_cached_sql(rag_result)
                rag_result.strategy = strategy
                
                logger.info(f"使用策略: {strategy}")
                
                # 缓存结果
                if use_cache:
                    self._set_cache(cache_key, rag_result)
                
                return rag_result
                
        except Exception as e:
            logger.error(f"搜索SQL知识库失败: {str(e)}")
            return RAGResult(found_match=False)
        finally:
            # 更新性能统计
            search_time = time.time() - search_start
            self._performance_stats["total_search_time"] += search_time
            self._performance_stats["avg_search_time"] = (
                self._performance_stats["total_search_time"] / 
                self._performance_stats["search_count"]
            )
    
    def batch_add_knowledge(self, 
                           items: List[Dict[str, Any]], 
                           validate: bool = True,
                           max_workers: int = 4) -> BatchOperationResult:
        """
        批量添加知识库条目
        
        Args:
            items: 知识库条目列表，每个条目包含question, sql, description等字段
            validate: 是否验证数据
            max_workers: 最大并发数
            
        Returns:
            BatchOperationResult: 批量操作结果
        """
        if not self.enabled or not self.vector_store:
            return BatchOperationResult(
                total_items=len(items),
                successful_items=0,
                failed_items=len(items),
                errors=[{"error": "知识库未启用"}],
                execution_time=0.0
            )
        
        start_time = time.time()
        successful_items = 0
        failed_items = 0
        errors = []
        
        with self._error_handling("批量添加知识库条目"):
            # 数据验证
            if validate:
                validated_items = []
                for i, item in enumerate(items):
                    validation = self._validate_input_data(
                        item.get("question", ""),
                        item.get("sql", ""),
                        item.get("description", "")
                    )
                    
                    if validation.is_valid:
                        validated_items.append(item)
                    else:
                        failed_items += 1
                        errors.append({
                            "index": i,
                            "item": item,
                            "errors": validation.errors
                        })
                
                items = validated_items
            
            # 并发处理
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_item = {
                    executor.submit(self._add_single_knowledge_item, item): item 
                    for item in items
                }
                
                for future in as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        result = future.result()
                        if result:
                            successful_items += 1
                        else:
                            failed_items += 1
                            errors.append({
                                "item": item,
                                "error": "添加失败"
                            })
                    except Exception as e:
                        failed_items += 1
                        errors.append({
                            "item": item,
                            "error": str(e)
                        })
        
        execution_time = time.time() - start_time
        
        return BatchOperationResult(
            total_items=len(items) + failed_items,  # 包含验证失败的条目
            successful_items=successful_items,
            failed_items=failed_items,
            errors=errors,
            execution_time=execution_time
        )
    
    def _add_single_knowledge_item(self, item: Dict[str, Any]) -> bool:
        """添加单个知识库条目"""
        try:
            item_id = self.vector_store.add_sql_knowledge(
                question=item.get("question", ""),
                sql=item.get("sql", ""),
                description=item.get("description", ""),
                tags=item.get("tags", []),
                rating=item.get("rating", 1.0),
                metadata=item.get("metadata", {})
            )
            return bool(item_id)
        except Exception as e:
            logger.error(f"添加知识库条目失败: {str(e)}")
            return False
    
    def create_knowledge_version(self, 
                               item_id: str, 
                               change_reason: str,
                               created_by: str = "system") -> Optional[str]:
        """
        创建知识库条目版本
        
        Args:
            item_id: 条目ID
            change_reason: 变更原因
            created_by: 创建者
            
        Returns:
            Optional[str]: 版本ID
        """
        if not self.enabled or not self.vector_store:
            return None
        
        try:
            with self._error_handling("创建知识库版本"):
                # 获取当前条目数据
                existing = self.vector_store.collection.get(
                    ids=[item_id],
                    include=['metadatas']
                )
                
                if not existing['metadatas']:
                    logger.warning(f"条目不存在: {item_id}")
                    return None
                
                metadata = existing['metadatas'][0]
                
                # 创建版本记录
                version_id = f"v_{item_id}_{int(time.time())}"
                version_data = {
                    "version_id": version_id,
                    "item_id": item_id,
                    "question": metadata.get("question", ""),
                    "sql": metadata.get("sql", ""),
                    "description": metadata.get("description", ""),
                    "tags": metadata.get("tags", "[]"),
                    "rating": metadata.get("rating", 0.0),
                    "created_at": datetime.now().isoformat(),
                    "created_by": created_by,
                    "change_reason": change_reason
                }
                
                # 将版本信息添加到元数据
                versions = json.loads(metadata.get("versions", "[]"))
                versions.append(version_data)
                metadata["versions"] = json.dumps(versions)
                metadata["version_count"] = len(versions)
                
                # 更新条目
                self.vector_store.collection.update(
                    ids=[item_id],
                    metadatas=[metadata]
                )
                
                logger.info(f"创建知识库版本: {version_id}")
                return version_id
                
        except Exception as e:
            logger.error(f"创建知识库版本失败: {str(e)}")
            return None
    
    def get_knowledge_versions(self, item_id: str) -> List[KnowledgeVersion]:
        """获取知识库条目的版本历史"""
        if not self.enabled or not self.vector_store:
            return []
        
        try:
            existing = self.vector_store.collection.get(
                ids=[item_id],
                include=['metadatas']
            )
            
            if not existing['metadatas']:
                return []
            
            metadata = existing['metadatas'][0]
            versions_data = json.loads(metadata.get("versions", "[]"))
            
            versions = []
            for version_data in versions_data:
                version = KnowledgeVersion(
                    version_id=version_data["version_id"],
                    item_id=version_data["item_id"],
                    question=version_data["question"],
                    sql=version_data["sql"],
                    description=version_data["description"],
                    tags=json.loads(version_data["tags"]),
                    rating=version_data["rating"],
                    created_at=datetime.fromisoformat(version_data["created_at"]),
                    created_by=version_data["created_by"],
                    change_reason=version_data["change_reason"]
                )
                versions.append(version)
            
            return versions
            
        except Exception as e:
            logger.error(f"获取知识库版本失败: {str(e)}")
            return []
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        cache_hit_rate = (
            self._performance_stats["cache_hits"] / 
            max(self._performance_stats["search_count"], 1)
        )
        
        return {
            "search_count": self._performance_stats["search_count"],
            "cache_hits": self._performance_stats["cache_hits"],
            "cache_hit_rate": cache_hit_rate,
            "avg_search_time": self._performance_stats["avg_search_time"],
            "cache_size": len(self._cache),
            "enabled": self.enabled
        }
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("知识库缓存已清空")
    
    def optimize_search_algorithm(self, 
                                 question: str, 
                                 top_k: int = 10) -> List[Dict[str, Any]]:
        """
        优化的搜索算法，提高相似度计算准确性
        
        Args:
            question: 查询问题
            top_k: 返回结果数量
            
        Returns:
            List[Dict]: 优化后的搜索结果
        """
        if not self.enabled or not self.vector_store:
            return []
        
        try:
            with self._error_handling("优化搜索算法"):
                # 多阶段搜索策略
                
                # 第一阶段：基础向量搜索
                basic_results = self.vector_store.search_similar_questions(
                    question=question,
                    top_k=top_k * 2,  # 搜索更多候选
                    similarity_threshold=0.5  # 降低阈值获取更多候选
                )
                
                if not basic_results:
                    return []
                
                # 第二阶段：语义相似度重排序
                enhanced_results = []
                for result in basic_results:
                    # 计算增强相似度分数
                    enhanced_score = self._calculate_enhanced_similarity(
                        question, result
                    )
                    
                    result["enhanced_similarity"] = enhanced_score
                    result["original_similarity"] = result["similarity"]
                    result["similarity"] = enhanced_score  # 使用增强分数
                    
                    enhanced_results.append(result)
                
                # 按增强相似度排序
                enhanced_results.sort(
                    key=lambda x: x["enhanced_similarity"], 
                    reverse=True
                )
                
                # 返回top_k结果
                return enhanced_results[:top_k]
                
        except Exception as e:
            logger.error(f"优化搜索算法失败: {str(e)}")
            return []
    
    def _calculate_enhanced_similarity(self, 
                                     question: str, 
                                     result: Dict[str, Any]) -> float:
        """
        计算增强相似度分数
        
        Args:
            question: 查询问题
            result: 搜索结果
            
        Returns:
            float: 增强相似度分数
        """
        base_similarity = result["similarity"]
        
        # 因子1：关键词匹配度
        keyword_score = self._calculate_keyword_similarity(
            question, result["question"]
        )
        
        # 因子2：SQL复杂度匹配度
        complexity_score = self._calculate_complexity_similarity(
            question, result["sql"]
        )
        
        # 因子3：历史评分权重
        rating_weight = max(0.1, (result["rating"] + 1) / 2)  # 0.1-1.0
        
        # 因子4：使用频率权重
        usage_weight = min(1.0, 1 + result["usage_count"] * 0.1)
        
        # 综合计算增强相似度
        enhanced_similarity = (
            base_similarity * 0.6 +  # 基础向量相似度权重60%
            keyword_score * 0.2 +    # 关键词匹配权重20%
            complexity_score * 0.1 + # 复杂度匹配权重10%
            base_similarity * rating_weight * 0.05 +  # 评分权重5%
            base_similarity * usage_weight * 0.05     # 使用频率权重5%
        )
        
        return min(1.0, enhanced_similarity)
    
    def _calculate_keyword_similarity(self, question1: str, question2: str) -> float:
        """计算关键词相似度"""
        # 简单的关键词提取和匹配
        def extract_keywords(text: str) -> Set[str]:
            # 对中文文本进行简单的字符级分词
            # 移除标点符号，转换为小写
            import string
            # 移除英文标点符号
            text = text.translate(str.maketrans('', '', string.punctuation))
            # 移除中文标点符号
            chinese_punctuation = '，。！？；：""''（）【】《》'
            for punct in chinese_punctuation:
                text = text.replace(punct, ' ')
            
            # 提取中文词汇和英文单词
            words = set()
            # 英文单词
            english_words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
            words.update(english_words)
            
            # 中文字符（简单处理：提取2-4字的中文词组）
            chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
            for chars in chinese_chars:
                # 提取2-4字的子串作为词汇
                for i in range(len(chars)):
                    for length in [2, 3, 4]:
                        if i + length <= len(chars):
                            word = chars[i:i+length]
                            words.add(word)
                # 也添加单个字符
                words.update(chars)
            
            # 过滤停用词
            stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '如何', '什么', '哪个', 
                         'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
            return set(word for word in words if len(word) > 1 and word not in stop_words)
        
        keywords1 = extract_keywords(question1)
        keywords2 = extract_keywords(question2)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # 计算Jaccard相似度
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_complexity_similarity(self, question: str, sql: str) -> float:
        """计算SQL复杂度匹配度"""
        # 从问题中推断查询复杂度
        question_lower = question.lower()
        
        complexity_indicators = {
            "简单": ["查询", "显示", "列出", "获取"],
            "中等": ["统计", "计算", "分组", "排序", "前", "最"],
            "复杂": ["关联", "连接", "子查询", "嵌套", "复杂"]
        }
        
        question_complexity = "简单"
        for complexity, indicators in complexity_indicators.items():
            if any(indicator in question_lower for indicator in indicators):
                question_complexity = complexity
        
        # 分析SQL复杂度
        sql_upper = sql.upper()
        sql_complexity = "简单"
        
        if any(keyword in sql_upper for keyword in ["JOIN", "UNION", "SUBQUERY"]):
            sql_complexity = "复杂"
        elif any(keyword in sql_upper for keyword in ["GROUP BY", "ORDER BY", "HAVING"]):
            sql_complexity = "中等"
        
        # 复杂度匹配度
        complexity_match = {
            ("简单", "简单"): 1.0,
            ("简单", "中等"): 0.7,
            ("简单", "复杂"): 0.3,
            ("中等", "简单"): 0.7,
            ("中等", "中等"): 1.0,
            ("中等", "复杂"): 0.8,
            ("复杂", "简单"): 0.3,
            ("复杂", "中等"): 0.8,
            ("复杂", "复杂"): 1.0,
        }
        
        return complexity_match.get((question_complexity, sql_complexity), 0.5)

# 全局增强知识库管理器实例
_enhanced_knowledge_manager: Optional[EnhancedSQLKnowledgeManager] = None

def get_enhanced_knowledge_manager() -> EnhancedSQLKnowledgeManager:
    """获取全局增强知识库管理器实例"""
    global _enhanced_knowledge_manager
    
    if _enhanced_knowledge_manager is None:
        _enhanced_knowledge_manager = EnhancedSQLKnowledgeManager()
    
    return _enhanced_knowledge_manager