"""
RAG系统初始化器
在系统启动时检查RAG功能可用性并进行初始化
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .config import config
from .config_manager import rag_config_manager


class RAGInitializer:
    """RAG系统初始化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.initialization_status = {
            'initialized': False,
            'available': False,
            'errors': [],
            'warnings': [],
            'timestamp': None
        }
    
    def initialize(self) -> Dict[str, Any]:
        """初始化RAG系统"""
        self.logger.info("开始初始化RAG系统...")
        
        try:
            # 检查配置
            if not self._check_configuration():
                return self.initialization_status
            
            # 检查依赖
            if not self._check_dependencies():
                return self.initialization_status
            
            # 初始化向量数据库
            if not self._initialize_vector_store():
                return self.initialization_status
            
            # 初始化嵌入服务
            if not self._initialize_embedding_service():
                return self.initialization_status
            
            # 初始化知识库管理器
            if not self._initialize_knowledge_manager():
                return self.initialization_status
            
            # 标记初始化成功
            self.initialization_status.update({
                'initialized': True,
                'available': True,
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info("RAG系统初始化成功")
            
        except Exception as e:
            self.logger.error(f"RAG系统初始化失败: {e}")
            self.initialization_status['errors'].append(f"初始化异常: {str(e)}")
        
        return self.initialization_status
    
    def _check_configuration(self) -> bool:
        """检查配置"""
        try:
            # 验证RAG配置
            validation_result = config.rag.validate()
            
            if validation_result['errors']:
                self.initialization_status['errors'].extend(validation_result['errors'])
                self.logger.error(f"RAG配置验证失败: {validation_result['errors']}")
                return False
            
            if validation_result['warnings']:
                self.initialization_status['warnings'].extend(validation_result['warnings'])
                self.logger.warning(f"RAG配置警告: {validation_result['warnings']}")
            
            # 检查RAG是否启用
            if not config.rag.enabled:
                self.initialization_status['warnings'].append("RAG功能已禁用")
                self.logger.info("RAG功能已禁用，跳过初始化")
                return False
            
            return True
            
        except Exception as e:
            error_msg = f"配置检查失败: {str(e)}"
            self.initialization_status['errors'].append(error_msg)
            self.logger.error(error_msg)
            return False
    
    def _check_dependencies(self) -> bool:
        """检查依赖包"""
        required_packages = [
            ('chromadb', 'ChromaDB向量数据库'),
            ('sentence_transformers', 'Sentence Transformers'),
            ('dashscope', 'DashScope API客户端'),
            ('numpy', 'NumPy数值计算库')
        ]
        
        missing_packages = []
        
        for package, description in required_packages:
            try:
                __import__(package)
                self.logger.debug(f"✓ {description} 可用")
            except ImportError:
                missing_packages.append((package, description))
                self.logger.error(f"✗ {description} 不可用")
        
        if missing_packages:
            error_msg = f"缺少必需依赖: {', '.join([pkg for pkg, _ in missing_packages])}"
            self.initialization_status['errors'].append(error_msg)
            return False
        
        return True
    
    def _initialize_vector_store(self) -> bool:
        """初始化向量数据库"""
        try:
            from .knowledge_base.vector_store import SQLVectorStore
            
            # 创建向量存储实例
            vector_store = SQLVectorStore()
            
            # 测试连接
            if hasattr(vector_store, 'client') and vector_store.client:
                self.logger.info("✓ 向量数据库初始化成功")
                return True
            else:
                error_msg = "向量数据库客户端创建失败"
                self.initialization_status['errors'].append(error_msg)
                self.logger.error(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"向量数据库初始化失败: {str(e)}"
            self.initialization_status['errors'].append(error_msg)
            self.logger.error(error_msg)
            return False
    
    def _initialize_embedding_service(self) -> bool:
        """初始化嵌入服务"""
        try:
            from .knowledge_base.embedding_service import QwenEmbeddingService
            
            # 检查API密钥
            if not config.llm.api_key:
                error_msg = "DashScope API密钥未设置"
                self.initialization_status['errors'].append(error_msg)
                self.logger.error(error_msg)
                return False
            
            # 创建嵌入服务实例
            embedding_service = QwenEmbeddingService()
            
            # 测试嵌入服务（使用简单文本）
            try:
                test_embedding = embedding_service.get_embedding("测试文本")
                if test_embedding and len(test_embedding) > 0:
                    self.logger.info("✓ 嵌入服务初始化成功")
                    return True
                else:
                    error_msg = "嵌入服务测试失败"
                    self.initialization_status['errors'].append(error_msg)
                    self.logger.error(error_msg)
                    return False
            except Exception as e:
                # 如果测试失败，记录警告但不阻止初始化
                warning_msg = f"嵌入服务测试失败，可能是网络问题: {str(e)}"
                self.initialization_status['warnings'].append(warning_msg)
                self.logger.warning(warning_msg)
                return True  # 允许继续，运行时再处理
                
        except Exception as e:
            error_msg = f"嵌入服务初始化失败: {str(e)}"
            self.initialization_status['errors'].append(error_msg)
            self.logger.error(error_msg)
            return False
    
    def _initialize_knowledge_manager(self) -> bool:
        """初始化知识库管理器"""
        try:
            from .knowledge_base.enhanced_sql_knowledge_manager import EnhancedSQLKnowledgeManager
            
            # 创建知识库管理器实例
            knowledge_manager = EnhancedSQLKnowledgeManager()
            
            # 检查知识库状态
            try:
                stats = knowledge_manager.get_knowledge_stats()
                self.logger.info(f"✓ 知识库管理器初始化成功，当前条目数: {stats.get('total_entries', 0)}")
                return True
            except Exception as e:
                warning_msg = f"知识库状态检查失败: {str(e)}"
                self.initialization_status['warnings'].append(warning_msg)
                self.logger.warning(warning_msg)
                return True  # 允许继续，可能是空知识库
                
        except Exception as e:
            error_msg = f"知识库管理器初始化失败: {str(e)}"
            self.initialization_status['errors'].append(error_msg)
            self.logger.error(error_msg)
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取初始化状态"""
        return self.initialization_status.copy()
    
    def is_available(self) -> bool:
        """检查RAG系统是否可用"""
        return self.initialization_status.get('available', False)
    
    def get_health_check(self) -> Dict[str, Any]:
        """获取系统健康检查结果"""
        health_status = {
            'status': 'healthy' if self.is_available() else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        if not self.is_available():
            health_status['components']['initialization'] = {
                'status': 'failed',
                'errors': self.initialization_status.get('errors', [])
            }
            return health_status
        
        # 检查各个组件的健康状态
        try:
            # 检查配置
            config_validation = config.rag.validate()
            health_status['components']['configuration'] = {
                'status': 'healthy' if config_validation['valid'] else 'unhealthy',
                'errors': config_validation.get('errors', []),
                'warnings': config_validation.get('warnings', [])
            }
            
            # 检查向量数据库
            try:
                from .knowledge_base.vector_store import SQLVectorStore
                vector_store = SQLVectorStore()
                health_status['components']['vector_store'] = {
                    'status': 'healthy' if hasattr(vector_store, 'client') else 'unhealthy'
                }
            except Exception as e:
                health_status['components']['vector_store'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            
            # 检查知识库管理器
            try:
                from .knowledge_base.enhanced_sql_knowledge_manager import EnhancedSQLKnowledgeManager
                knowledge_manager = EnhancedSQLKnowledgeManager()
                stats = knowledge_manager.get_knowledge_stats()
                health_status['components']['knowledge_manager'] = {
                    'status': 'healthy',
                    'stats': stats
                }
            except Exception as e:
                health_status['components']['knowledge_manager'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            
        except Exception as e:
            health_status['components']['health_check'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return health_status
    
    def restart(self) -> Dict[str, Any]:
        """重启RAG系统"""
        self.logger.info("重启RAG系统...")
        
        # 重置状态
        self.initialization_status = {
            'initialized': False,
            'available': False,
            'errors': [],
            'warnings': [],
            'timestamp': None
        }
        
        # 重新初始化
        return self.initialize()


# 全局初始化器实例
rag_initializer = RAGInitializer()