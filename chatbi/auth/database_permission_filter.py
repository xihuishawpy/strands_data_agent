"""
数据库权限过滤器
实现SQL查询权限验证、schema访问控制和用户特定数据库连接
"""

import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple
from dataclasses import dataclass

from .models import User, PermissionLevel
from .permission_manager import PermissionManager
from .database import AuthDatabase
from .config import get_permission_config


@dataclass
class ValidationResult:
    """SQL权限验证结果"""
    valid: bool
    message: str = ""
    errors: List[str] = None
    allowed_schemas: List[str] = None
    blocked_schemas: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.allowed_schemas is None:
            self.allowed_schemas = []
        if self.blocked_schemas is None:
            self.blocked_schemas = []


class DatabasePermissionFilter:
    """数据库权限过滤器类"""
    
    def __init__(self, permission_manager: PermissionManager, auth_database: AuthDatabase):
        """
        初始化数据库权限过滤器
        
        Args:
            permission_manager: 权限管理器实例
            auth_database: 认证数据库实例
        """
        self.permission_manager = permission_manager
        self.auth_database = auth_database
        self.permission_config = get_permission_config()
        self.logger = logging.getLogger(__name__)
        
        # SQL解析相关的正则表达式
        self._init_sql_patterns()
    
    def _init_sql_patterns(self):
        """初始化SQL解析正则表达式"""
        # 匹配表名的模式（支持schema.table格式）
        self.table_pattern = re.compile(
            r'\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+(?:`?(\w+)`?\.)?`?(\w+)`?',
            re.IGNORECASE
        )
        
        # 匹配schema名称的模式 - 修复以支持多个schema
        self.schema_pattern = re.compile(
            r'(?:`([^`]+)`|\[([^\]]+)\]|(\w+))\.(?:`\w+`|\[\w+\]|\w+)',
            re.IGNORECASE
        )
        
        # 匹配危险操作的模式
        self.dangerous_operations = re.compile(
            r'\b(?:DROP|CREATE|ALTER|TRUNCATE|DELETE|INSERT|UPDATE)\b',
            re.IGNORECASE
        )
        
        # 匹配系统表的模式
        self.system_tables = re.compile(
            r'\b(?:information_schema|mysql|performance_schema|sys|pg_catalog)\.', 
            re.IGNORECASE
        ) 
   
    def filter_schemas(self, user_id: str, available_schemas: List[str]) -> List[str]:
        """
        根据用户权限过滤可用的schema列表
        
        Args:
            user_id: 用户ID
            available_schemas: 可用的schema列表
            
        Returns:
            List[str]: 用户有权限访问的schema列表
        """
        try:
            self.logger.info(f"开始过滤用户schema权限: {user_id}")
            self.logger.info(f"可用的schema列表: {available_schemas}")
            
            # 1. 获取用户信息
            user = self.auth_database.get_user_by_id(user_id)
            if not user or not user.is_active:
                self.logger.warning(f"用户不存在或未激活: {user_id}")
                return []
            
            # 2. 如果schema隔离未启用，返回所有schema
            if not self.permission_config.schema_isolation_enabled:
                self.logger.info("Schema隔离未启用，返回所有schema")
                return available_schemas
            
            # 3. 获取用户可访问的schema
            accessible_schemas = set()
            
            # 3.1 添加公共schema
            for schema in available_schemas:
                if schema in self.permission_config.public_schemas:
                    accessible_schemas.add(schema)
            
            # 3.2 管理员权限检查
            if user.is_admin and self.permission_config.inherit_admin_permissions:
                for schema in available_schemas:
                    if schema in self.permission_config.admin_schemas:
                        accessible_schemas.add(schema)
            
            # 3.3 检查用户特定权限
            user_permissions = self.permission_manager.get_user_permissions(user_id)
            self.logger.info(f"获取到用户权限数量: {len(user_permissions)}")
            
            for permission in user_permissions:
                self.logger.info(f"检查权限: schema={permission.schema_name}, valid={permission.is_valid()}, active={permission.is_active}")
                self.logger.info(f"schema '{permission.schema_name}' 是否在可用列表中: {permission.schema_name in available_schemas}")
                if permission.is_valid() and permission.schema_name in available_schemas:
                    accessible_schemas.add(permission.schema_name)
                    self.logger.info(f"添加可访问schema: {permission.schema_name}")
                elif permission.is_valid():
                    self.logger.warning(f"权限有效但schema不在可用列表中: {permission.schema_name}")
            
            # 3.4 添加默认schema权限
            for schema in self.permission_config.default_schema_access:
                if schema in available_schemas:
                    accessible_schemas.add(schema)
            
            result = list(accessible_schemas)
            self.logger.info(f"用户 {user_id} 可访问的schema: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"过滤schema权限异常: {user_id} - {str(e)}")
            return []
    
    def validate_sql_permissions(self, user_id: str, sql_query: str) -> ValidationResult:
        """
        验证SQL查询的权限
        
        Args:
            user_id: 用户ID
            sql_query: SQL查询语句
            
        Returns:
            ValidationResult: 验证结果
        """
        try:
            self.logger.info(f"开始验证SQL权限: {user_id}")
            
            # 1. 基本参数验证
            if not user_id or not sql_query:
                return ValidationResult(
                    valid=False,
                    message="用户ID和SQL查询不能为空",
                    errors=["invalid_input"]
                )
            
            # 2. 获取用户信息
            user = self.auth_database.get_user_by_id(user_id)
            if not user:
                return ValidationResult(
                    valid=False,
                    message="用户不存在",
                    errors=["user_not_found"]
                )
            
            if not user.is_active:
                return ValidationResult(
                    valid=False,
                    message="用户未激活",
                    errors=["user_inactive"]
                )
            
            # 3. 如果权限检查未启用，直接通过
            if not self.permission_config.strict_permission_check:
                return ValidationResult(valid=True, message="权限检查已禁用")
            
            # 4. 解析SQL中涉及的schema
            schemas_in_query = self._extract_schemas_from_sql(sql_query)
            
            # 5. 检查是否包含系统表访问
            if self._is_system_table_access(sql_query):
                if not user.is_admin:
                    return ValidationResult(
                        valid=False,
                        message="不能访问系统表",
                        errors=["system_table_access_denied"]
                    )
            
            # 6. 确定所需权限级别（默认为读权限）
            actual_required_level = self._determine_required_permission_level(sql_query, "read")
            
            # 7. 验证每个schema的权限
            allowed_schemas = []
            blocked_schemas = []
            
            for schema in schemas_in_query:
                if self._check_schema_permission(user_id, schema, actual_required_level, user.is_admin):
                    allowed_schemas.append(schema)
                else:
                    blocked_schemas.append(schema)
            
            # 8. 生成验证结果
            if blocked_schemas:
                return ValidationResult(
                    valid=False,
                    message=f"用户没有权限访问以下schema: {', '.join(blocked_schemas)}",
                    errors=["schema_access_denied"],
                    allowed_schemas=allowed_schemas,
                    blocked_schemas=blocked_schemas
                )
            
            return ValidationResult(
                valid=True,
                message="SQL权限验证通过",
                allowed_schemas=allowed_schemas
            )
            
        except Exception as e:
            self.logger.error(f"验证SQL权限异常: {user_id} - {str(e)}")
            return ValidationResult(
                valid=False,
                message="权限验证过程中发生错误",
                errors=["internal_error"]
            )
    
    def _extract_schemas_from_sql(self, sql_query: str) -> Set[str]:
        """从SQL查询中提取schema名称"""
        schemas = set()
        
        try:
            # 清理SQL语句
            cleaned_sql = self._clean_sql(sql_query)
            
            # 查找所有schema.table模式
            schema_matches = self.schema_pattern.findall(cleaned_sql)
            for match in schema_matches:
                # schema_pattern 返回的是元组，需要处理
                if isinstance(match, tuple):
                    # 取第一个非空的匹配项作为schema名称
                    for schema in match:
                        if schema and schema.lower() not in ['information_schema', 'mysql', 'performance_schema', 'sys', 'pg_catalog']:
                            schemas.add(schema)
                            break  # 只取第一个匹配的schema
                elif match and match.lower() not in ['information_schema', 'mysql', 'performance_schema', 'sys', 'pg_catalog']:
                    schemas.add(match)
            
            # 如果没有找到明确的schema，检查是否有表名（可能使用默认schema）
            if not schemas:
                table_matches = self.table_pattern.findall(cleaned_sql)
                for schema, table in table_matches:
                    if schema:
                        schemas.add(schema)
            
        except Exception as e:
            self.logger.error(f"解析SQL中的schema异常: {str(e)}")
        
        return schemas
    
    def _clean_sql(self, sql_query: str) -> str:
        """清理SQL语句，移除注释和多余空格"""
        # 移除单行注释
        sql_query = re.sub(r'--.*\n', '', sql_query, flags=re.MULTILINE)
        
        # 移除多行注释
        sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
        
        # 移除多余空格
        sql_query = re.sub(r'\s+', ' ', sql_query).strip()
        
        return sql_query
    
    def _is_system_table_access(self, sql_query: str) -> bool:
        """检查SQL是否包含系统表访问"""
        return bool(self.system_tables.search(sql_query))
    
    def _is_write_operation(self, sql_query: str) -> bool:
        """检查SQL是否为写操作"""
        cleaned_sql = sql_query.strip().upper()
        write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TRUNCATE']
        return any(keyword in cleaned_sql for keyword in write_keywords)
    
    def _determine_required_permission_level(self, sql_query: str, default_level: str) -> str:
        """根据SQL操作类型确定所需权限级别"""
        cleaned_sql = sql_query.strip().upper()
        
        # DDL操作需要admin权限
        if any(op in cleaned_sql for op in ['CREATE', 'DROP', 'ALTER', 'TRUNCATE']):
            return "admin"
        
        # DML写操作需要write权限
        if any(op in cleaned_sql for op in ['INSERT', 'UPDATE', 'DELETE']):
            return "write"
        
        # 默认为读权限
        return default_level
    
    def _check_schema_permission(self, user_id: str, schema_name: str, 
                               required_level: str, is_admin: bool) -> bool:
        """检查用户对schema的权限"""
        # 1. 检查是否为公共schema
        if schema_name in self.permission_config.public_schemas:
            return True
        
        # 2. 管理员权限检查
        if is_admin and self.permission_config.inherit_admin_permissions:
            if schema_name in self.permission_config.admin_schemas:
                return True
        
        # 3. 检查用户特定权限
        return self.permission_manager.check_schema_access(
            user_id, schema_name, required_level
        )


class UserSpecificDatabaseConnector:
    """用户特定的数据库连接器包装器"""
    
    def __init__(self, base_connector, permission_filter: DatabasePermissionFilter, user_id: str):
        """
        初始化用户特定数据库连接器
        
        Args:
            base_connector: 基础数据库连接器
            permission_filter: 权限过滤器
            user_id: 用户ID
        """
        self.base_connector = base_connector
        self.permission_filter = permission_filter
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """连接数据库（委托给基础连接器）"""
        try:
            if hasattr(self.base_connector, 'connect'):
                return self.base_connector.connect()
            else:
                # 如果基础连接器没有connect方法，假设已连接
                return True
        except Exception as e:
            self.logger.error(f"用户特定数据库连接器连接失败: {self.user_id} - {str(e)}")
            return False
    
    @property
    def is_connected(self) -> bool:
        """检查数据库连接状态（委托给基础连接器）"""
        try:
            if hasattr(self.base_connector, 'is_connected'):
                return self.base_connector.is_connected
            else:
                # 如果基础连接器没有is_connected属性，假设已连接
                return True
        except Exception as e:
            self.logger.error(f"检查用户特定数据库连接状态失败: {self.user_id} - {str(e)}")
            return False
    
    def get_schemas(self) -> List[str]:
        """获取用户可访问的schema列表"""
        try:
            # 1. 获取所有schema
            if hasattr(self.base_connector, 'get_schemas'):
                all_schemas = self.base_connector.get_schemas()
            else:
                # 如果基础连接器没有get_schemas方法，使用默认的schema列表
                # 这里包含常见的MySQL schema
                all_schemas = ['root', 'information_schema', 'mysql', 'performance_schema', 'sys']
                self.logger.info(f"基础连接器没有get_schemas方法，使用默认schema列表: {all_schemas}")
            
            self.logger.info(f"获取到的所有schema: {all_schemas}")
            
            # 2. 根据权限过滤schema
            return self.permission_filter.filter_schemas(self.user_id, all_schemas)
            
        except Exception as e:
            self.logger.error(f"获取用户可访问schema异常: {self.user_id} - {str(e)}")
            return []
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> Any:
        """
        执行查询（带权限检查）
        
        Args:
            query: SQL查询语句
            params: 查询参数（可选）
            
        Returns:
            查询结果
        """
        try:
            # 1. 权限验证
            validation_result = self.permission_filter.validate_sql_permissions(
                self.user_id, query
            )
            
            if not validation_result.valid:
                self.logger.warning(f"用户 {self.user_id} SQL权限验证失败: {validation_result.message}")
                raise PermissionError(validation_result.message)
            
            # 2. 执行查询
            if hasattr(self.base_connector, 'execute_query'):
                return self.base_connector.execute_query(query, params)
            else:
                # 模拟执行查询
                return [{"result": "query executed"}]
            
        except PermissionError:
            raise
        except Exception as e:
            self.logger.error(f"用户特定查询执行异常: {self.user_id} - {str(e)}")
            raise
    
    def get_tables(self) -> List[str]:
        """获取表列表（委托给基础连接器）"""
        try:
            if hasattr(self.base_connector, 'get_tables'):
                return self.base_connector.get_tables()
            else:
                return []
        except Exception as e:
            self.logger.error(f"获取表列表异常: {self.user_id} - {str(e)}")
            return []
    
    def get_table_names(self) -> List[str]:
        """获取表名列表（委托给基础连接器）"""
        try:
            if hasattr(self.base_connector, 'get_table_names'):
                return self.base_connector.get_table_names()
            elif hasattr(self.base_connector, 'get_tables'):
                return self.base_connector.get_tables()
            else:
                return []
        except Exception as e:
            self.logger.error(f"获取表名列表异常: {self.user_id} - {str(e)}")
            return []
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构（委托给基础连接器）"""
        try:
            if hasattr(self.base_connector, 'get_table_schema'):
                return self.base_connector.get_table_schema(table_name)
            else:
                return {}
        except Exception as e:
            self.logger.error(f"获取表结构异常: {self.user_id} - {str(e)}")
            return {}
    
    def disconnect(self):
        """断开连接（委托给基础连接器）"""
        try:
            if hasattr(self.base_connector, 'disconnect'):
                return self.base_connector.disconnect()
        except Exception as e:
            self.logger.error(f"断开连接异常: {self.user_id} - {str(e)}")
    
    def __getattr__(self, name):
        """代理其他方法到基础连接器"""
        if hasattr(self.base_connector, name):
            return getattr(self.base_connector, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def get_table_info(self, schema_name: str = None) -> Dict[str, Any]:
        """
        获取表信息（带权限检查）
        
        Args:
            schema_name: schema名称（可选）
            
        Returns:
            Dict[str, Any]: 表信息
        """
        try:
            # 1. 如果指定了schema，检查权限
            if schema_name:
                accessible_schemas = self.permission_filter.filter_schemas(
                    self.user_id, [schema_name]
                )
                if schema_name not in accessible_schemas:
                    raise PermissionError(f"没有权限访问schema: {schema_name}")
            
            # 2. 获取表信息
            if hasattr(self.base_connector, 'get_table_info'):
                all_table_info = self.base_connector.get_table_info(schema_name)
            else:
                all_table_info = {}
            
            # 3. 过滤表信息
            if not schema_name:
                # 如果没有指定schema，过滤所有表信息
                accessible_schemas = self.get_schemas()
                filtered_info = {}
                for table_name, info in all_table_info.items():
                    if '.' in table_name:
                        table_schema = table_name.split('.')[0]
                        if table_schema in accessible_schemas:
                            filtered_info[table_name] = info
                    else:
                        # 没有schema前缀的表，假设在默认schema中
                        filtered_info[table_name] = info
                return filtered_info
            else:
                return all_table_info
            
        except PermissionError:
            raise
        except Exception as e:
            self.logger.error(f"获取表信息异常: {self.user_id} - {str(e)}")
            return {}