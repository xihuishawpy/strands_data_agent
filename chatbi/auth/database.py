"""
认证模块数据库操作工具
提供数据库连接、查询和事务管理功能
"""

import logging
import sqlite3
import pymysql
import psycopg2
from typing import Dict, List, Optional, Any, Union, Tuple
from contextlib import contextmanager
from datetime import datetime
import json

from .models import User, AllowedEmployee, UserPermission, UserSession, AuditLog
from .migrations.migration_manager import MigrationManager


class DatabaseError(Exception):
    """数据库操作异常"""
    pass


class AuthDatabase:
    """认证模块数据库操作类"""
    
    def __init__(self, database_config):
        """
        初始化数据库连接
        
        Args:
            database_config: 数据库配置对象
        """
        self.db_config = database_config
        self.logger = logging.getLogger(__name__)
        self._connection_pool = {}
        
        # 初始化迁移管理器
        self.migration_manager = MigrationManager(database_config)
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            if self.db_config.type == "sqlite":
                conn = sqlite3.connect(self.db_config.database, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                # 启用外键约束
                conn.execute("PRAGMA foreign_keys = ON")
                return conn
            elif self.db_config.type == "mysql":
                return pymysql.connect(
                    host=self.db_config.host,
                    port=self.db_config.port,
                    user=self.db_config.username,
                    password=self.db_config.password,
                    database=self.db_config.database,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False
                )
            elif self.db_config.type == "postgresql":
                return psycopg2.connect(
                    host=self.db_config.host,
                    port=self.db_config.port,
                    user=self.db_config.username,
                    password=self.db_config.password,
                    database=self.db_config.database
                )
            else:
                raise DatabaseError(f"不支持的数据库类型: {self.db_config.type}")
        except Exception as e:
            self.logger.error(f"数据库连接失败: {str(e)}")
            raise DatabaseError(f"数据库连接失败: {str(e)}")
    
    @contextmanager
    def get_cursor(self, commit=True):
        """获取数据库游标的上下文管理器"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"数据库操作失败: {str(e)}")
            raise DatabaseError(f"数据库操作失败: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询SQL"""
        with self.get_cursor(commit=False) as cursor:
            if self.db_config.type == "sqlite":
                cursor.execute(sql, params or ())
                return [dict(row) for row in cursor.fetchall()]
            else:
                cursor.execute(sql, params)
                return cursor.fetchall()
    
    def execute_update(self, sql: str, params: tuple = None) -> int:
        """执行更新SQL，返回影响的行数"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.rowcount
    
    def execute_insert(self, sql: str, params: tuple = None) -> Optional[str]:
        """执行插入SQL，返回插入的ID"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            if self.db_config.type == "sqlite":
                return str(cursor.lastrowid)
            elif self.db_config.type == "mysql":
                return str(cursor.lastrowid)
            elif self.db_config.type == "postgresql":
                # PostgreSQL需要使用RETURNING子句
                return None
    
    def _get_placeholder(self) -> str:
        """获取数据库占位符"""
        if self.db_config.type == "sqlite":
            return "?"
        else:
            return "%s"
    
    # 用户相关操作
    def create_user(self, user: User) -> bool:
        """创建用户"""
        placeholder = self._get_placeholder()
        sql = f"""
        INSERT INTO users (id, employee_id, password_hash, email, full_name, 
                          is_active, is_admin, created_at, updated_at, login_count)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 
                {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """
        
        params = (
            user.id, user.employee_id, user.password_hash, user.email, user.full_name,
            user.is_active, user.is_admin, user.created_at, user.updated_at, user.login_count
        )
        
        try:
            self.execute_insert(sql, params)
            self.logger.info(f"用户创建成功: {user.employee_id}")
            return True
        except Exception as e:
            self.logger.error(f"用户创建失败: {user.employee_id} - {str(e)}")
            return False
    
    def get_user_by_employee_id(self, employee_id: str) -> Optional[User]:
        """根据工号获取用户"""
        placeholder = self._get_placeholder()
        sql = f"SELECT * FROM users WHERE employee_id = {placeholder}"
        
        try:
            results = self.execute_query(sql, (employee_id,))
            if results:
                return User.from_dict(results[0])
            return None
        except Exception as e:
            self.logger.error(f"获取用户失败: {employee_id} - {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        placeholder = self._get_placeholder()
        sql = f"SELECT * FROM users WHERE id = {placeholder}"
        
        try:
            results = self.execute_query(sql, (user_id,))
            if results:
                return User.from_dict(results[0])
            return None
        except Exception as e:
            self.logger.error(f"获取用户失败: {user_id} - {str(e)}")
            return None
    
    def update_user_login_info(self, user_id: str) -> bool:
        """更新用户登录信息"""
        placeholder = self._get_placeholder()
        sql = f"""
        UPDATE users 
        SET last_login = {placeholder}, login_count = login_count + 1, updated_at = {placeholder}
        WHERE id = {placeholder}
        """
        
        now = datetime.now()
        try:
            affected = self.execute_update(sql, (now, now, user_id))
            return affected > 0
        except Exception as e:
            self.logger.error(f"更新用户登录信息失败: {user_id} - {str(e)}")
            return False
    
    # 允许工号相关操作
    def add_allowed_employee(self, allowed_employee: AllowedEmployee) -> bool:
        """添加允许注册的工号"""
        placeholder = self._get_placeholder()
        sql = f"""
        INSERT INTO allowed_employees (employee_id, added_by, added_at, description)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
        """
        
        params = (
            allowed_employee.employee_id, allowed_employee.added_by,
            allowed_employee.added_at, allowed_employee.description
        )
        
        try:
            self.execute_insert(sql, params)
            self.logger.info(f"允许工号添加成功: {allowed_employee.employee_id}")
            return True
        except Exception as e:
            self.logger.error(f"允许工号添加失败: {allowed_employee.employee_id} - {str(e)}")
            return False
    
    def is_employee_allowed(self, employee_id: str) -> bool:
        """检查工号是否允许注册"""
        placeholder = self._get_placeholder()
        sql = f"SELECT COUNT(*) as count FROM allowed_employees WHERE employee_id = {placeholder}"
        
        try:
            results = self.execute_query(sql, (employee_id,))
            return results[0]['count'] > 0
        except Exception as e:
            self.logger.error(f"检查允许工号失败: {employee_id} - {str(e)}")
            return False
    
    def get_allowed_employees(self) -> List[AllowedEmployee]:
        """获取所有允许注册的工号"""
        sql = "SELECT * FROM allowed_employees ORDER BY added_at DESC"
        
        try:
            results = self.execute_query(sql)
            return [AllowedEmployee.from_dict(row) for row in results]
        except Exception as e:
            self.logger.error(f"获取允许工号列表失败: {str(e)}")
            return []
    
    # 权限相关操作
    def create_user_permission(self, permission: UserPermission) -> bool:
        """创建用户权限"""
        placeholder = self._get_placeholder()
        sql = f"""
        INSERT INTO user_permissions (id, user_id, schema_name, permission_level, 
                                    granted_by, granted_at, expires_at, is_active)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 
                {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """
        
        params = (
            permission.id, permission.user_id, permission.schema_name,
            permission.permission_level.value, permission.granted_by,
            permission.granted_at, permission.expires_at, permission.is_active
        )
        
        try:
            self.execute_insert(sql, params)
            self.logger.info(f"用户权限创建成功: {permission.user_id} - {permission.schema_name}")
            return True
        except Exception as e:
            self.logger.error(f"用户权限创建失败: {permission.user_id} - {str(e)}")
            return False
    
    def get_user_permissions(self, user_id: str) -> List[UserPermission]:
        """获取用户权限列表"""
        placeholder = self._get_placeholder()
        sql = f"""
        SELECT * FROM user_permissions 
        WHERE user_id = {placeholder} AND is_active = 1
        ORDER BY granted_at DESC
        """
        
        try:
            results = self.execute_query(sql, (user_id,))
            return [UserPermission.from_dict(row) for row in results]
        except Exception as e:
            self.logger.error(f"获取用户权限失败: {user_id} - {str(e)}")
            return []
    
    def check_user_schema_permission(self, user_id: str, schema_name: str) -> bool:
        """检查用户是否有schema权限"""
        placeholder = self._get_placeholder()
        sql = f"""
        SELECT COUNT(*) as count FROM user_permissions 
        WHERE user_id = {placeholder} AND schema_name = {placeholder} 
        AND is_active = 1 AND (expires_at IS NULL OR expires_at > {placeholder})
        """
        
        try:
            results = self.execute_query(sql, (user_id, schema_name, datetime.now()))
            return results[0]['count'] > 0
        except Exception as e:
            self.logger.error(f"检查用户权限失败: {user_id} - {schema_name} - {str(e)}")
            return False
    
    # 会话相关操作
    def create_session(self, session: UserSession) -> bool:
        """创建用户会话"""
        placeholder = self._get_placeholder()
        sql = f"""
        INSERT INTO user_sessions (id, user_id, session_token, ip_address, user_agent,
                                 created_at, expires_at, last_activity, is_active)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """
        
        params = (
            session.id, session.user_id, session.session_token, session.ip_address,
            session.user_agent, session.created_at, session.expires_at,
            session.last_activity, session.is_active
        )
        
        try:
            self.execute_insert(sql, params)
            self.logger.info(f"会话创建成功: {session.user_id}")
            return True
        except Exception as e:
            self.logger.error(f"会话创建失败: {session.user_id} - {str(e)}")
            return False
    
    def get_session_by_token(self, token: str) -> Optional[UserSession]:
        """根据token获取会话"""
        placeholder = self._get_placeholder()
        sql = f"""
        SELECT * FROM user_sessions 
        WHERE session_token = {placeholder} AND is_active = 1
        """
        
        try:
            results = self.execute_query(sql, (token,))
            if results:
                return UserSession.from_dict(results[0])
            return None
        except Exception as e:
            self.logger.error(f"获取会话失败: {token} - {str(e)}")
            return None
    
    def update_session_activity(self, session_id: str) -> bool:
        """更新会话活动时间"""
        placeholder = self._get_placeholder()
        sql = f"""
        UPDATE user_sessions 
        SET last_activity = {placeholder}
        WHERE id = {placeholder}
        """
        
        try:
            affected = self.execute_update(sql, (datetime.now(), session_id))
            return affected > 0
        except Exception as e:
            self.logger.error(f"更新会话活动时间失败: {session_id} - {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        placeholder = self._get_placeholder()
        sql = f"""
        UPDATE user_sessions 
        SET is_active = 0 
        WHERE expires_at < {placeholder} AND is_active = 1
        """
        
        try:
            affected = self.execute_update(sql, (datetime.now(),))
            if affected > 0:
                self.logger.info(f"清理过期会话: {affected} 个")
            return affected
        except Exception as e:
            self.logger.error(f"清理过期会话失败: {str(e)}")
            return 0
    
    # 审计日志相关操作
    def create_audit_log(self, audit_log: AuditLog) -> bool:
        """创建审计日志"""
        placeholder = self._get_placeholder()
        
        # 处理details字段（JSON）
        details_json = json.dumps(audit_log.details) if audit_log.details else None
        
        sql = f"""
        INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id,
                              details, ip_address, user_agent, created_at)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """
        
        params = (
            audit_log.id, audit_log.user_id, audit_log.action, audit_log.resource_type,
            audit_log.resource_id, details_json, audit_log.ip_address,
            audit_log.user_agent, audit_log.created_at
        )
        
        try:
            self.execute_insert(sql, params)
            return True
        except Exception as e:
            self.logger.error(f"创建审计日志失败: {str(e)}")
            return False
    
    def get_audit_logs(self, user_id: str = None, limit: int = 100) -> List[AuditLog]:
        """获取审计日志"""
        placeholder = self._get_placeholder()
        
        if user_id:
            sql = f"""
            SELECT * FROM audit_logs 
            WHERE user_id = {placeholder}
            ORDER BY created_at DESC 
            LIMIT {placeholder}
            """
            params = (user_id, limit)
        else:
            sql = f"""
            SELECT * FROM audit_logs 
            ORDER BY created_at DESC 
            LIMIT {placeholder}
            """
            params = (limit,)
        
        try:
            results = self.execute_query(sql, params)
            logs = []
            for row in results:
                # 处理details字段
                if row.get('details'):
                    try:
                        row['details'] = json.loads(row['details'])
                    except json.JSONDecodeError:
                        row['details'] = {}
                else:
                    row['details'] = {}
                logs.append(AuditLog.from_dict(row))
            return logs
        except Exception as e:
            self.logger.error(f"获取审计日志失败: {str(e)}")
            return []
    
    # 数据库管理操作
    def initialize_database(self) -> bool:
        """初始化数据库（运行迁移）"""
        try:
            self.logger.info("开始初始化认证数据库...")
            
            # 运行迁移
            success = self.migration_manager.migrate_up()
            
            if success:
                self.logger.info("认证数据库初始化成功")
            else:
                self.logger.error("认证数据库初始化失败")
            
            return success
        except Exception as e:
            self.logger.error(f"认证数据库初始化异常: {str(e)}")
            return False
    
    def get_database_status(self) -> Dict[str, Any]:
        """获取数据库状态"""
        try:
            # 获取迁移状态
            migration_status = self.migration_manager.get_migration_status()
            
            # 获取表统计信息
            table_stats = {}
            tables = ['users', 'allowed_employees', 'user_permissions', 'user_sessions', 'audit_logs']
            
            for table in tables:
                try:
                    count_sql = f"SELECT COUNT(*) as count FROM {table}"
                    result = self.execute_query(count_sql)
                    table_stats[table] = result[0]['count']
                except Exception:
                    table_stats[table] = 0
            
            return {
                "database_type": self.db_config.type,
                "migration_status": migration_status,
                "table_statistics": table_stats,
                "connection_status": "connected"
            }
        except Exception as e:
            self.logger.error(f"获取数据库状态失败: {str(e)}")
            return {
                "database_type": self.db_config.type,
                "connection_status": "error",
                "error": str(e)
            }