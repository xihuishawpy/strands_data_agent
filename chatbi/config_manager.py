"""
RAG配置管理器
提供动态配置更新、验证和监控功能
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import asdict
from datetime import datetime

from .config import config, RAGConfig


class RAGConfigManager:
    """RAG配置管理器"""
    
    def __init__(self):
        self.config = config
        self.config_history = []
        self.logger = logging.getLogger(__name__)
    
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前RAG配置"""
        return asdict(self.config.rag)
    
    def update_thresholds(self, similarity: float, confidence: float) -> bool:
        """动态更新相似度阈值"""
        if not (0.0 <= similarity <= 1.0):
            self.logger.error(f"相似度阈值无效: {similarity}")
            return False
        
        if not (0.0 <= confidence <= 1.0):
            self.logger.error(f"置信度阈值无效: {confidence}")
            return False
        
        if similarity >= confidence:
            self.logger.warning("相似度阈值应该小于置信度阈值")
        
        # 记录配置变更历史
        self._record_config_change("thresholds", {
            "old_similarity": self.config.rag.similarity_threshold,
            "new_similarity": similarity,
            "old_confidence": self.config.rag.confidence_threshold,
            "new_confidence": confidence
        })
        
        return self.config.update_rag_config(
            similarity_threshold=similarity,
            confidence_threshold=confidence
        )
    
    def update_search_params(self, max_examples: int, search_timeout: float) -> bool:
        """更新搜索参数"""
        if max_examples <= 0:
            self.logger.error(f"最大示例数无效: {max_examples}")
            return False
        
        if search_timeout <= 0:
            self.logger.error(f"搜索超时时间无效: {search_timeout}")
            return False
        
        self._record_config_change("search_params", {
            "old_max_examples": self.config.rag.max_examples,
            "new_max_examples": max_examples,
            "old_search_timeout": self.config.rag.search_timeout,
            "new_search_timeout": search_timeout
        })
        
        return self.config.update_rag_config(
            max_examples=max_examples,
            search_timeout=search_timeout
        )
    
    def toggle_rag(self, enabled: bool) -> bool:
        """启用或禁用RAG功能"""
        self._record_config_change("toggle", {
            "old_enabled": self.config.rag.enabled,
            "new_enabled": enabled
        })
        
        return self.config.update_rag_config(enabled=enabled)
    
    def validate_config(self) -> Dict[str, Any]:
        """验证当前配置"""
        return self.config.rag.validate()
    
    def reload_config(self) -> bool:
        """重新加载配置文件"""
        try:
            old_config = asdict(self.config.rag)
            success = self.config.reload_config()
            
            if success:
                new_config = asdict(self.config.rag)
                self._record_config_change("reload", {
                    "old_config": old_config,
                    "new_config": new_config
                })
            
            return success
        except Exception as e:
            self.logger.error(f"配置重新加载失败: {e}")
            return False
    
    def export_config(self, file_path: Optional[str] = None) -> str:
        """导出当前配置到文件"""
        config_data = {
            "rag_config": asdict(self.config.rag),
            "export_time": datetime.now().isoformat(),
            "config_history": self.config_history[-10:]  # 只保留最近10次变更
        }
        
        if file_path is None:
            file_path = f"./data/rag_config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置导出成功: {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"配置导出失败: {e}")
            raise
    
    def import_config(self, file_path: str) -> bool:
        """从文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            rag_config_data = config_data.get("rag_config", {})
            
            # 验证导入的配置
            imported_config = RAGConfig(**rag_config_data)
            validation_result = imported_config.validate()
            
            if validation_result["errors"]:
                self.logger.error(f"导入的配置无效: {validation_result['errors']}")
                return False
            
            # 记录配置变更
            self._record_config_change("import", {
                "source_file": file_path,
                "old_config": asdict(self.config.rag),
                "new_config": rag_config_data
            })
            
            # 更新配置
            return self.config.update_rag_config(**rag_config_data)
            
        except Exception as e:
            self.logger.error(f"配置导入失败: {e}")
            return False
    
    def get_config_history(self, limit: int = 20) -> list:
        """获取配置变更历史"""
        return self.config_history[-limit:]
    
    def reset_to_defaults(self) -> bool:
        """重置为默认配置"""
        default_config = RAGConfig()
        
        self._record_config_change("reset", {
            "old_config": asdict(self.config.rag),
            "new_config": asdict(default_config)
        })
        
        return self.config.update_rag_config(**asdict(default_config))
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要信息"""
        return {
            "current_config": asdict(self.config.rag),
            "validation_result": self.validate_config(),
            "last_change": self.config_history[-1] if self.config_history else None,
            "total_changes": len(self.config_history)
        }
    
    def _record_config_change(self, change_type: str, details: Dict[str, Any]):
        """记录配置变更历史"""
        change_record = {
            "timestamp": datetime.now().isoformat(),
            "type": change_type,
            "details": details
        }
        
        self.config_history.append(change_record)
        
        # 只保留最近100次变更记录
        if len(self.config_history) > 100:
            self.config_history = self.config_history[-100:]
        
        self.logger.info(f"配置变更记录: {change_type}")


# 全局配置管理器实例
rag_config_manager = RAGConfigManager()