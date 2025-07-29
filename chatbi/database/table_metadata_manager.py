"""
表元数据管理器
负责管理用户自定义的表注释、业务意义和字段注释
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from ..config import config

logger = logging.getLogger(__name__)

@dataclass
class ColumnMetadata:
    """字段元数据"""
    name: str
    business_name: str = ""  # 业务名称
    description: str = ""    # 字段描述
    business_meaning: str = ""  # 业务含义
    data_examples: List[str] = None  # 数据示例
    
    def __post_init__(self):
        if self.data_examples is None:
            self.data_examples = []

@dataclass
class TableMetadata:
    """表元数据"""
    table_name: str
    business_name: str = ""  # 业务名称
    description: str = ""    # 表描述
    business_meaning: str = ""  # 业务含义
    category: str = ""       # 业务分类
    columns: Dict[str, ColumnMetadata] = None  # 字段元数据
    
    def __post_init__(self):
        if self.columns is None:
            self.columns = {}

class TableMetadataManager:
    """表元数据管理器"""
    
    def __init__(self):
        self.metadata_file = Path(config.knowledge_base_path) / "table_metadata.json"
        self._metadata_cache: Dict[str, TableMetadata] = {}
        self._load_metadata()
    
    def get_table_metadata(self, table_name: str) -> Optional[TableMetadata]:
        """获取表的元数据"""
        return self._metadata_cache.get(table_name)
    
    def get_all_table_metadata(self) -> Dict[str, TableMetadata]:
        """获取所有表的元数据"""
        return self._metadata_cache.copy()
    
    def update_table_metadata(self, table_name: str, 
                            business_name: str = None,
                            description: str = None,
                            business_meaning: str = None,
                            category: str = None) -> bool:
        """更新表的元数据"""
        try:
            if table_name not in self._metadata_cache:
                self._metadata_cache[table_name] = TableMetadata(table_name=table_name)
            
            metadata = self._metadata_cache[table_name]
            
            if business_name is not None:
                metadata.business_name = business_name
            if description is not None:
                metadata.description = description
            if business_meaning is not None:
                metadata.business_meaning = business_meaning
            if category is not None:
                metadata.category = category
            
            self._save_metadata()
            logger.info(f"表 {table_name} 的元数据已更新")
            return True
            
        except Exception as e:
            logger.error(f"更新表元数据失败: {str(e)}")
            return False
    
    def update_column_metadata(self, table_name: str, column_name: str,
                             business_name: str = None,
                             description: str = None,
                             business_meaning: str = None,
                             data_examples: List[str] = None) -> bool:
        """更新字段的元数据"""
        try:
            if table_name not in self._metadata_cache:
                self._metadata_cache[table_name] = TableMetadata(table_name=table_name)
            
            table_metadata = self._metadata_cache[table_name]
            
            if column_name not in table_metadata.columns:
                table_metadata.columns[column_name] = ColumnMetadata(name=column_name)
            
            column_metadata = table_metadata.columns[column_name]
            
            if business_name is not None:
                column_metadata.business_name = business_name
            if description is not None:
                column_metadata.description = description
            if business_meaning is not None:
                column_metadata.business_meaning = business_meaning
            if data_examples is not None:
                column_metadata.data_examples = data_examples
            
            self._save_metadata()
            logger.info(f"表 {table_name} 字段 {column_name} 的元数据已更新")
            return True
            
        except Exception as e:
            logger.error(f"更新字段元数据失败: {str(e)}")
            return False
    
    def delete_table_metadata(self, table_name: str) -> bool:
        """删除表的元数据"""
        try:
            if table_name in self._metadata_cache:
                del self._metadata_cache[table_name]
                self._save_metadata()
                logger.info(f"表 {table_name} 的元数据已删除")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除表元数据失败: {str(e)}")
            return False
    
    def delete_column_metadata(self, table_name: str, column_name: str) -> bool:
        """删除字段的元数据"""
        try:
            if (table_name in self._metadata_cache and 
                column_name in self._metadata_cache[table_name].columns):
                del self._metadata_cache[table_name].columns[column_name]
                self._save_metadata()
                logger.info(f"表 {table_name} 字段 {column_name} 的元数据已删除")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除字段元数据失败: {str(e)}")
            return False
    
    def get_enhanced_schema_summary(self, base_schema: str) -> str:
        """获取增强的Schema摘要，包含用户自定义的业务信息"""
        try:
            # 检查是否有业务元数据需要增强
            has_business_metadata = False
            for table_name, metadata in self._metadata_cache.items():
                if any([metadata.business_name, metadata.description, 
                       metadata.business_meaning, metadata.category]):
                    has_business_metadata = True
                    break
                for col_metadata in metadata.columns.values():
                    if any([col_metadata.business_name, col_metadata.description,
                           col_metadata.business_meaning, col_metadata.data_examples]):
                        has_business_metadata = True
                        break
                if has_business_metadata:
                    break
            
            # 如果没有业务元数据，直接返回基础schema
            if not has_business_metadata:
                return base_schema
            
            # 重新构建完整的schema，将业务信息直接集成到基础schema中，避免重复
            enhanced_parts = []
            lines = base_schema.split('\n')
            
            current_table = None
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # 检测表名行
                if line.startswith('表名: '):
                    current_table = line.replace('表名: ', '').strip()
                    enhanced_parts.append(line)
                    
                    # 添加表级别的业务信息（紧跟在表名后面）
                    if current_table in self._metadata_cache:
                        metadata = self._metadata_cache[current_table]
                        if metadata.business_name:
                            enhanced_parts.append(f"  业务名称: {metadata.business_name}")
                        if metadata.description:
                            enhanced_parts.append(f"  描述: {metadata.description}")
                        if metadata.business_meaning:
                            enhanced_parts.append(f"  业务含义: {metadata.business_meaning}")
                        if metadata.category:
                            enhanced_parts.append(f"  业务分类: {metadata.category}")
                
                # 检测字段行并增强
                elif line.startswith('- ') and current_table and current_table in self._metadata_cache:
                    # 解析字段名
                    field_part = line[2:].split(' ')[0]  # 去掉"- "前缀，取第一个单词作为字段名
                    enhanced_parts.append(line)
                    
                    # 添加字段级别的业务信息（紧跟在字段后面）
                    metadata = self._metadata_cache[current_table]
                    if field_part in metadata.columns:
                        col_metadata = metadata.columns[field_part]
                        if col_metadata.business_name:
                            enhanced_parts.append(f"    业务名称: {col_metadata.business_name}")
                        if col_metadata.description:
                            enhanced_parts.append(f"    描述: {col_metadata.description}")
                        if col_metadata.business_meaning:
                            enhanced_parts.append(f"    业务含义: {col_metadata.business_meaning}")
                        if col_metadata.data_examples:
                            enhanced_parts.append(f"    数据示例: {', '.join(col_metadata.data_examples)}")
                else:
                    enhanced_parts.append(line)
                
                i += 1
            
            # 不再添加单独的"=== 业务信息增强 ==="部分，因为已经集成到基础schema中了
            return "\n".join(enhanced_parts)
            
        except Exception as e:
            logger.error(f"生成增强Schema摘要失败: {str(e)}")
            return base_schema
    
    def search_by_business_terms(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """根据业务术语搜索相关的表和字段"""
        try:
            results = []
            
            for table_name, metadata in self._metadata_cache.items():
                table_score = 0.0
                matched_fields = []
                
                # 搜索表级别的业务信息
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    
                    if keyword_lower in metadata.business_name.lower():
                        table_score += 3.0
                    if keyword_lower in metadata.description.lower():
                        table_score += 2.0
                    if keyword_lower in metadata.business_meaning.lower():
                        table_score += 2.0
                    if keyword_lower in metadata.category.lower():
                        table_score += 1.5
                
                # 搜索字段级别的业务信息
                for col_name, col_metadata in metadata.columns.items():
                    col_score = 0.0
                    
                    for keyword in keywords:
                        keyword_lower = keyword.lower()
                        
                        if keyword_lower in col_metadata.business_name.lower():
                            col_score += 3.0
                        if keyword_lower in col_metadata.description.lower():
                            col_score += 2.0
                        if keyword_lower in col_metadata.business_meaning.lower():
                            col_score += 2.0
                        
                        # 搜索数据示例
                        for example in col_metadata.data_examples:
                            if keyword_lower in example.lower():
                                col_score += 1.0
                    
                    if col_score > 0:
                        matched_fields.append({
                            "column_name": col_name,
                            "score": col_score,
                            "metadata": col_metadata
                        })
                        table_score += col_score * 0.5  # 字段匹配对表得分的贡献
                
                if table_score > 0:
                    results.append({
                        "table_name": table_name,
                        "score": table_score,
                        "table_metadata": metadata,
                        "matched_columns": matched_fields
                    })
            
            # 按得分排序
            results.sort(key=lambda x: x["score"], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"业务术语搜索失败: {str(e)}")
            return []
    
    def export_metadata(self) -> Dict[str, Any]:
        """导出所有元数据"""
        try:
            export_data = {}
            for table_name, metadata in self._metadata_cache.items():
                export_data[table_name] = {
                    "table_name": metadata.table_name,
                    "business_name": metadata.business_name,
                    "description": metadata.description,
                    "business_meaning": metadata.business_meaning,
                    "category": metadata.category,
                    "columns": {}
                }
                
                for col_name, col_metadata in metadata.columns.items():
                    export_data[table_name]["columns"][col_name] = {
                        "name": col_metadata.name,
                        "business_name": col_metadata.business_name,
                        "description": col_metadata.description,
                        "business_meaning": col_metadata.business_meaning,
                        "data_examples": col_metadata.data_examples
                    }
            
            return export_data
            
        except Exception as e:
            logger.error(f"导出元数据失败: {str(e)}")
            return {}
    
    def import_metadata(self, import_data: Dict[str, Any]) -> bool:
        """导入元数据"""
        try:
            for table_name, table_data in import_data.items():
                metadata = TableMetadata(
                    table_name=table_data.get("table_name", table_name),
                    business_name=table_data.get("business_name", ""),
                    description=table_data.get("description", ""),
                    business_meaning=table_data.get("business_meaning", ""),
                    category=table_data.get("category", "")
                )
                
                # 导入字段元数据
                columns_data = table_data.get("columns", {})
                for col_name, col_data in columns_data.items():
                    col_metadata = ColumnMetadata(
                        name=col_data.get("name", col_name),
                        business_name=col_data.get("business_name", ""),
                        description=col_data.get("description", ""),
                        business_meaning=col_data.get("business_meaning", ""),
                        data_examples=col_data.get("data_examples", [])
                    )
                    metadata.columns[col_name] = col_metadata
                
                self._metadata_cache[table_name] = metadata
            
            self._save_metadata()
            logger.info("元数据导入成功")
            return True
            
        except Exception as e:
            logger.error(f"导入元数据失败: {str(e)}")
            return False
    
    def _load_metadata(self):
        """从文件加载元数据"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for table_name, table_data in data.items():
                    metadata = TableMetadata(
                        table_name=table_data.get("table_name", table_name),
                        business_name=table_data.get("business_name", ""),
                        description=table_data.get("description", ""),
                        business_meaning=table_data.get("business_meaning", ""),
                        category=table_data.get("category", "")
                    )
                    
                    # 加载字段元数据
                    columns_data = table_data.get("columns", {})
                    for col_name, col_data in columns_data.items():
                        col_metadata = ColumnMetadata(
                            name=col_data.get("name", col_name),
                            business_name=col_data.get("business_name", ""),
                            description=col_data.get("description", ""),
                            business_meaning=col_data.get("business_meaning", ""),
                            data_examples=col_data.get("data_examples", [])
                        )
                        metadata.columns[col_name] = col_metadata
                    
                    self._metadata_cache[table_name] = metadata
                
                logger.info("表元数据加载成功")
        except Exception as e:
            logger.warning(f"加载表元数据失败: {str(e)}")
            self._metadata_cache = {}
    
    def _save_metadata(self):
        """保存元数据到文件"""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 转换为可序列化的格式
            save_data = {}
            for table_name, metadata in self._metadata_cache.items():
                save_data[table_name] = {
                    "table_name": metadata.table_name,
                    "business_name": metadata.business_name,
                    "description": metadata.description,
                    "business_meaning": metadata.business_meaning,
                    "category": metadata.category,
                    "columns": {}
                }
                
                for col_name, col_metadata in metadata.columns.items():
                    save_data[table_name]["columns"][col_name] = {
                        "name": col_metadata.name,
                        "business_name": col_metadata.business_name,
                        "description": col_metadata.description,
                        "business_meaning": col_metadata.business_meaning,
                        "data_examples": col_metadata.data_examples
                    }
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"保存表元数据失败: {str(e)}")

# 全局表元数据管理器实例
_metadata_manager: Optional[TableMetadataManager] = None

def get_table_metadata_manager() -> TableMetadataManager:
    """获取全局表元数据管理器实例"""
    global _metadata_manager
    
    if _metadata_manager is None:
        _metadata_manager = TableMetadataManager()
    
    return _metadata_manager