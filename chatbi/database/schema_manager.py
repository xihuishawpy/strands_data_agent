"""
Schema管理器
负责数据库Schema的提取、缓存和管理，支持用户权限过滤
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from .connectors import get_global_connector
from ..config import config

logger = logging.getLogger(__name__)

class SchemaManager:
    """数据库Schema管理器"""
    
    def __init__(self, user_id: Optional[str] = None):
        """
        初始化Schema管理器
        
        Args:
            user_id: 用户ID，如果提供则启用权限过滤
        """
        self.user_id = user_id
        self.connector = get_global_connector()
        self.cache_file = Path(config.knowledge_base_path) / "schema_cache.json"
        self.cache_ttl = config.schema_cache_ttl
        self._schema_cache = {}
        self._metadata_manager = None  # 延迟初始化避免循环导入
        self._permission_filter = None  # 权限过滤器
        
        # 如果提供了用户ID，则设置用户特定的连接器和权限过滤器
        if user_id:
            self._setup_user_components()
        
        self._load_cache()
    
    def _setup_user_components(self):
        """设置用户特定的组件"""
        try:
            from ..auth.chatbi_integration import get_integration_adapter
            
            integration = get_integration_adapter()
            
            # 设置用户特定的数据库连接器
            user_connector = integration.create_user_database_connector(self.user_id)
            if user_connector:
                self.connector = user_connector
                logger.info(f"为用户 {self.user_id} 设置了特定的数据库连接器")
            
            # 设置权限过滤器
            self._permission_filter = integration.permission_filter
            
        except Exception as e:
            logger.error(f"设置用户Schema管理器组件失败: {str(e)}")
            # 继续使用默认组件
    
    def get_all_tables(self, force_refresh: bool = False) -> List[str]:
        """
        获取所有表名（带用户权限过滤）
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            List[str]: 用户有权限访问的表名列表
        """
        cache_key = f"all_tables_{self.user_id or 'global'}"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            return self._schema_cache[cache_key]["data"]
        
        try:
            # 获取所有表名
            all_tables = self.connector.get_tables()
            
            # 如果有用户ID和权限过滤器，进行权限过滤
            if self.user_id and self._permission_filter:
                filtered_tables = self._filter_tables_by_permission(all_tables)
                self._update_cache(cache_key, filtered_tables)
                return filtered_tables
            else:
                self._update_cache(cache_key, all_tables)
                return all_tables
                
        except Exception as e:
            logger.error(f"获取表名失败: {str(e)}")
            return []
    
    def _filter_tables_by_permission(self, tables: List[str]) -> List[str]:
        """
        根据用户权限过滤表名列表
        
        Args:
            tables: 所有表名列表
            
        Returns:
            List[str]: 用户有权限访问的表名列表
        """
        try:
            # 提取表名中的schema信息
            schemas_in_tables = set()
            for table in tables:
                if '.' in table:
                    schema_name = table.split('.')[0]
                    schemas_in_tables.add(schema_name)
            
            # 获取用户可访问的schema
            accessible_schemas = self._permission_filter.filter_schemas(
                self.user_id, list(schemas_in_tables)
            )
            
            # 过滤表名
            filtered_tables = []
            for table in tables:
                if '.' in table:
                    schema_name = table.split('.')[0]
                    if schema_name in accessible_schemas:
                        filtered_tables.append(table)
                else:
                    # 没有schema前缀的表，默认允许访问
                    filtered_tables.append(table)
            
            logger.info(f"用户 {self.user_id} 可访问 {len(filtered_tables)}/{len(tables)} 个表")
            return filtered_tables
            
        except Exception as e:
            logger.error(f"过滤表名权限异常: {str(e)}")
            return tables  # 出错时返回所有表
    
    def get_table_schema(self, table_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取表结构信息
        
        Args:
            table_name: 表名
            force_refresh: 是否强制刷新缓存
            
        Returns:
            Dict[str, Any]: 表结构信息
        """
        cache_key = f"table_schema_{table_name}"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            return self._schema_cache[cache_key]["data"]
        
        try:
            schema = self.connector.get_table_schema(table_name)
            self._update_cache(cache_key, schema)
            return schema
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return {}
    
    def get_database_schema(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取完整的数据库Schema（带用户权限过滤）
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            Dict[str, Any]: 用户有权限访问的数据库Schema
        """
        cache_key = f"database_schema_{self.user_id or 'global'}"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            return self._schema_cache[cache_key]["data"]
        
        try:
            # 获取用户可访问的表名
            tables = self.get_all_tables(force_refresh)
            
            # 获取每个表的结构
            schema = {
                "database_type": config.database.type,
                "tables": {},
                "relationships": [],
                "user_id": self.user_id,
                "permission_filtered": bool(self.user_id)
            }
            
            for table_name in tables:
                table_schema = self.get_table_schema(table_name, force_refresh)
                if table_schema:
                    schema["tables"][table_name] = table_schema
            
            # 分析表关系（只包含用户可访问的表）
            schema["relationships"] = self._analyze_relationships(schema["tables"])
            
            self._update_cache(cache_key, schema)
            return schema
            
        except Exception as e:
            logger.error(f"获取数据库Schema失败: {str(e)}")
            return {}
    
    def search_relevant_tables(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        根据关键词搜索相关的表
        
        Args:
            keywords: 搜索关键词列表
            
        Returns:
            List[Dict[str, Any]]: 相关表信息
        """
        try:
            schema = self.get_database_schema()
            relevant_tables = []
            
            for table_name, table_info in schema.get("tables", {}).items():
                relevance_score = self._calculate_table_relevance(table_info, keywords)
                if relevance_score > 0:
                    relevant_tables.append({
                        "table_name": table_name,
                        "relevance_score": relevance_score,
                        "schema": table_info
                    })
            
            # 按相关性得分排序
            relevant_tables.sort(key=lambda x: x["relevance_score"], reverse=True)
            return relevant_tables
            
        except Exception as e:
            logger.error(f"搜索相关表失败: {str(e)}")
            return []
    
    def get_schema_summary(self) -> str:
        """
        获取Schema的文本摘要，用于LLM理解（带用户权限过滤）
        
        Returns:
            str: 用户有权限访问的Schema摘要文本
        """
        try:
            schema = self.get_database_schema()
            summary_parts = []
            
            summary_parts.append(f"数据库类型: {schema.get('database_type', '未知')}")
            summary_parts.append(f"表数量: {len(schema.get('tables', {}))}")
            
            # 如果启用了权限过滤，添加权限说明
            if schema.get("permission_filtered") and self.user_id:
                summary_parts.append(f"权限过滤: 已为用户 {self.user_id} 过滤")
                
                # 获取用户可访问的schema列表
                if self._permission_filter:
                    try:
                        all_schemas = self._extract_schemas_from_tables(schema.get("tables", {}).keys())
                        accessible_schemas = self._permission_filter.filter_schemas(self.user_id, all_schemas)
                        if accessible_schemas:
                            summary_parts.append(f"可访问的schema: {', '.join(accessible_schemas)}")
                    except Exception as e:
                        logger.warning(f"获取可访问schema列表失败: {str(e)}")
            
            summary_parts.append("")
            
            # 表信息摘要
            for table_name, table_info in schema.get("tables", {}).items():
                summary_parts.append(f"表名: {table_name}")
                
                # 字段信息
                columns = table_info.get("columns", [])
                if columns:
                    summary_parts.append("  字段:")
                    for col in columns:
                        col_desc = f"    - {col['name']} ({col['type']})"
                        if not col.get('nullable', True):
                            col_desc += " NOT NULL"
                        if col.get('comment'):
                            col_desc += f" -- {col['comment']}"
                        summary_parts.append(col_desc)
                
                # 主键信息
                primary_keys = table_info.get("primary_keys", [])
                if primary_keys:
                    summary_parts.append(f"  主键: {', '.join(primary_keys)}")
                
                # 外键信息
                foreign_keys = table_info.get("foreign_keys", [])
                if foreign_keys:
                    summary_parts.append("  外键:")
                    for fk in foreign_keys:
                        fk_desc = f"    - {', '.join(fk['columns'])} -> {fk['referred_table']}.{', '.join(fk['referred_columns'])}"
                        summary_parts.append(fk_desc)
                
                summary_parts.append("")
            
            # 表关系摘要
            relationships = schema.get("relationships", [])
            if relationships:
                summary_parts.append("表关系:")
                for rel in relationships:
                    rel_desc = f"  - {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}"
                    summary_parts.append(rel_desc)
            
            base_summary = "\n".join(summary_parts)
            
            # 使用表元数据管理器增强Schema摘要
            if self._metadata_manager is None:
                from .table_metadata_manager import get_table_metadata_manager
                self._metadata_manager = get_table_metadata_manager()
            
            enhanced_summary = self._metadata_manager.get_enhanced_schema_summary(base_summary)
            
            # 如果启用了权限过滤，添加权限提醒
            if schema.get("permission_filtered") and self.user_id:
                permission_note = "\n\n注意: 以上信息已根据用户权限进行过滤，只显示您有权限访问的数据库对象。"
                enhanced_summary += permission_note
            
            return enhanced_summary
            
        except Exception as e:
            logger.error(f"生成Schema摘要失败: {str(e)}")
            return "无法获取数据库Schema信息"
    
    def _extract_schemas_from_tables(self, table_names) -> List[str]:
        """从表名列表中提取schema名称"""
        schemas = set()
        for table_name in table_names:
            if '.' in table_name:
                schema_name = table_name.split('.')[0]
                schemas.add(schema_name)
        return list(schemas)
    
    def refresh_cache(self):
        """刷新所有缓存"""
        logger.info("开始刷新Schema缓存")
        self._schema_cache.clear()
        self.get_database_schema(force_refresh=True)
        self._save_cache()
        logger.info("Schema缓存刷新完成")
    
    def _analyze_relationships(self, tables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析表之间的关系"""
        relationships = []
        
        for table_name, table_info in tables.items():
            foreign_keys = table_info.get("foreign_keys", [])
            for fk in foreign_keys:
                for i, col in enumerate(fk["columns"]):
                    relationships.append({
                        "from_table": table_name,
                        "from_column": col,
                        "to_table": fk["referred_table"],
                        "to_column": fk["referred_columns"][i] if i < len(fk["referred_columns"]) else fk["referred_columns"][0]
                    })
        
        return relationships
    
    def _calculate_table_relevance(self, table_info: Dict[str, Any], keywords: List[str]) -> float:
        """计算表与关键词的相关性得分"""
        score = 0.0
        table_name = table_info.get("table_name", "").lower()
        
        for keyword in keywords:
            if keyword is None:
                continue
            keyword = str(keyword).lower()
            
            # 表名匹配
            if keyword in table_name:
                score += 3.0
            
            # 字段名匹配
            for col in table_info.get("columns", []):
                col_name = col.get("name", "").lower()
                if keyword in col_name:
                    score += 2.0
                
                # 字段注释匹配
                col_comment = col.get("comment", "").lower()
                if col_comment and keyword in col_comment:
                    score += 1.5
        
        return score
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._schema_cache:
            return False
        
        cache_entry = self._schema_cache[cache_key]
        current_time = time.time()
        return (current_time - cache_entry["timestamp"]) < self.cache_ttl
    
    def _update_cache(self, cache_key: str, data: Any):
        """更新缓存"""
        self._schema_cache[cache_key] = {
            "data": data,
            "timestamp": time.time()
        }
        self._save_cache()
    
    def _load_cache(self):
        """从文件加载缓存"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self._schema_cache = json.load(f)
                logger.info("Schema缓存加载成功")
        except Exception as e:
            logger.warning(f"加载Schema缓存失败: {str(e)}")
            self._schema_cache = {}
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._schema_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存Schema缓存失败: {str(e)}")

# 全局Schema管理器实例
_schema_manager: Optional[SchemaManager] = None

def get_schema_manager(user_id: Optional[str] = None) -> SchemaManager:
    """
    获取Schema管理器实例
    
    Args:
        user_id: 用户ID，如果提供则返回带权限过滤的管理器
        
    Returns:
        SchemaManager: Schema管理器实例
    """
    if user_id:
        # 为特定用户创建新的管理器实例
        return SchemaManager(user_id=user_id)
    
    # 返回全局管理器实例
    global _schema_manager
    
    if _schema_manager is None:
        _schema_manager = SchemaManager()
    
    return _schema_manager

def create_user_schema_manager(user_id: str) -> SchemaManager:
    """
    为特定用户创建Schema管理器
    
    Args:
        user_id: 用户ID
        
    Returns:
        SchemaManager: 用户特定的Schema管理器
    """
    return SchemaManager(user_id=user_id) 