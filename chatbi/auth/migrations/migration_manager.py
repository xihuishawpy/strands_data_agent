"""
数据库迁移管理器
负责执行和管理认证模块的数据库迁移
"""

import os
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import sqlite3
import pymysql
import psycopg2
from dataclasses import dataclass


@dataclass
class Migration:
    """迁移定义"""
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: str
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, database_config):
        """
        初始化迁移管理器
        
        Args:
            database_config: 数据库配置对象
        """
        self.db_config = database_config
        self.logger = logging.getLogger(__name__)
        self.migrations: Dict[str, Migration] = {}
        self._connection = None
        
        # 注册内置迁移
        self._register_builtin_migrations()
    
    def _register_builtin_migrations(self):
        """注册内置迁移"""
        from .create_auth_tables import create_auth_tables_migration
        self.register_migration(create_auth_tables_migration)
    
    def register_migration(self, migration: Migration):
        """注册迁移"""
        self.migrations[migration.version] = migration
        self.logger.info(f"注册迁移: {migration.version} - {migration.name}")
    
    def get_connection(self):
        """获取数据库连接"""
        if self._connection is None:
            if self.db_config.type == "sqlite":
                self._connection = sqlite3.connect(self.db_config.database)
                self._connection.row_factory = sqlite3.Row
            elif self.db_config.type == "mysql":
                self._connection = pymysql.connect(
                    host=self.db_config.host,
                    port=self.db_config.port,
                    user=self.db_config.username,
                    password=self.db_config.password,
                    database=self.db_config.database,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
            elif self.db_config.type == "postgresql":
                self._connection = psycopg2.connect(
                    host=self.db_config.host,
                    port=self.db_config.port,
                    user=self.db_config.username,
                    password=self.db_config.password,
                    database=self.db_config.database
                )
            else:
                raise ValueError(f"不支持的数据库类型: {self.db_config.type}")
        
        return self._connection
    
    def close_connection(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def _ensure_migration_table(self):
        """确保迁移记录表存在"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.db_config.type == "sqlite":
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS auth_migrations (
                version VARCHAR(50) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER DEFAULT 0
            )
            """
        elif self.db_config.type == "mysql":
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS auth_migrations (
                version VARCHAR(50) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        elif self.db_config.type == "postgresql":
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS auth_migrations (
                version VARCHAR(50) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER DEFAULT 0
            )
            """
        
        cursor.execute(create_table_sql)
        conn.commit()
        cursor.close()
    
    def get_applied_migrations(self) -> List[str]:
        """获取已应用的迁移列表"""
        self._ensure_migration_table()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT version FROM auth_migrations ORDER BY applied_at")
        
        if self.db_config.type == "sqlite":
            results = [row[0] for row in cursor.fetchall()]
        else:
            results = [row['version'] for row in cursor.fetchall()]
        
        cursor.close()
        return results
    
    def get_pending_migrations(self) -> List[Migration]:
        """获取待应用的迁移列表"""
        applied = set(self.get_applied_migrations())
        pending = []
        
        # 按版本排序
        sorted_migrations = sorted(self.migrations.items(), key=lambda x: x[0])
        
        for version, migration in sorted_migrations:
            if version not in applied:
                # 检查依赖是否已满足
                if all(dep in applied for dep in migration.dependencies):
                    pending.append(migration)
                else:
                    missing_deps = [dep for dep in migration.dependencies if dep not in applied]
                    self.logger.warning(f"迁移 {version} 的依赖未满足: {missing_deps}")
        
        return pending
    
    def apply_migration(self, migration: Migration) -> bool:
        """应用单个迁移"""
        start_time = datetime.now()
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            self.logger.info(f"开始应用迁移: {migration.version} - {migration.name}")
            
            # 执行迁移SQL
            if self.db_config.type == "sqlite":
                # SQLite需要逐条执行SQL语句
                for sql_statement in migration.up_sql.split(';'):
                    sql_statement = sql_statement.strip()
                    if sql_statement:
                        cursor.execute(sql_statement)
            else:
                cursor.execute(migration.up_sql)
            
            # 记录迁移
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            insert_sql = """
            INSERT INTO auth_migrations (version, name, description, applied_at, execution_time_ms)
            VALUES (%s, %s, %s, %s, %s)
            """
            
            if self.db_config.type == "sqlite":
                insert_sql = insert_sql.replace('%s', '?')
            
            cursor.execute(insert_sql, (
                migration.version,
                migration.name,
                migration.description,
                datetime.now(),
                execution_time
            ))
            
            conn.commit()
            cursor.close()
            
            self.logger.info(f"迁移应用成功: {migration.version} (耗时: {execution_time}ms)")
            return True
            
        except Exception as e:
            self.logger.error(f"迁移应用失败: {migration.version} - {str(e)}")
            conn.rollback()
            return False
    
    def rollback_migration(self, migration: Migration) -> bool:
        """回滚单个迁移"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            self.logger.info(f"开始回滚迁移: {migration.version} - {migration.name}")
            
            # 执行回滚SQL
            if self.db_config.type == "sqlite":
                for sql_statement in migration.down_sql.split(';'):
                    sql_statement = sql_statement.strip()
                    if sql_statement:
                        cursor.execute(sql_statement)
            else:
                cursor.execute(migration.down_sql)
            
            # 删除迁移记录
            delete_sql = "DELETE FROM auth_migrations WHERE version = %s"
            if self.db_config.type == "sqlite":
                delete_sql = delete_sql.replace('%s', '?')
            
            cursor.execute(delete_sql, (migration.version,))
            
            conn.commit()
            cursor.close()
            
            self.logger.info(f"迁移回滚成功: {migration.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"迁移回滚失败: {migration.version} - {str(e)}")
            conn.rollback()
            return False
    
    def migrate_up(self, target_version: Optional[str] = None) -> bool:
        """向上迁移到指定版本（或最新版本）"""
        pending = self.get_pending_migrations()
        
        if target_version:
            # 过滤到目标版本
            pending = [m for m in pending if m.version <= target_version]
        
        if not pending:
            self.logger.info("没有待应用的迁移")
            return True
        
        success_count = 0
        for migration in pending:
            if self.apply_migration(migration):
                success_count += 1
            else:
                self.logger.error(f"迁移失败，停止后续迁移: {migration.version}")
                break
        
        self.logger.info(f"成功应用 {success_count}/{len(pending)} 个迁移")
        return success_count == len(pending)
    
    def migrate_down(self, target_version: str) -> bool:
        """向下迁移到指定版本"""
        applied = self.get_applied_migrations()
        
        # 找到需要回滚的迁移（按版本倒序）
        to_rollback = []
        for version in reversed(applied):
            if version > target_version:
                if version in self.migrations:
                    to_rollback.append(self.migrations[version])
                else:
                    self.logger.error(f"找不到迁移定义: {version}")
                    return False
        
        if not to_rollback:
            self.logger.info("没有需要回滚的迁移")
            return True
        
        success_count = 0
        for migration in to_rollback:
            if self.rollback_migration(migration):
                success_count += 1
            else:
                self.logger.error(f"迁移回滚失败，停止后续回滚: {migration.version}")
                break
        
        self.logger.info(f"成功回滚 {success_count}/{len(to_rollback)} 个迁移")
        return success_count == len(to_rollback)
    
    def get_migration_status(self) -> Dict[str, Any]:
        """获取迁移状态"""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        return {
            "total_migrations": len(self.migrations),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_migrations": applied,
            "pending_migrations": [m.version for m in pending],
            "latest_applied": applied[-1] if applied else None
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close_connection()