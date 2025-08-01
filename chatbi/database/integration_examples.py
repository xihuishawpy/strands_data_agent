"""
数据库组件集成示例
展示如何使用修改后的数据库组件与认证系统集成
"""

import logging
from typing import Dict, Any, Optional, List

from .sql_executor import get_sql_executor, create_user_sql_executor
from .schema_manager import get_schema_manager, create_user_schema_manager
from ..auth.chatbi_integration import get_integration_adapter

logger = logging.getLogger(__name__)


class AuthenticatedDatabaseService:
    """带认证功能的数据库服务示例"""
    
    def __init__(self):
        """初始化服务"""
        self.integration = get_integration_adapter()
        logger.info("认证数据库服务初始化完成")
    
    def execute_user_query(self, session_token: str, sql_query: str) -> Dict[str, Any]:
        """
        为用户执行SQL查询（带权限检查）
        
        Args:
            session_token: 用户会话令牌
            sql_query: SQL查询语句
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            # 验证用户会话
            session_result = self.integration.validate_user_session(session_token)
            if not session_result["valid"]:
                return {
                    "success": False,
                    "error": session_result["message"],
                    "requires_login": True
                }
            
            user_id = session_result["user_id"]
            
            # 创建用户特定的SQL执行器
            executor = create_user_sql_executor(user_id)
            
            # 执行查询
            result = executor.execute(sql_query)
            
            return {
                "success": result.success,
                "data": result.data,
                "columns": result.columns,
                "row_count": result.row_count,
                "error": result.error,
                "execution_time": result.execution_time,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"执行用户查询异常: {str(e)}")
            return {
                "success": False,
                "error": f"查询执行失败: {str(e)}"
            }
    
    def get_user_schema_info(self, session_token: str, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取用户可访问的Schema信息
        
        Args:
            session_token: 用户会话令牌
            table_name: 特定表名（可选）
            
        Returns:
            Dict[str, Any]: Schema信息
        """
        try:
            # 验证用户会话
            session_result = self.integration.validate_user_session(session_token)
            if not session_result["valid"]:
                return {
                    "success": False,
                    "error": session_result["message"],
                    "requires_login": True
                }
            
            user_id = session_result["user_id"]
            
            # 创建用户特定的Schema管理器
            schema_manager = create_user_schema_manager(user_id)
            
            if table_name:
                # 获取特定表的Schema
                table_schema = schema_manager.get_table_schema(table_name)
                return {
                    "success": True,
                    "table_schema": table_schema,
                    "user_id": user_id
                }
            else:
                # 获取完整的数据库Schema
                database_schema = schema_manager.get_database_schema()
                return {
                    "success": True,
                    "database_schema": database_schema,
                    "user_id": user_id
                }
                
        except Exception as e:
            logger.error(f"获取用户Schema信息异常: {str(e)}")
            return {
                "success": False,
                "error": f"获取Schema信息失败: {str(e)}"
            }
    
    def get_user_accessible_tables(self, session_token: str) -> Dict[str, Any]:
        """
        获取用户可访问的表列表
        
        Args:
            session_token: 用户会话令牌
            
        Returns:
            Dict[str, Any]: 可访问的表列表
        """
        try:
            # 验证用户会话
            session_result = self.integration.validate_user_session(session_token)
            if not session_result["valid"]:
                return {
                    "success": False,
                    "error": session_result["message"],
                    "requires_login": True
                }
            
            user_id = session_result["user_id"]
            
            # 创建用户特定的Schema管理器
            schema_manager = create_user_schema_manager(user_id)
            
            # 获取用户可访问的表
            tables = schema_manager.get_all_tables()
            
            return {
                "success": True,
                "tables": tables,
                "table_count": len(tables),
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"获取用户可访问表异常: {str(e)}")
            return {
                "success": False,
                "error": f"获取表列表失败: {str(e)}"
            }
    
    def get_user_schema_summary(self, session_token: str) -> Dict[str, Any]:
        """
        获取用户可访问的Schema摘要
        
        Args:
            session_token: 用户会话令牌
            
        Returns:
            Dict[str, Any]: Schema摘要
        """
        try:
            # 验证用户会话
            session_result = self.integration.validate_user_session(session_token)
            if not session_result["valid"]:
                return {
                    "success": False,
                    "error": session_result["message"],
                    "requires_login": True
                }
            
            user_id = session_result["user_id"]
            
            # 创建用户特定的Schema管理器
            schema_manager = create_user_schema_manager(user_id)
            
            # 获取Schema摘要
            summary = schema_manager.get_schema_summary()
            
            return {
                "success": True,
                "schema_summary": summary,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"获取用户Schema摘要异常: {str(e)}")
            return {
                "success": False,
                "error": f"获取Schema摘要失败: {str(e)}"
            }
    
    def search_user_accessible_tables(self, session_token: str, keywords: List[str]) -> Dict[str, Any]:
        """
        搜索用户可访问的相关表
        
        Args:
            session_token: 用户会话令牌
            keywords: 搜索关键词
            
        Returns:
            Dict[str, Any]: 相关表信息
        """
        try:
            # 验证用户会话
            session_result = self.integration.validate_user_session(session_token)
            if not session_result["valid"]:
                return {
                    "success": False,
                    "error": session_result["message"],
                    "requires_login": True
                }
            
            user_id = session_result["user_id"]
            
            # 创建用户特定的Schema管理器
            schema_manager = create_user_schema_manager(user_id)
            
            # 搜索相关表
            relevant_tables = schema_manager.search_relevant_tables(keywords)
            
            return {
                "success": True,
                "relevant_tables": relevant_tables,
                "keywords": keywords,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"搜索用户可访问表异常: {str(e)}")
            return {
                "success": False,
                "error": f"搜索表失败: {str(e)}"
            }
    
    def validate_user_sql(self, session_token: str, sql_query: str) -> Dict[str, Any]:
        """
        验证用户SQL查询的权限和语法
        
        Args:
            session_token: 用户会话令牌
            sql_query: SQL查询语句
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 验证用户会话
            session_result = self.integration.validate_user_session(session_token)
            if not session_result["valid"]:
                return {
                    "success": False,
                    "error": session_result["message"],
                    "requires_login": True
                }
            
            user_id = session_result["user_id"]
            
            # 创建用户特定的SQL执行器
            executor = create_user_sql_executor(user_id)
            
            # 验证查询
            validation_result = executor.validate_query(sql_query)
            
            return {
                "success": True,
                "validation_result": validation_result,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"验证用户SQL异常: {str(e)}")
            return {
                "success": False,
                "error": f"SQL验证失败: {str(e)}"
            }
    
    def explain_user_query(self, session_token: str, sql_query: str) -> Dict[str, Any]:
        """
        解释用户SQL查询的执行计划
        
        Args:
            session_token: 用户会话令牌
            sql_query: SQL查询语句
            
        Returns:
            Dict[str, Any]: 执行计划
        """
        try:
            # 验证用户会话
            session_result = self.integration.validate_user_session(session_token)
            if not session_result["valid"]:
                return {
                    "success": False,
                    "error": session_result["message"],
                    "requires_login": True
                }
            
            user_id = session_result["user_id"]
            
            # 创建用户特定的SQL执行器
            executor = create_user_sql_executor(user_id)
            
            # 解释查询
            explain_result = executor.explain_query(sql_query)
            
            return {
                "success": explain_result["success"],
                "explain_result": explain_result,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"解释用户查询异常: {str(e)}")
            return {
                "success": False,
                "error": f"查询解释失败: {str(e)}"
            }


def example_usage():
    """使用示例"""
    
    # 创建服务实例
    service = AuthenticatedDatabaseService()
    
    # 模拟会话令牌
    session_token = "example_session_token"
    
    # 示例1: 执行用户查询
    print("=== 示例1: 执行用户查询 ===")
    query_result = service.execute_user_query(
        session_token=session_token,
        sql_query="SELECT * FROM public.users LIMIT 10"
    )
    print(f"查询结果: {query_result}")
    
    # 示例2: 获取用户可访问的表
    print("\n=== 示例2: 获取用户可访问的表 ===")
    tables_result = service.get_user_accessible_tables(session_token)
    print(f"可访问的表: {tables_result}")
    
    # 示例3: 获取Schema信息
    print("\n=== 示例3: 获取Schema信息 ===")
    schema_result = service.get_user_schema_info(session_token)
    print(f"Schema信息: {schema_result}")
    
    # 示例4: 获取Schema摘要
    print("\n=== 示例4: 获取Schema摘要 ===")
    summary_result = service.get_user_schema_summary(session_token)
    print(f"Schema摘要: {summary_result}")
    
    # 示例5: 搜索相关表
    print("\n=== 示例5: 搜索相关表 ===")
    search_result = service.search_user_accessible_tables(
        session_token=session_token,
        keywords=["user", "order", "product"]
    )
    print(f"搜索结果: {search_result}")
    
    # 示例6: 验证SQL查询
    print("\n=== 示例6: 验证SQL查询 ===")
    validation_result = service.validate_user_sql(
        session_token=session_token,
        sql_query="SELECT name, email FROM public.users WHERE active = true"
    )
    print(f"验证结果: {validation_result}")
    
    # 示例7: 解释查询执行计划
    print("\n=== 示例7: 解释查询执行计划 ===")
    explain_result = service.explain_user_query(
        session_token=session_token,
        sql_query="SELECT COUNT(*) FROM public.orders WHERE created_at > '2024-01-01'"
    )
    print(f"执行计划: {explain_result}")


def compare_global_vs_user_components():
    """比较全局组件与用户特定组件的差异"""
    
    print("=== 全局组件 vs 用户特定组件对比 ===")
    
    # 全局组件
    print("\n--- 全局组件 ---")
    global_executor = get_sql_executor()
    global_schema_manager = get_schema_manager()
    
    print(f"全局SQL执行器用户ID: {global_executor.user_id}")
    print(f"全局Schema管理器用户ID: {global_schema_manager.user_id}")
    
    # 用户特定组件
    print("\n--- 用户特定组件 ---")
    user_executor = create_user_sql_executor("user123")
    user_schema_manager = create_user_schema_manager("user123")
    
    print(f"用户SQL执行器用户ID: {user_executor.user_id}")
    print(f"用户Schema管理器用户ID: {user_schema_manager.user_id}")
    
    # 功能差异说明
    print("\n--- 功能差异 ---")
    print("全局组件:")
    print("- 不进行用户权限检查")
    print("- 可以访问所有数据库对象")
    print("- 适用于系统级操作")
    
    print("\n用户特定组件:")
    print("- 自动进行用户权限检查")
    print("- 只能访问用户有权限的数据库对象")
    print("- 适用于用户级操作")
    print("- 自动记录审计日志")


if __name__ == "__main__":
    # 运行使用示例
    example_usage()
    
    print("\n" + "="*60)
    
    # 运行组件对比
    compare_global_vs_user_components()