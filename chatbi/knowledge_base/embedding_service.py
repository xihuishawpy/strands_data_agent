"""
Embedding服务
使用Qwen API进行文本向量化
"""

import logging
import openai
from typing import List, Optional
import numpy as np
from ..config import config

logger = logging.getLogger(__name__)

class QwenEmbeddingService:
    """Qwen Embedding服务"""
    
    def __init__(self):
        """初始化embedding服务"""
        self.client = openai.OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url
        )
        self.model = config.llm.embedding_model
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        对文本列表进行向量化
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 向量列表
        """
        import time
        
        try:
            if not texts:
                return []
            
            # 过滤空文本
            valid_texts = [text.strip() for text in texts if text and text.strip()]
            if not valid_texts:
                logger.warning("所有输入文本都为空")
                return []
            
            logger.info(f"开始生成 {len(valid_texts)} 个文本的向量")
            start_time = time.time()
            
            # 调用Qwen embedding API
            response = self.client.embeddings.create(
                model=self.model,
                input=valid_texts,
                timeout=30.0  # 设置30秒超时
            )
            
            # 提取向量
            embeddings = []
            for item in response.data:
                embeddings.append(item.embedding)
            
            elapsed_time = time.time() - start_time
            logger.info(f"成功生成 {len(embeddings)} 个向量，耗时: {elapsed_time:.2f}秒")
            
            # 验证向量维度
            if embeddings:
                dimension = len(embeddings[0])
                logger.debug(f"向量维度: {dimension}")
                
                # 检查所有向量维度是否一致
                for i, emb in enumerate(embeddings):
                    if len(emb) != dimension:
                        logger.warning(f"向量 {i} 维度不一致: {len(emb)} vs {dimension}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"生成向量失败: {str(e)}")
            # 不再抛出异常，而是返回空列表
            return []
    
    def embed_text(self, text: str) -> List[float]:
        """
        对单个文本进行向量化
        
        Args:
            text: 文本
            
        Returns:
            List[float]: 向量
        """
        try:
            embeddings = self.embed_texts([text])
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"单文本向量化失败: {str(e)}")
            return []

# 全局embedding服务实例
_embedding_service: Optional[QwenEmbeddingService] = None

def get_embedding_service() -> QwenEmbeddingService:
    """获取全局embedding服务实例"""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = QwenEmbeddingService()
    
    return _embedding_service