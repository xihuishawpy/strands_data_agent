"""
数据库连接器
支持 PostgreSQL、MySQL、SQLite 等数据库
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd

from ..config import config

logger = logging.getLogger(__name__)

class DatabaseConnector(ABC):
    """数据库连接器基类"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine: Optional[Engine] = None
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """连接数据库"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开数据库连接"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行查询"""
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        pass
    
    def get_table_names(self) -> List[str]:
        """获取所有表名（别名方法）"""
        return self.get_tables()
    
    @abstractmethod
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构信息"""
        pass
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.engine is not None

class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL连接器"""
    
    def connect(self) -> bool:
        """连接PostgreSQL数据库"""
        try:
            self.engine = create_engine(
                self.connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=config.web.debug
            )
            
            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._connected = True
            logger.info("PostgreSQL数据库连接成功")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"PostgreSQL连接失败: {str(e)}")
            self._connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.engine:
            self.engine.dispose()
            self._connected = False
            logger.info("PostgreSQL连接已断开")
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行查询"""
        if not self.is_connected:
            return {
                "success": False,
                "error": "数据库未连接",
                "data": []
            }
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                
                if result.returns_rows:
                    # 查询操作
                    columns = list(result.keys())
                    rows = [dict(zip(columns, row)) for row in result.fetchall()]
                    
                    return {
                        "success": True,
                        "data": rows,
                        "columns": columns,
                        "row_count": len(rows)
                    }
                else:
                    # 非查询操作
                    return {
                        "success": True,
                        "message": "操作执行成功",
                        "affected_rows": result.rowcount
                    }
                    
        except SQLAlchemyError as e:
            logger.error(f"查询执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        if not self.is_connected:
            return []
        
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except SQLAlchemyError as e:
            logger.error(f"获取表名失败: {str(e)}")
            return []
    
    def get_table_names(self) -> List[str]:
        """获取所有表名（别名方法）"""
        return self.get_tables()
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构信息"""
        if not self.is_connected:
            return {}
        
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            indexes = inspector.get_indexes(table_name)
            
            return {
                "table_name": table_name,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "default": col.get("default"),
                        "comment": col.get("comment")
                    }
                    for col in columns
                ],
                "primary_keys": primary_keys.get("constrained_columns", []),
                "foreign_keys": [
                    {
                        "columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    }
                    for fk in foreign_keys
                ],
                "indexes": [
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx["unique"]
                    }
                    for idx in indexes
                ]
            }
            
        except SQLAlchemyError as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return {}

class MySQLConnector(DatabaseConnector):
    """MySQL连接器"""
    
    def connect(self) -> bool:
        """连接MySQL数据库"""
        try:
            self.engine = create_engine(
                self.connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=config.web.debug
            )
            
            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._connected = True
            logger.info("MySQL数据库连接成功")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"MySQL连接失败: {str(e)}")
            self._connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.engine:
            self.engine.dispose()
            self._connected = False
            logger.info("MySQL连接已断开")
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行查询"""
        if not self.is_connected:
            return {
                "success": False,
                "error": "数据库未连接",
                "data": []
            }
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                
                if result.returns_rows:
                    columns = list(result.keys())
                    rows = [dict(zip(columns, row)) for row in result.fetchall()]
                    
                    return {
                        "success": True,
                        "data": rows,
                        "columns": columns,
                        "row_count": len(rows)
                    }
                else:
                    return {
                        "success": True,
                        "message": "操作执行成功",
                        "affected_rows": result.rowcount
                    }
                    
        except SQLAlchemyError as e:
            logger.error(f"查询执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        if not self.is_connected:
            return []
        
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except SQLAlchemyError as e:
            logger.error(f"获取表名失败: {str(e)}")
            return []
    
    def get_table_names(self) -> List[str]:
        """获取所有表名（别名方法）"""
        return self.get_tables()
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构信息"""
        if not self.is_connected:
            return {}
        
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            indexes = inspector.get_indexes(table_name)
            
            return {
                "table_name": table_name,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "default": col.get("default"),
                        "comment": col.get("comment")
                    }
                    for col in columns
                ],
                "primary_keys": primary_keys.get("constrained_columns", []),
                "foreign_keys": [
                    {
                        "columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    }
                    for fk in foreign_keys
                ],
                "indexes": [
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx["unique"]
                    }
                    for idx in indexes
                ]
            }
            
        except SQLAlchemyError as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return {}
    
    def update_column_comment(self, table_name: str, column_name: str, comment: str) -> bool:
        """更新字段备注"""
        if not self.is_connected:
            logger.error("数据库未连接")
            return False
        
        try:
            # 首先获取字段的当前信息
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            
            target_column = None
            for col in columns:
                if col["name"] == column_name:
                    target_column = col
                    break
            
            if not target_column:
                logger.error(f"字段 {column_name} 在表 {table_name} 中不存在")
                return False
            
            # 构建ALTER TABLE语句
            column_type = str(target_column["type"])
            nullable = "NULL" if target_column["nullable"] else "NOT NULL"
            default_clause = ""
            if target_column.get("default") is not None:
                default_value = target_column["default"]
                default_clause = f" DEFAULT {default_value}"
            
            # 转义备注中的单引号
            escaped_comment = comment.replace("'", "''")
            
            alter_sql = f"""
            ALTER TABLE `{table_name}` 
            MODIFY COLUMN `{column_name}` {column_type} {nullable}{default_clause} 
            COMMENT '{escaped_comment}'
            """
            
            with self.engine.begin() as conn:
                conn.execute(text(alter_sql))
            
            logger.info(f"成功更新表 {table_name} 字段 {column_name} 的备注")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"更新字段备注失败: {str(e)}")
            return False

class SQLiteConnector(DatabaseConnector):
    """SQLite连接器"""
    
    def connect(self) -> bool:
        """连接SQLite数据库"""
        try:
            self.engine = create_engine(
                self.connection_string,
                echo=config.web.debug
            )
            
            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._connected = True
            logger.info("SQLite数据库连接成功")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"SQLite连接失败: {str(e)}")
            self._connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.engine:
            self.engine.dispose()
            self._connected = False
            logger.info("SQLite连接已断开")
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行查询"""
        if not self.is_connected:
            return {
                "success": False,
                "error": "数据库未连接",
                "data": []
            }
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                
                if result.returns_rows:
                    columns = list(result.keys())
                    rows = [dict(zip(columns, row)) for row in result.fetchall()]
                    
                    return {
                        "success": True,
                        "data": rows,
                        "columns": columns,
                        "row_count": len(rows)
                    }
                else:
                    return {
                        "success": True,
                        "message": "操作执行成功",
                        "affected_rows": result.rowcount
                    }
                    
        except SQLAlchemyError as e:
            logger.error(f"查询执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        if not self.is_connected:
            return []
        
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except SQLAlchemyError as e:
            logger.error(f"获取表名失败: {str(e)}")
            return []
    
    def get_table_names(self) -> List[str]:
        """获取所有表名（别名方法）"""
        return self.get_tables()
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构信息"""
        if not self.is_connected:
            return {}
        
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            indexes = inspector.get_indexes(table_name)
            
            return {
                "table_name": table_name,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "default": col.get("default"),
                        "comment": col.get("comment")
                    }
                    for col in columns
                ],
                "primary_keys": primary_keys.get("constrained_columns", []),
                "foreign_keys": [
                    {
                        "columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    }
                    for fk in foreign_keys
                ],
                "indexes": [
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx["unique"]
                    }
                    for idx in indexes
                ]
            }
            
        except SQLAlchemyError as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return {}

def get_database_connector() -> DatabaseConnector:
    """获取数据库连接器实例"""
    db_type = config.database.type
    connection_string = config.database.connection_string
    
    if db_type == "postgresql":
        return PostgreSQLConnector(connection_string)
    elif db_type == "mysql":
        return MySQLConnector(connection_string)
    elif db_type == "sqlite":
        return SQLiteConnector(connection_string)
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")

# 全局数据库连接实例
_db_connector: Optional[DatabaseConnector] = None

def get_global_connector() -> DatabaseConnector:
    """获取全局数据库连接实例"""
    global _db_connector
    
    if _db_connector is None:
        _db_connector = get_database_connector()
        
        # 确保连接成功
        if not _db_connector.connect():
            logger.error("全局数据库连接器连接失败")
            # 即使连接失败也返回连接器，让上层处理错误
        else:
            logger.info("全局数据库连接器连接成功")
    
    # 检查连接状态，如果断开则重新连接
    if not _db_connector.is_connected:
        logger.warning("数据库连接已断开，尝试重新连接")
        if not _db_connector.connect():
            logger.error("数据库重新连接失败")
    
    return _db_connector 