"""
向量数据库管理器
负责SQL知识库的向量存储和检索
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB未安装，SQL知识库功能将被禁用")

from ..config import config
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

@dataclass
class SQLKnowledgeItem:
    """SQL知识库条目"""
    id: str
    question: str
    sql: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    rating: float = 0.0
    usage_count: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class QwenEmbeddingFunction:
    """自定义Qwen Embedding函数"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
    
    def __call__(self, input):
        """ChromaDB调用的embedding函数"""
        try:
            # 确保input是字符串列表
            if isinstance(input, str):
                input = [input]
            elif not isinstance(input, list):
                input = list(input)
            
            # 调用embedding服务
            embeddings = self.embedding_service.embed_texts(input)
            return embeddings
        except Exception as e:
            logger.error(f"Embedding函数调用失败: {str(e)}")
            raise

class SQLVectorStore:
    """SQL向量数据库管理器"""
    
    def __init__(self, 
                 collection_name: str = "sql_knowledge_base",
                 persist_directory: str = None):
        """
        初始化向量数据库
        
        Args:
            collection_name: 集合名称
            persist_directory: 持久化目录
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB未安装，请运行: pip install chromadb")
        
        self.collection_name = collection_name
        self.persist_directory = persist_directory or os.path.join("data", "knowledge_base", "vectors")
        
        # 确保目录存在
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 初始化embedding服务（用于手动embedding）
        self.embedding_service = get_embedding_service()
        
        # 获取或创建集合（不使用自定义embedding函数）
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"加载现有SQL知识库集合: {collection_name}")
        except Exception as e:
            # 检查是否是集合不存在的错误
            error_msg = str(e).lower()
            if "does not exist" in error_msg or "not found" in error_msg:
                # 集合不存在，创建新集合
                try:
                    self.collection = self.client.create_collection(
                        name=collection_name,
                        metadata={"description": "SQL查询知识库"}
                    )
                    logger.info(f"创建新的SQL知识库集合: {collection_name}")
                except Exception as create_error:
                    logger.error(f"创建集合失败: {str(create_error)}")
                    raise
            else:
                # 其他错误，记录并重新抛出
                logger.error(f"获取集合时出错: {str(e)}")
                raise
    
    def add_sql_knowledge(self, 
                         question: str, 
                         sql: str,
                         description: str = None,
                         tags: List[str] = None,
                         rating: float = 0.0,
                         metadata: Dict[str, Any] = None) -> str:
        """
        添加SQL知识到向量数据库
        
        Args:
            question: 用户问题
            sql: SQL查询语句
            description: 描述信息
            tags: 标签列表
            rating: 评分
            metadata: 额外元数据
            
        Returns:
            str: 知识条目ID
        """
        try:
            # 生成唯一ID
            content_hash = hashlib.md5(f"{question}_{sql}".encode()).hexdigest()
            item_id = f"sql_{content_hash}"
            
            # 构建文档内容（用于向量化）
            doc_content = self._build_document_content(question, sql, description, tags)
            
            # 构建元数据
            item_metadata = {
                "question": question,
                "sql": sql,
                "description": description or "",
                "tags": json.dumps(tags or []),
                "rating": rating,
                "usage_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            if metadata:
                item_metadata.update(metadata)
            
            # 生成embedding
            embedding = self.embedding_service.embed_text(doc_content)
            
            # 添加到向量数据库
            self.collection.add(
                documents=[doc_content],
                metadatas=[item_metadata],
                ids=[item_id],
                embeddings=[embedding]
            )
            
            logger.info(f"成功添加SQL知识: {item_id}")
            return item_id
            
        except Exception as e:
            logger.error(f"添加SQL知识失败: {str(e)}")
            raise
    
    def search_similar_questions(self, 
                                question: str, 
                                top_k: int = 5,
                                similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        搜索相似问题
        
        Args:
            question: 查询问题
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
            
        Returns:
            List[Dict]: 相似问题列表
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        
        def _search_with_timeout():
            try:
                # 首先检查集合中是否有数据
                collection_count = self.collection.count()
                logger.info(f"集合中共有 {collection_count} 个条目")
                
                if collection_count == 0:
                    logger.warning("集合为空，无法进行搜索")
                    return []
                
                # 生成查询embedding（添加超时）
                logger.info(f"开始生成查询向量: {question}")
                start_time = time.time()
                query_embedding = self.embedding_service.embed_text(question)
                embed_time = time.time() - start_time
                logger.info(f"向量生成完成，耗时: {embed_time:.2f}秒")
                
                if not query_embedding:
                    logger.error("查询向量生成失败")
                    return []
                
                # 执行向量搜索
                logger.info(f"开始向量搜索，向量维度: {len(query_embedding)}")
                search_start = time.time()
                
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, collection_count),
                    include=['documents', 'metadatas', 'distances']
                )
                
                search_time = time.time() - search_start
                logger.info(f"向量搜索完成，耗时: {search_time:.2f}秒")
                
                if not results or not results.get('documents') or not results['documents'][0]:
                    logger.warning("搜索结果为空")
                    return []
                
                similar_items = []
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                
                logger.info(f"处理 {len(documents)} 个搜索结果")
                
                for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                    try:
                        # 计算相似度（距离越小相似度越高）
                        similarity = max(0.0, 1.0 - distance / 2.0)
                        
                        logger.debug(f"结果 {i+1}: 距离={distance:.4f}, 相似度={similarity:.4f}")
                        
                        if similarity >= similarity_threshold:
                            # 安全地解析tags
                            tags = []
                            try:
                                tags_str = metadata.get("tags", "[]")
                                if isinstance(tags_str, str):
                                    tags = json.loads(tags_str)
                                elif isinstance(tags_str, list):
                                    tags = tags_str
                            except:
                                tags = []
                            
                            item = {
                                "similarity": similarity,
                                "question": metadata.get("question", ""),
                                "sql": metadata.get("sql", ""),
                                "description": metadata.get("description", ""),
                                "tags": tags,
                                "rating": float(metadata.get("rating", 0.0)),
                                "usage_count": int(metadata.get("usage_count", 0)),
                                "created_at": metadata.get("created_at", ""),
                                "updated_at": metadata.get("updated_at", "")
                            }
                            similar_items.append(item)
                            logger.info(f"添加相似项: {item['question'][:50]}... (相似度: {similarity:.3f})")
                    except Exception as item_error:
                        logger.warning(f"处理搜索结果项 {i} 时出错: {item_error}")
                        continue
                
                # 按相似度排序
                similar_items.sort(key=lambda x: x["similarity"], reverse=True)
                
                logger.info(f"找到 {len(similar_items)} 个相似问题")
                return similar_items
                
            except Exception as e:
                logger.error(f"搜索过程中出错: {str(e)}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")
                return []
        
        try:
            # 使用线程池执行搜索，设置超时
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_search_with_timeout)
                try:
                    # 从配置中获取超时时间，默认30秒
                    timeout = getattr(config.rag, 'search_timeout', 30.0)
                    result = future.result(timeout=timeout)
                    return result
                except TimeoutError:
                    logger.error(f"搜索超时（{timeout}秒），返回空结果")
                    return []
                except Exception as e:
                    logger.error(f"搜索执行失败: {str(e)}")
                    return []
                    
        except Exception as e:
            logger.error(f"搜索相似问题失败: {str(e)}")
            return []
    
    def update_usage_stats(self, item_id: str, rating_delta: float = 0.0):
        """
        更新使用统计
        
        Args:
            item_id: 条目ID
            rating_delta: 评分变化
        """
        try:
            # 获取现有数据
            result = self.collection.get(ids=[item_id], include=['metadatas'])
            
            if not result['metadatas']:
                logger.warning(f"未找到条目: {item_id}")
                return
            
            metadata = result['metadatas'][0]
            
            # 更新统计信息
            metadata['usage_count'] = metadata.get('usage_count', 0) + 1
            metadata['rating'] = metadata.get('rating', 0.0) + rating_delta
            metadata['updated_at'] = datetime.now().isoformat()
            
            # 更新数据库
            self.collection.update(
                ids=[item_id],
                metadatas=[metadata]
            )
            
            logger.info(f"更新使用统计: {item_id}")
            
        except Exception as e:
            logger.error(f"更新使用统计失败: {str(e)}")
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            count = self.collection.count()
            
            # 获取所有元数据进行统计
            all_data = self.collection.get(include=['metadatas'])
            
            if all_data['metadatas']:
                ratings = [float(m.get('rating', 0)) for m in all_data['metadatas']]
                usage_counts = [int(m.get('usage_count', 0)) for m in all_data['metadatas']]
                
                stats = {
                    "total_items": count,
                    "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
                    "total_usage": sum(usage_counts),
                    "top_rated_count": len([r for r in ratings if r > 0]),
                    "collection_name": self.collection_name
                }
            else:
                stats = {
                    "total_items": count,
                    "avg_rating": 0,
                    "total_usage": 0,
                    "top_rated_count": 0,
                    "collection_name": self.collection_name
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取知识库统计失败: {str(e)}")
            return {"error": str(e)}
    
    def delete_knowledge(self, item_id: str) -> bool:
        """删除知识条目"""
        try:
            self.collection.delete(ids=[item_id])
            logger.info(f"删除知识条目: {item_id}")
            return True
        except Exception as e:
            logger.error(f"删除知识条目失败: {str(e)}")
            return False
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """获取所有知识库条目"""
        try:
            # 获取所有条目
            results = self.collection.get(
                include=['documents', 'metadatas', 'embeddings']
            )
            
            if not results or not results.get('ids'):
                return []
            
            items = []
            for i, item_id in enumerate(results['ids']):
                metadata = results['metadatas'][i] if results.get('metadatas') else {}
                
                # 解析tags字段
                tags = metadata.get('tags', [])
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = []
                elif not isinstance(tags, list):
                    tags = []
                
                # 构建条目数据
                item = {
                    'id': item_id,
                    'question': metadata.get('question', ''),
                    'sql': metadata.get('sql', ''),
                    'description': metadata.get('description', ''),
                    'tags': tags,
                    'rating': metadata.get('rating', 0.0),
                    'usage_count': metadata.get('usage_count', 0),
                    'created_at': metadata.get('created_at', ''),
                    'updated_at': metadata.get('updated_at', ''),
                    'metadata': metadata
                }
                items.append(item)
            
            logger.info(f"获取到 {len(items)} 个知识库条目")
            return items
            
        except Exception as e:
            logger.error(f"获取所有知识库条目失败: {str(e)}")
            return []
    
    def update_item(self, item_id: str, update_data: Dict[str, Any]) -> bool:
        """更新知识库条目"""
        try:
            # 首先获取现有条目
            existing = self.collection.get(
                ids=[item_id],
                include=['documents', 'metadatas']
            )
            
            if not existing or not existing.get('ids'):
                logger.warning(f"条目不存在: {item_id}")
                return False
            
            # 获取现有元数据
            existing_metadata = existing['metadatas'][0] if existing.get('metadatas') else {}
            
            # 处理更新数据，确保符合ChromaDB元数据要求
            processed_update_data = {}
            for key, value in update_data.items():
                if key == 'tags':
                    # 将tags列表转换为JSON字符串
                    if isinstance(value, list):
                        processed_update_data[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        processed_update_data[key] = value
                else:
                    processed_update_data[key] = value
            
            # 合并更新数据
            new_metadata = {**existing_metadata, **processed_update_data}
            new_metadata['updated_at'] = datetime.now().isoformat()
            
            # 获取tags用于文档构建
            tags_for_doc = update_data.get('tags', existing_metadata.get('tags', []))
            if isinstance(tags_for_doc, str):
                try:
                    tags_for_doc = json.loads(tags_for_doc)
                except:
                    tags_for_doc = []
            
            # 构建新的文档内容
            new_document = self._build_document_content(
                question=update_data.get('question', existing_metadata.get('question', '')),
                sql=update_data.get('sql', existing_metadata.get('sql', '')),
                description=update_data.get('description', existing_metadata.get('description', '')),
                tags=tags_for_doc
            )
            
            # 生成新的嵌入向量
            new_embedding = self.embedding_service.embed_text(new_document)
            
            # 更新条目
            self.collection.update(
                ids=[item_id],
                documents=[new_document],
                metadatas=[new_metadata],
                embeddings=[new_embedding]
            )
            
            logger.info(f"更新知识库条目成功: {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新知识库条目失败: {str(e)}")
            return False
    
    def delete_item(self, item_id: str) -> bool:
        """删除知识库条目（别名方法）"""
        return self.delete_knowledge(item_id)
    
    def _build_document_content(self, 
                               question: str, 
                               sql: str, 
                               description: str = None,
                               tags: List[str] = None) -> str:
        """构建用于向量化的文档内容"""
        content_parts = [f"问题: {question}"]
        
        if description:
            content_parts.append(f"描述: {description}")
        
        if tags:
            content_parts.append(f"标签: {', '.join(tags)}")
        
        # 添加SQL的关键信息（不包含完整SQL以避免过度拟合）
        sql_keywords = self._extract_sql_keywords(sql)
        if sql_keywords:
            content_parts.append(f"SQL关键词: {', '.join(sql_keywords)}")
        
        return " | ".join(content_parts)
    
    def _extract_sql_keywords(self, sql: str) -> List[str]:
        """从SQL中提取关键词"""
        import re
        
        keywords = []
        sql_upper = sql.upper()
        
        # 提取表名
        table_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables = re.findall(table_pattern, sql_upper)
        keywords.extend([f"表:{t.lower()}" for t in tables])
        
        # 提取JOIN表名
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_tables = re.findall(join_pattern, sql_upper)
        keywords.extend([f"关联:{t.lower()}" for t in join_tables])
        
        # 提取聚合函数
        agg_functions = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']
        for func in agg_functions:
            if func in sql_upper:
                keywords.append(f"聚合:{func.lower()}")
        
        # 提取其他关键SQL结构
        if 'GROUP BY' in sql_upper:
            keywords.append("分组查询")
        if 'ORDER BY' in sql_upper:
            keywords.append("排序查询")
        if 'WHERE' in sql_upper:
            keywords.append("条件查询")
        
        return keywords

# 全局向量存储实例
_vector_store: Optional[SQLVectorStore] = None

def get_vector_store() -> SQLVectorStore:
    """获取全局向量存储实例"""
    global _vector_store
    
    if _vector_store is None:
        try:
            _vector_store = SQLVectorStore()
        except ImportError as e:
            logger.error(f"无法初始化向量数据库: {str(e)}")
            raise
    
    return _vector_store