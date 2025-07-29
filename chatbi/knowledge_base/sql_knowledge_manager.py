"""
SQL知识库管理器
集成RAG功能到SQL生成流程
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .vector_store import SQLVectorStore, get_vector_store, CHROMADB_AVAILABLE
from ..config import config

logger = logging.getLogger(__name__)

@dataclass
class RAGResult:
    """RAG检索结果"""
    found_match: bool
    best_match: Optional[Dict[str, Any]] = None
    similar_examples: Optional[List[Dict[str, Any]]] = None
    confidence: float = 0.0
    should_use_cached: bool = False

class SQLKnowledgeManager:
    """SQL知识库管理器"""
    
    def __init__(self):
        """初始化知识库管理器"""
        self.vector_store = None
        self.enabled = CHROMADB_AVAILABLE
        
        if self.enabled:
            try:
                self.vector_store = get_vector_store()
                logger.info("SQL知识库管理器初始化成功")
            except Exception as e:
                logger.error(f"SQL知识库初始化失败: {str(e)}")
                self.enabled = False
        else:
            logger.warning("SQL知识库功能已禁用（ChromaDB未安装）")
    
    def search_knowledge(self, 
                        question: str,
                        similarity_threshold: float = None,
                        confidence_threshold: float = None) -> RAGResult:
        """
        搜索SQL知识库
        
        Args:
            question: 用户问题
            similarity_threshold: 相似度阈值
            confidence_threshold: 置信度阈值（决定是否直接使用缓存SQL）
            
        Returns:
            RAGResult: 检索结果
        """
        if not self.enabled or not self.vector_store:
            return RAGResult(found_match=False)
        
        # 使用配置文件中的默认值
        from ..config import config
        if similarity_threshold is None:
            similarity_threshold = config.rag_similarity_threshold
        if confidence_threshold is None:
            confidence_threshold = config.rag_confidence_threshold
        
        try:
            # 搜索相似问题
            similar_items = self.vector_store.search_similar_questions(
                question=question,
                top_k=5,
                similarity_threshold=similarity_threshold
            )
            
            if not similar_items:
                logger.info("未找到相似的SQL知识")
                return RAGResult(found_match=False)
            
            # 获取最佳匹配
            best_match = similar_items[0]
            confidence = best_match["similarity"]
            
            # 策略选择逻辑
            if confidence >= confidence_threshold and best_match["rating"] > 0:
                # 高相似度策略：直接使用缓存SQL
                should_use_cached = True
                strategy = "high_similarity_cached"
                logger.info(f"🎯 高相似度策略 (相似度: {confidence:.3f} >= {confidence_threshold}): 直接使用缓存SQL")
            elif confidence >= (similarity_threshold + confidence_threshold) / 2:
                # 中相似度策略：使用相似示例辅助生成
                should_use_cached = False
                strategy = "medium_similarity_assisted"
                logger.info(f"🔍 中相似度策略 (相似度: {confidence:.3f}): 使用相似示例辅助生成")
            else:
                # 低相似度策略：常规生成流程（但仍提供示例）
                should_use_cached = False
                strategy = "low_similarity_normal"
                logger.info(f"📝 低相似度策略 (相似度: {confidence:.3f}): 常规生成流程")
            
            return RAGResult(
                found_match=True,
                best_match=best_match,
                similar_examples=similar_items[:3],  # 返回前3个作为示例
                confidence=confidence,
                should_use_cached=should_use_cached
            )
            
        except Exception as e:
            logger.error(f"搜索SQL知识库失败: {str(e)}")
            return RAGResult(found_match=False)
    
    def add_positive_feedback(self, 
                             question: str, 
                             sql: str,
                             description: str = None,
                             metadata: Dict[str, Any] = None) -> bool:
        """
        添加正面反馈（用户点赞）
        
        Args:
            question: 用户问题
            sql: SQL查询
            description: 描述信息
            metadata: 额外元数据
            
        Returns:
            bool: 是否成功添加
        """
        if not self.enabled or not self.vector_store:
            logger.warning("SQL知识库未启用，跳过正面反馈存储")
            return False
        
        try:
            # 添加标签
            tags = ["用户点赞", "高质量"]
            
            # 从SQL中提取更多标签
            sql_tags = self._extract_sql_tags(sql)
            tags.extend(sql_tags)
            
            # 构建元数据
            feedback_metadata = {
                "feedback_type": "positive",
                "source": "user_like",
                "timestamp": datetime.now().isoformat()
            }
            
            if metadata:
                feedback_metadata.update(metadata)
            
            # 添加到知识库
            item_id = self.vector_store.add_sql_knowledge(
                question=question,
                sql=sql,
                description=description or "用户点赞的高质量SQL查询",
                tags=tags,
                rating=1.0,  # 点赞给予1分
                metadata=feedback_metadata
            )
            
            logger.info(f"成功添加正面反馈到知识库: {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加正面反馈失败: {str(e)}")
            return False
    
    def update_usage_feedback(self, question: str, sql: str, rating_change: float = 0.1):
        """
        更新使用反馈
        
        Args:
            question: 问题
            sql: SQL查询
            rating_change: 评分变化
        """
        if not self.enabled or not self.vector_store:
            return
        
        try:
            # 搜索匹配的条目
            similar_items = self.vector_store.search_similar_questions(
                question=question,
                top_k=1,
                similarity_threshold=0.9
            )
            
            if similar_items and similar_items[0]["sql"].strip() == sql.strip():
                # 找到匹配的条目，更新使用统计
                import hashlib
                content_hash = hashlib.md5(f"{question}_{sql}".encode()).hexdigest()
                item_id = f"sql_{content_hash}"
                
                self.vector_store.update_usage_stats(item_id, rating_change)
                logger.info(f"更新SQL使用反馈: {item_id}")
            
        except Exception as e:
            logger.error(f"更新使用反馈失败: {str(e)}")
    
    def get_examples_for_generation(self, 
                                   question: str, 
                                   max_examples: int = 3) -> List[Dict[str, str]]:
        """
        获取用于SQL生成的示例
        
        Args:
            question: 用户问题
            max_examples: 最大示例数量
            
        Returns:
            List[Dict]: SQL示例列表
        """
        if not self.enabled or not self.vector_store:
            return []
        
        try:
            # 搜索相关示例
            similar_items = self.vector_store.search_similar_questions(
                question=question,
                top_k=max_examples * 2,  # 搜索更多以便筛选
                similarity_threshold=0.6  # 降低阈值以获取更多示例
            )
            
            # 筛选高质量示例
            quality_examples = []
            for item in similar_items:
                if (item["rating"] > 0 or item["usage_count"] > 0) and len(quality_examples) < max_examples:
                    quality_examples.append({
                        "question": item["question"],
                        "sql": item["sql"],
                        "similarity": item["similarity"]
                    })
            
            logger.info(f"为SQL生成提供 {len(quality_examples)} 个示例")
            return quality_examples
            
        except Exception as e:
            logger.error(f"获取SQL生成示例失败: {str(e)}")
            return []
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if not self.enabled or not self.vector_store:
            return {
                "enabled": False,
                "reason": "ChromaDB未安装或初始化失败"
            }
        
        try:
            stats = self.vector_store.get_knowledge_stats()
            stats["enabled"] = True
            return stats
        except Exception as e:
            logger.error(f"获取知识库统计失败: {str(e)}")
            return {
                "enabled": False,
                "error": str(e)
            }
    
    def get_all_knowledge_items(self) -> List[Dict[str, Any]]:
        """获取所有知识库条目"""
        if not self.enabled or not self.vector_store:
            return []
        
        try:
            # 获取所有数据
            all_data = self.vector_store.collection.get(
                include=['documents', 'metadatas']
            )
            
            items = []
            if all_data['ids']:
                for i, item_id in enumerate(all_data['ids']):
                    metadata = all_data['metadatas'][i]
                    items.append({
                        'id': item_id,
                        'question': metadata.get('question', ''),
                        'sql': metadata.get('sql', ''),
                        'description': metadata.get('description', ''),
                        'tags': json.loads(metadata.get('tags', '[]')),
                        'rating': float(metadata.get('rating', 0.0)),
                        'usage_count': int(metadata.get('usage_count', 0)),
                        'created_at': metadata.get('created_at', ''),
                        'updated_at': metadata.get('updated_at', '')
                    })
            
            # 按创建时间排序
            items.sort(key=lambda x: x['created_at'], reverse=True)
            return items
            
        except Exception as e:
            logger.error(f"获取知识库条目失败: {str(e)}")
            return []
    
    def update_knowledge_item(self, item_id: str, question: str, sql: str, 
                             description: str = "", tags: List[str] = None) -> bool:
        """更新知识库条目"""
        if not self.enabled or not self.vector_store:
            return False
        
        try:
            # 获取现有条目
            existing = self.vector_store.collection.get(
                ids=[item_id],
                include=['metadatas']
            )
            
            if not existing['metadatas']:
                logger.warning(f"条目不存在: {item_id}")
                return False
            
            # 更新元数据
            metadata = existing['metadatas'][0]
            metadata.update({
                'question': question,
                'sql': sql,
                'description': description,
                'tags': json.dumps(tags or []),
                'updated_at': datetime.now().isoformat()
            })
            
            # 重新生成文档内容
            doc_content = self.vector_store._build_document_content(
                question, sql, description, tags
            )
            
            # 生成新的embedding
            embedding = self.vector_store.embedding_service.embed_text(doc_content)
            
            # 更新向量数据库
            self.vector_store.collection.update(
                ids=[item_id],
                documents=[doc_content],
                metadatas=[metadata],
                embeddings=[embedding]
            )
            
            logger.info(f"成功更新知识库条目: {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新知识库条目失败: {str(e)}")
            return False
    
    def delete_knowledge_item(self, item_id: str) -> bool:
        """删除知识库条目"""
        if not self.enabled or not self.vector_store:
            return False
        
        try:
            self.vector_store.collection.delete(ids=[item_id])
            logger.info(f"成功删除知识库条目: {item_id}")
            return True
        except Exception as e:
            logger.error(f"删除知识库条目失败: {str(e)}")
            return False
    
    def add_knowledge_item(self, question: str, sql: str, description: str = "", 
                          tags: List[str] = None, rating: float = 1.0) -> bool:
        """添加新的知识库条目"""
        if not self.enabled or not self.vector_store:
            return False
        
        try:
            item_id = self.vector_store.add_sql_knowledge(
                question=question,
                sql=sql,
                description=description,
                tags=tags or [],
                rating=rating
            )
            logger.info(f"成功添加知识库条目: {item_id}")
            return True
        except Exception as e:
            logger.error(f"添加知识库条目失败: {str(e)}")
            return False
    
    def _extract_sql_tags(self, sql: str) -> List[str]:
        """从SQL中提取标签"""
        tags = []
        sql_upper = sql.upper()
        
        # 查询类型标签
        if 'JOIN' in sql_upper:
            tags.append("关联查询")
        if 'GROUP BY' in sql_upper:
            tags.append("分组查询")
        if 'ORDER BY' in sql_upper:
            tags.append("排序查询")
        if 'HAVING' in sql_upper:
            tags.append("条件分组")
        if 'UNION' in sql_upper:
            tags.append("联合查询")
        if 'SUBQUERY' in sql_upper or '(' in sql and 'SELECT' in sql_upper:
            tags.append("子查询")
        
        # 聚合函数标签
        agg_functions = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']
        for func in agg_functions:
            if func in sql_upper:
                tags.append(f"{func.lower()}聚合")
        
        # 时间相关标签
        time_keywords = ['DATE', 'TIMESTAMP', 'CURRENT_DATE', 'NOW()', 'INTERVAL']
        for keyword in time_keywords:
            if keyword in sql_upper:
                tags.append("时间查询")
                break
        
        return tags

# 全局知识库管理器实例
_knowledge_manager: Optional[SQLKnowledgeManager] = None

def get_knowledge_manager() -> SQLKnowledgeManager:
    """获取全局知识库管理器实例"""
    global _knowledge_manager
    
    if _knowledge_manager is None:
        _knowledge_manager = SQLKnowledgeManager()
    
    return _knowledge_manager