"""
ChatBI集成适配器
实现认证模块与现有ChatBI系统的无缝集成
"""

import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from dataclasses import dataclass

from .database_permission_filter import DatabasePermissionFilter, UserSpecificDatabaseConnector
from .permission_manager import PermissionManager
from .session_manager import SessionManager
from .database import AuthDatabase
from ..orchestrator import ChatBIOrchestrator, QueryResult
from ..database.connectors import DatabaseConnector, get_global_connector

logger = logging.getLogger(__name__)


@dataclass
class AuthenticatedQueryResult(QueryResult):
    """带认证信息的查询结果"""
    user_id: Optional[str] = None
    accessible_schemas: Optional[List[str]] = None
    permission_filtered: bool = False


class AuthenticatedOrchestrator:
    """带认证功能的ChatBI主控智能体包装器"""
    
    def __init__(self, base_orchestrator: ChatBIOrchestrator, user_id: str, 
                 permission_filter: DatabasePermissionFilter):
        """
        初始化认证包装器
        
        Args:
            base_orchestrator: 原始ChatBI主控智能体
            user_id: 用户ID
            permission_filter: 权限过滤器
        """
        self.base_orchestrator = base_orchestrator
        self.user_id = user_id
        self.permission_filter = permission_filter
        self.logger = logging.getLogger(__name__)
        
        # 创建用户特定的数据库连接器
        self.user_db_connector = self._create_user_database_connector()
        
        # 替换基础orchestrator的数据库相关组件
        self._wrap_database_components()
    
    def _create_user_database_connector(self) -> Optional[UserSpecificDatabaseConnector]:
        """创建用户特定的数据库连接器"""
        try:
            base_connector = get_global_connector()
            user_connector = UserSpecificDatabaseConnector(
                base_connector=base_connector,
                user_id=self.user_id,
                permission_filter=self.permission_filter
            )
            
            if user_connector.connect():
                self.logger.info(f"用户 {self.user_id} 的数据库连接器创建成功")
                return user_connector
            else:
                self.logger.error(f"用户 {self.user_id} 的数据库连接器创建失败")
                return None
                
        except Exception as e:
            self.logger.error(f"创建用户数据库连接器异常: {str(e)}")
            return None
    
    def _wrap_database_components(self):
        """包装数据库相关组件以支持权限过滤"""
        if self.user_db_connector:
            # 替换SQL执行器的数据库连接
            if hasattr(self.base_orchestrator, 'sql_executor'):
                self.base_orchestrator.sql_executor.connector = self.user_db_connector
            
            # 替换Schema管理器的数据库连接
            if hasattr(self.base_orchestrator, 'schema_manager'):
                self.base_orchestrator.schema_manager.connector = self.user_db_connector
    
    def query(self, question: str, auto_visualize: bool = True, 
              analysis_level: str = "standard") -> AuthenticatedQueryResult:
        """
        执行带权限检查的查询
        
        Args:
            question: 用户问题
            auto_visualize: 是否自动生成可视化
            analysis_level: 分析级别
            
        Returns:
            AuthenticatedQueryResult: 带认证信息的查询结果
        """
        try:
            self.logger.info(f"用户 {self.user_id} 开始执行查询: {question}")
            
            # 获取用户可访问的schema列表
            accessible_schemas = self._get_user_accessible_schemas()
            
            # 执行原始查询
            base_result = self.base_orchestrator.query(
                question=question,
                auto_visualize=auto_visualize,
                analysis_level=analysis_level
            )
            
            # 创建带认证信息的结果
            auth_result = AuthenticatedQueryResult(
                success=base_result.success,
                question=base_result.question,
                sql_query=base_result.sql_query,
                data=base_result.data,
                analysis=base_result.analysis,
                chart_info=base_result.chart_info,
                error=base_result.error,
                execution_time=base_result.execution_time,
                metadata=base_result.metadata,
                user_id=self.user_id,
                accessible_schemas=accessible_schemas,
                permission_filtered=True
            )
            
            # 如果查询成功，记录审计日志
            if base_result.success:
                self._log_query_audit(question, base_result.sql_query, True)
            else:
                self._log_query_audit(question, base_result.sql_query, False, base_result.error)
            
            return auth_result
            
        except Exception as e:
            self.logger.error(f"认证查询执行异常: {str(e)}")
            self._log_query_audit(question, None, False, str(e))
            
            return AuthenticatedQueryResult(
                success=False,
                question=question,
                error=f"认证查询执行失败: {str(e)}",
                user_id=self.user_id,
                accessible_schemas=[],
                permission_filtered=True
            )
    
    def query_stream(self, question: str, auto_visualize: bool = True, 
                    analysis_level: str = "standard"):
        """
        执行带权限检查的流式查询
        
        Args:
            question: 用户问题
            auto_visualize: 是否自动生成可视化
            analysis_level: 分析级别
            
        Yields:
            Dict: 包含step_info或final_result的字典
        """
        try:
            self.logger.info(f"用户 {self.user_id} 开始执行流式查询: {question}")
            
            # 添加权限检查步骤
            yield {"step_info": "🔐 **权限验证**: 正在检查用户权限..."}
            
            accessible_schemas = self._get_user_accessible_schemas()
            if not accessible_schemas:
                yield {"step_info": "❌ **权限验证失败**: 用户没有任何数据库访问权限"}
                yield {"final_result": AuthenticatedQueryResult(
                    success=False,
                    question=question,
                    error="用户没有任何数据库访问权限",
                    user_id=self.user_id,
                    accessible_schemas=[],
                    permission_filtered=True
                )}
                return
            
            yield {"step_info": f"✅ **权限验证通过**: 用户可访问 {len(accessible_schemas)} 个schema"}
            
            # 执行原始流式查询
            for result in self.base_orchestrator.query_stream(
                question=question,
                auto_visualize=auto_visualize,
                analysis_level=analysis_level
            ):
                if "final_result" in result:
                    # 包装最终结果
                    base_result = result["final_result"]
                    auth_result = AuthenticatedQueryResult(
                        success=base_result.success,
                        question=base_result.question,
                        sql_query=base_result.sql_query,
                        data=base_result.data,
                        analysis=base_result.analysis,
                        chart_info=base_result.chart_info,
                        error=base_result.error,
                        execution_time=base_result.execution_time,
                        metadata=base_result.metadata,
                        user_id=self.user_id,
                        accessible_schemas=accessible_schemas,
                        permission_filtered=True
                    )
                    
                    # 记录审计日志
                    if base_result.success:
                        self._log_query_audit(question, base_result.sql_query, True)
                    else:
                        self._log_query_audit(question, base_result.sql_query, False, base_result.error)
                    
                    yield {"final_result": auth_result}
                else:
                    # 传递步骤信息
                    yield result
                    
        except Exception as e:
            self.logger.error(f"认证流式查询执行异常: {str(e)}")
            self._log_query_audit(question, None, False, str(e))
            
            yield {"final_result": AuthenticatedQueryResult(
                success=False,
                question=question,
                error=f"认证流式查询执行失败: {str(e)}",
                user_id=self.user_id,
                accessible_schemas=[],
                permission_filtered=True
            )}
    
    def get_schema_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取用户可访问的Schema信息
        
        Args:
            table_name: 特定表名（可选）
            
        Returns:
            Dict[str, Any]: 过滤后的Schema信息
        """
        try:
            # 获取原始schema信息
            base_schema_info = self.base_orchestrator.get_schema_info(table_name)
            
            if "error" in base_schema_info:
                return base_schema_info
            
            # 过滤schema信息
            filtered_schema_info = self._filter_schema_info(base_schema_info)
            
            return filtered_schema_info
            
        except Exception as e:
            self.logger.error(f"获取用户Schema信息异常: {str(e)}")
            return {"error": str(e)}
    
    def refresh_schema(self) -> bool:
        """刷新Schema缓存"""
        return self.base_orchestrator.refresh_schema()
    
    def add_positive_feedback(self, question: str, sql: str, description: str = None) -> bool:
        """添加正面反馈"""
        try:
            # 记录用户反馈审计日志
            self._log_feedback_audit(question, sql, "positive", description)
            
            return self.base_orchestrator.add_positive_feedback(question, sql, description)
            
        except Exception as e:
            self.logger.error(f"添加用户反馈异常: {str(e)}")
            return False
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return self.base_orchestrator.get_knowledge_stats()
    
    def _get_user_accessible_schemas(self) -> List[str]:
        """获取用户可访问的schema列表"""
        try:
            if self.user_db_connector:
                return self.user_db_connector.get_schemas()
            else:
                # 如果用户连接器不可用，使用权限过滤器
                base_connector = get_global_connector()
                all_schemas = base_connector.get_tables()  # 这里需要获取schema列表
                return self.permission_filter.filter_schemas(self.user_id, all_schemas)
                
        except Exception as e:
            self.logger.error(f"获取用户可访问schema异常: {str(e)}")
            return []
    
    def _filter_schema_info(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """过滤schema信息，只返回用户有权限的部分"""
        try:
            accessible_schemas = self._get_user_accessible_schemas()
            
            if not accessible_schemas:
                return {"error": "用户没有任何数据库访问权限"}
            
            # 这里需要根据实际的schema_info结构进行过滤
            # 假设schema_info包含表信息，需要过滤掉用户无权访问的表
            filtered_info = {}
            
            for key, value in schema_info.items():
                if key == "error":
                    filtered_info[key] = value
                elif isinstance(value, dict) and "schema" in str(key).lower():
                    # 过滤schema相关信息
                    if any(schema in str(key) for schema in accessible_schemas):
                        filtered_info[key] = value
                else:
                    # 保留其他信息
                    filtered_info[key] = value
            
            return filtered_info
            
        except Exception as e:
            self.logger.error(f"过滤schema信息异常: {str(e)}")
            return {"error": f"过滤schema信息失败: {str(e)}"}
    
    def _log_query_audit(self, question: str, sql_query: Optional[str], 
                        success: bool, error: Optional[str] = None):
        """记录查询审计日志"""
        try:
            from .models import AuditLog
            from datetime import datetime
            
            audit_log = AuditLog(
                user_id=self.user_id,
                action="chatbi_query_executed",
                resource_type="database",
                resource_id="query",
                details={
                    "question": question,
                    "sql_query": sql_query[:1000] if sql_query else None,
                    "success": success,
                    "error": error,
                    "timestamp": str(datetime.now())
                }
            )
            
            # 这里应该通过AuthDatabase保存审计日志
            # 但为了避免循环依赖，暂时记录到日志文件
            self.logger.info(f"用户 {self.user_id} 查询审计: 成功={success}, 问题={question}")
            
        except Exception as e:
            # 审计日志失败不应该影响主要功能
            self.logger.warning(f"记录查询审计日志失败: {str(e)}")
    
    def _log_feedback_audit(self, question: str, sql: str, feedback_type: str, 
                           description: Optional[str] = None):
        """记录反馈审计日志"""
        try:
            from .models import AuditLog
            from datetime import datetime
            
            audit_log = AuditLog(
                user_id=self.user_id,
                action="user_feedback_submitted",
                resource_type="knowledge_base",
                resource_id="feedback",
                details={
                    "question": question,
                    "sql": sql[:1000] if sql else None,
                    "feedback_type": feedback_type,
                    "description": description,
                    "timestamp": str(datetime.now())
                }
            )
            
            self.logger.info(f"用户 {self.user_id} 反馈审计: 类型={feedback_type}")
            
        except Exception as e:
            self.logger.warning(f"记录反馈审计日志失败: {str(e)}")
    
    def __getattr__(self, name):
        """代理对基础orchestrator的属性访问"""
        if hasattr(self.base_orchestrator, name):
            return getattr(self.base_orchestrator, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


class ChatBIAuthIntegration:
    """ChatBI认证集成适配器"""
    
    def __init__(self, database_config=None):
        """初始化集成适配器"""
        # 如果没有提供数据库配置，使用默认配置
        if database_config is None:
            from chatbi.config import config
            database_config = config.database
            
        self.auth_database = AuthDatabase(database_config)
        self.session_manager = SessionManager(self.auth_database)
        self.permission_manager = PermissionManager(self.auth_database)
        self.permission_filter = DatabasePermissionFilter(
            self.permission_manager, 
            self.auth_database
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("ChatBI认证集成适配器初始化完成")
    
    def wrap_orchestrator(self, orchestrator: ChatBIOrchestrator, 
                         session_token: str) -> Optional[AuthenticatedOrchestrator]:
        """
        包装ChatBI主控智能体以支持认证
        
        Args:
            orchestrator: 原始ChatBI主控智能体
            session_token: 用户会话令牌
            
        Returns:
            Optional[AuthenticatedOrchestrator]: 认证包装器，如果认证失败返回None
        """
        try:
            # 验证会话
            session_result = self.session_manager.validate_session(session_token)
            
            if not session_result.success:
                self.logger.warning(f"会话验证失败: {session_result.message}")
                return None
            
            user_id = session_result.session.user_id
            self.logger.info(f"为用户 {user_id} 创建认证包装器")
            
            # 创建认证包装器
            auth_orchestrator = AuthenticatedOrchestrator(
                base_orchestrator=orchestrator,
                user_id=user_id,
                permission_filter=self.permission_filter
            )
            
            return auth_orchestrator
            
        except Exception as e:
            self.logger.error(f"包装orchestrator异常: {str(e)}")
            return None
    
    def create_user_database_connector(self, user_id: str) -> Optional[UserSpecificDatabaseConnector]:
        """
        为用户创建特定的数据库连接器
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[UserSpecificDatabaseConnector]: 用户特定的数据库连接器
        """
        try:
            # 验证用户存在且活跃
            user = self.auth_database.get_user_by_id(user_id)
            if not user or not user.is_active:
                self.logger.warning(f"用户不存在或未激活: {user_id}")
                return None
            
            # 创建用户特定连接器
            base_connector = get_global_connector()
            user_connector = UserSpecificDatabaseConnector(
                base_connector=base_connector,
                user_id=user_id,
                permission_filter=self.permission_filter
            )
            
            if user_connector.connect():
                self.logger.info(f"用户 {user_id} 的数据库连接器创建成功")
                return user_connector
            else:
                self.logger.error(f"用户 {user_id} 的数据库连接器连接失败")
                return None
                
        except Exception as e:
            self.logger.error(f"创建用户数据库连接器异常: {str(e)}")
            return None
    
    def filter_schema_info(self, user_id: str, schema_info: str) -> str:
        """
        过滤schema信息，只返回用户有权限的部分
        
        Args:
            user_id: 用户ID
            schema_info: 原始schema信息
            
        Returns:
            str: 过滤后的schema信息
        """
        try:
            # 获取用户可访问的schema列表
            accessible_schemas = self.permission_filter.filter_schemas(
                user_id, self._extract_schemas_from_info(schema_info)
            )
            
            if not accessible_schemas:
                return "用户没有任何数据库访问权限。"
            
            # 过滤schema信息
            filtered_info = self._filter_schema_text(schema_info, accessible_schemas)
            
            return filtered_info
            
        except Exception as e:
            self.logger.error(f"过滤schema信息异常: {str(e)}")
            return f"过滤schema信息失败: {str(e)}"
    
    def validate_user_session(self, session_token: str) -> Dict[str, Any]:
        """
        验证用户会话
        
        Args:
            session_token: 会话令牌
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            session_result = self.session_manager.validate_session(session_token)
            
            return {
                "valid": session_result.valid,
                "user_id": session_result.user_id if session_result.valid else None,
                "message": session_result.message,
                "expires_at": session_result.expires_at if session_result.valid else None
            }
            
        except Exception as e:
            self.logger.error(f"验证用户会话异常: {str(e)}")
            return {
                "valid": False,
                "user_id": None,
                "message": f"会话验证失败: {str(e)}",
                "expires_at": None
            }
    
    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户权限信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 用户权限信息
        """
        try:
            user_permissions = self.permission_manager.get_user_permissions(user_id)
            
            return {
                "user_id": user_id,
                "permissions": [
                    {
                        "schema_name": perm.schema_name,
                        "permission_level": perm.permission_level.value,
                        "granted_at": perm.granted_at.isoformat(),
                        "expires_at": perm.expires_at.isoformat() if perm.expires_at else None,
                        "is_active": perm.is_active
                    }
                    for perm in user_permissions
                ],
                "accessible_schemas": [perm.schema_name for perm in user_permissions if perm.is_valid()]
            }
            
        except Exception as e:
            self.logger.error(f"获取用户权限异常: {str(e)}")
            return {
                "user_id": user_id,
                "permissions": [],
                "accessible_schemas": [],
                "error": str(e)
            }
    
    def _extract_schemas_from_info(self, schema_info: str) -> List[str]:
        """从schema信息文本中提取schema名称"""
        import re
        
        # 简单的schema名称提取，可以根据实际格式调整
        schema_pattern = r'(?:schema|database|table)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(schema_pattern, schema_info, re.IGNORECASE)
        
        return list(set(matches))
    
    def _filter_schema_text(self, schema_info: str, accessible_schemas: List[str]) -> str:
        """过滤schema信息文本"""
        if not accessible_schemas:
            return "用户没有任何数据库访问权限。"
        
        # 简单的文本过滤，保留包含可访问schema的行
        lines = schema_info.split('\n')
        filtered_lines = []
        current_schema_block = None
        
        for line in lines:
            line_lower = line.lower()
            
            # 检查是否是schema声明行
            if 'schema:' in line_lower or 'schema ' in line_lower:
                # 检查这个schema是否可访问
                if any(schema in line for schema in accessible_schemas):
                    current_schema_block = True
                    filtered_lines.append(line)
                else:
                    current_schema_block = False
            # 如果在可访问的schema块中，保留相关行
            elif current_schema_block and ('table:' in line_lower or 'table ' in line_lower or line.strip().startswith('-')):
                filtered_lines.append(line)
            # 保留不包含特定schema信息的通用行
            elif not any(keyword in line_lower for keyword in ['schema:', 'table:', '- table']):
                # 重置schema块状态
                if line.strip():  # 非空行
                    current_schema_block = None
                filtered_lines.append(line)
        
        filtered_info = '\n'.join(filtered_lines)
        
        # 添加权限说明
        accessible_schemas_str = ', '.join(accessible_schemas)
        permission_note = f"\n\n注意: 您当前有权限访问以下schema: {accessible_schemas_str}"
        
        return filtered_info + permission_note


# 全局集成适配器实例
_integration_adapter: Optional[ChatBIAuthIntegration] = None

def get_integration_adapter(database_config=None) -> ChatBIAuthIntegration:
    """获取全局集成适配器实例"""
    global _integration_adapter
    
    if _integration_adapter is None:
        _integration_adapter = ChatBIAuthIntegration(database_config)
    
    return _integration_adapter


def require_authentication(func):
    """
    装饰器：要求用户认证
    
    使用方式:
    @require_authentication
    def some_chatbi_function(session_token, ...):
        pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 从参数中提取session_token
        session_token = kwargs.get('session_token') or (args[0] if args else None)
        
        if not session_token:
            return {
                "success": False,
                "error": "缺少会话令牌",
                "requires_login": True
            }
        
        # 验证会话
        integration = get_integration_adapter()
        session_result = integration.validate_user_session(session_token)
        
        if not session_result["valid"]:
            return {
                "success": False,
                "error": session_result["message"],
                "requires_login": True
            }
        
        # 将用户ID添加到kwargs中
        kwargs["user_id"] = session_result["user_id"]
        
        return func(*args, **kwargs)
    
    return wrapper


def require_schema_permission(schema_name: str, permission_level: str = "read"):
    """
    装饰器：要求特定schema权限
    
    Args:
        schema_name: schema名称
        permission_level: 权限级别 (read/write/admin)
    
    使用方式:
    @require_schema_permission("user_data", "read")
    def query_user_data(user_id, ...):
        pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id')
            
            if not user_id:
                return {
                    "success": False,
                    "error": "缺少用户ID",
                    "requires_login": True
                }
            
            # 检查权限
            integration = get_integration_adapter()
            has_permission = integration.permission_filter.check_schema_access(
                user_id, schema_name, permission_level
            )
            
            if not has_permission:
                return {
                    "success": False,
                    "error": f"用户没有权限访问schema '{schema_name}' (需要 {permission_level} 权限)",
                    "permission_denied": True
                }
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator