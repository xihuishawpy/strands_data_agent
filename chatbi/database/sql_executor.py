"""
SQL执行器
提供安全的SQL执行功能，包括SQL验证、注入防护和用户权限验证
"""

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .connectors import get_global_connector

logger = logging.getLogger(__name__)

@dataclass
class SQLResult:
    """SQL执行结果"""
    success: bool
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    error: Optional[str] = None
    execution_time: Optional[float] = None
    query: Optional[str] = None

class SQLValidator:
    """SQL验证器"""
    
    # 危险的SQL关键词
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'TRUNCATE', 'ALTER',
        'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL'
    ]
    
    # 允许的SQL关键词
    ALLOWED_KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT',
        'FULL', 'ON', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT',
        'OFFSET', 'AS', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN',
        'IS', 'NULL', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'UNION', 'EXCEPT',
        'INTERSECT', 'WITH', 'CTE', 'CAST', 'COALESCE', 'NULLIF'
    ]
    
    @classmethod
    def is_safe_query(cls, query: str) -> tuple[bool, str]:
        """
        检查SQL查询是否安全
        返回: (是否安全, 错误信息)
        """
        if not query.strip():
            return False, "查询不能为空"
        
        # 移除注释和多余空格
        cleaned_query = cls._clean_query(query)
        
        # 检查是否包含危险关键词
        query_upper = cleaned_query.upper()
        for keyword in cls.DANGEROUS_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                return False, f"包含危险关键词: {keyword}"
        
        # 检查是否以SELECT开头
        if not re.match(r'^\s*SELECT\b', query_upper):
            return False, "只允许SELECT查询"
        
        # 检查分号数量（避免SQL注入）
        semicolon_count = query.count(';')
        if semicolon_count > 1:
            return False, "不允许执行多条SQL语句"
        
        # 移除末尾的分号
        if query.rstrip().endswith(';'):
            query = query.rstrip()[:-1]
        
        # 检查是否包含子查询中的危险操作
        if cls._contains_dangerous_subquery(query_upper):
            return False, "子查询中包含危险操作"
        
        return True, ""
    
    @classmethod
    def _clean_query(cls, query: str) -> str:
        """清理查询语句"""
        # 移除单行注释
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        # 移除多行注释
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        # 移除多余空格
        query = re.sub(r'\s+', ' ', query).strip()
        return query
    
    @classmethod
    def _contains_dangerous_subquery(cls, query: str) -> bool:
        """检查子查询中是否包含危险操作"""
        # 简单的子查询检查
        subquery_pattern = r'\(\s*SELECT.*?\)'
        subqueries = re.findall(subquery_pattern, query, re.IGNORECASE | re.DOTALL)
        
        for subquery in subqueries:
            for keyword in cls.DANGEROUS_KEYWORDS:
                if re.search(r'\b' + keyword + r'\b', subquery.upper()):
                    return True
        return False

class SQLExecutor:
    """SQL执行器"""
    
    def __init__(self, user_id: Optional[str] = None):
        """
        初始化SQL执行器
        
        Args:
            user_id: 用户ID，如果提供则启用权限检查
        """
        self.user_id = user_id
        self.connector = get_global_connector()
        self.validator = SQLValidator()
        
        # 如果提供了用户ID，则使用用户特定的数据库连接器
        if user_id:
            self._setup_user_connector()
    
    def _setup_user_connector(self):
        """设置用户特定的数据库连接器"""
        try:
            from ..auth.chatbi_integration import get_integration_adapter
            
            integration = get_integration_adapter()
            user_connector = integration.create_user_database_connector(self.user_id)
            
            if user_connector:
                self.connector = user_connector
                logger.info(f"为用户 {self.user_id} 设置了特定的数据库连接器")
            else:
                logger.warning(f"无法为用户 {self.user_id} 创建特定的数据库连接器，使用默认连接器")
                
        except Exception as e:
            logger.error(f"设置用户数据库连接器失败: {str(e)}")
            # 继续使用默认连接器
    
    def execute(self, query: str, params: Dict[str, Any] = None) -> SQLResult:
        """
        执行SQL查询（带用户权限验证）
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            SQLResult: 执行结果
        """
        import time
        
        start_time = time.time()
        
        try:
            # 检查数据库连接状态
            if not self.connector.is_connected:
                logger.warning("数据库连接已断开，尝试重新连接")
                if not self.connector.connect():
                    return SQLResult(
                        success=False,
                        data=[],
                        columns=[],
                        row_count=0,
                        error="数据库连接失败",
                        query=query
                    )
            
            # 验证SQL安全性
            is_safe, error_msg = self.validator.is_safe_query(query)
            if not is_safe:
                logger.warning(f"不安全的SQL查询被拦截: {query}")
                return SQLResult(
                    success=False,
                    data=[],
                    columns=[],
                    row_count=0,
                    error=f"SQL安全检查失败: {error_msg}",
                    query=query
                )
            
            # 如果有用户ID，进行权限验证
            if self.user_id:
                permission_result = self._validate_user_permissions(query)
                if not permission_result["valid"]:
                    logger.warning(f"用户 {self.user_id} SQL权限验证失败: {permission_result['error']}")
                    return SQLResult(
                        success=False,
                        data=[],
                        columns=[],
                        row_count=0,
                        error=f"权限验证失败: {permission_result['error']}",
                        query=query
                    )
            
            logger.info(f"执行SQL查询: {query}")
            
            # 执行查询
            result = self.connector.execute_query(query, params)
            execution_time = time.time() - start_time
            
            if result["success"]:
                return SQLResult(
                    success=True,
                    data=result.get("data", []),
                    columns=result.get("columns", []),
                    row_count=result.get("row_count", 0),
                    execution_time=execution_time,
                    query=query
                )
            else:
                return SQLResult(
                    success=False,
                    data=[],
                    columns=[],
                    row_count=0,
                    error=result.get("error", "未知错误"),
                    execution_time=execution_time,
                    query=query
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"SQL执行失败: {str(e)}")
            return SQLResult(
                success=False,
                data=[],
                columns=[],
                row_count=0,
                error=str(e),
                execution_time=execution_time,
                query=query
            )
    
    def _validate_user_permissions(self, query: str) -> Dict[str, Any]:
        """
        验证用户对SQL查询的权限
        
        Args:
            query: SQL查询语句
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            from ..auth.database_permission_filter import DatabasePermissionFilter
            from ..auth.permission_manager import PermissionManager
            from ..auth.database import AuthDatabase
            
            # 创建权限过滤器
            permission_manager = PermissionManager()
            auth_database = AuthDatabase()
            permission_filter = DatabasePermissionFilter(permission_manager, auth_database)
            
            # 验证SQL权限
            validation_result = permission_filter.validate_sql_permissions(self.user_id, query)
            
            return {
                "valid": validation_result.valid,
                "error": validation_result.message if not validation_result.valid else None,
                "allowed_schemas": validation_result.allowed_schemas,
                "blocked_schemas": validation_result.blocked_schemas
            }
            
        except Exception as e:
            logger.error(f"用户权限验证异常: {str(e)}")
            return {
                "valid": False,
                "error": f"权限验证过程中发生错误: {str(e)}"
            }
    
    def explain_query(self, query: str) -> Dict[str, Any]:
        """
        解释SQL查询执行计划
        
        Args:
            query: SQL查询语句
            
        Returns:
            Dict: 执行计划信息
        """
        try:
            # 验证SQL安全性
            is_safe, error_msg = self.validator.is_safe_query(query)
            if not is_safe:
                return {
                    "success": False,
                    "error": f"SQL安全检查失败: {error_msg}"
                }
            
            # 生成EXPLAIN查询
            explain_query = f"EXPLAIN {query}"
            result = self.connector.execute_query(explain_query)
            
            return result
            
        except Exception as e:
            logger.error(f"EXPLAIN查询失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        验证SQL查询语法
        
        Args:
            query: SQL查询语句
            
        Returns:
            Dict: 验证结果
        """
        try:
            # 安全性检查
            is_safe, error_msg = self.validator.is_safe_query(query)
            if not is_safe:
                return {
                    "valid": False,
                    "safe": False,
                    "error": error_msg
                }
            
            # 语法检查（通过EXPLAIN实现）
            explain_result = self.explain_query(query)
            
            return {
                "valid": explain_result["success"],
                "safe": True,
                "error": explain_result.get("error") if not explain_result["success"] else None
            }
            
        except Exception as e:
            return {
                "valid": False,
                "safe": True,
                "error": str(e)
            }

# 全局SQL执行器实例
_sql_executor: Optional[SQLExecutor] = None

def get_sql_executor(user_id: Optional[str] = None) -> SQLExecutor:
    """
    获取SQL执行器实例
    
    Args:
        user_id: 用户ID，如果提供则返回带权限检查的执行器
        
    Returns:
        SQLExecutor: SQL执行器实例
    """
    if user_id:
        # 为特定用户创建新的执行器实例
        return SQLExecutor(user_id=user_id)
    
    # 返回全局执行器实例
    global _sql_executor
    
    if _sql_executor is None:
        _sql_executor = SQLExecutor()
    
    return _sql_executor

def create_user_sql_executor(user_id: str) -> SQLExecutor:
    """
    为特定用户创建SQL执行器
    
    Args:
        user_id: 用户ID
        
    Returns:
        SQLExecutor: 用户特定的SQL执行器
    """
    return SQLExecutor(user_id=user_id) 