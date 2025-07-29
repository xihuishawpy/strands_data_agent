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
        try:
            if not texts:
                return []
            
            # 调用Qwen embedding API
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            # 提取向量
            embeddings = []
            for item in response.data:
                embeddings.append(item.embedding)
            
            logger.info(f"成功生成 {len(embeddings)} 个向量")
            return embeddings
            
        except Exception as e:
            logger.error(f"生成向量失败: {str(e)}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        对单个文本进行向量化
        
        Args:
            text: 文本
            
        Returns:
            List[float]: 向量
        """
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []

# 全局embedding服务实例
_embedding_service: Optional[QwenEmbeddingService] = None

def get_embedding_service() -> QwenEmbeddingService:
    """获取全局embedding服务实例"""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = QwenEmbeddingService()
    
    return _embedding_service