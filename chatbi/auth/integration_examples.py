"""
ChatBI集成适配器使用示例
展示如何在现有ChatBI应用中集成认证功能
"""

from typing import Dict, Any, Optional
import logging

from .chatbi_integration import (
    get_integration_adapter,
    require_authentication,
    require_schema_permission
)
from ..orchestrator import get_orchestrator

logger = logging.getLogger(__name__)


class AuthenticatedChatBIService:
    """带认证功能的ChatBI服务示例"""
    
    def __init__(self):
        """初始化服务"""
        self.integration = get_integration_adapter()
        self.base_orchestrator = get_orchestrator()
        logger.info("认证ChatBI服务初始化完成")
    
    @require_authentication
    def query_with_auth(self, session_token: str, question: str, 
                       auto_visualize: bool = True, user_id: str = None) -> Dict[str, Any]:
        """
        带认证的查询接口
        
        Args:
            session_token: 用户会话令牌
            question: 用户问题
            auto_visualize: 是否自动生成可视化
            user_id: 用户ID（由装饰器自动注入）
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            # 创建认证包装器
            auth_orchestrator = self.integration.wrap_orchestrator(
                self.base_orchestrator, session_token
            )
            
            if not auth_orchestrator:
                return {
                    "success": False,
                    "error": "创建认证包装器失败",
                    "requires_login": True
                }
            
            # 执行查询
            result = auth_orchestrator.query(
                question=question,
                auto_visualize=auto_visualize
            )
            
            # 转换为字典格式
            return {
                "success": result.success,
                "question": result.question,
                "sql_query": result.sql_query,
                "data": result.data,
                "analysis": result.analysis,
                "chart_info": result.chart_info,
                "error": result.error,
                "execution_time": result.execution_time,
                "metadata": result.metadata,
                "user_id": result.user_id,
                "accessible_schemas": result.accessible_schemas,
                "permission_filtered": result.permission_filtered
            }
            
        except Exception as e:
            logger.error(f"认证查询执行异常: {str(e)}")
            return {
                "success": False,
                "error": f"查询执行失败: {str(e)}",
                "user_id": user_id
            }
    
    @require_authentication
    def query_stream_with_auth(self, session_token: str, question: str, 
                              auto_visualize: bool = True, user_id: str = None):
        """
        带认证的流式查询接口
        
        Args:
            session_token: 用户会话令牌
            question: 用户问题
            auto_visualize: 是否自动生成可视化
            user_id: 用户ID（由装饰器自动注入）
            
        Yields:
            Dict[str, Any]: 查询步骤信息或最终结果
        """
        try:
            # 创建认证包装器
            auth_orchestrator = self.integration.wrap_orchestrator(
                self.base_orchestrator, session_token
            )
            
            if not auth_orchestrator:
                yield {
                    "final_result": {
                        "success": False,
                        "error": "创建认证包装器失败",
                        "requires_login": True,
                        "user_id": user_id
                    }
                }
                return
            
            # 执行流式查询
            for result in auth_orchestrator.query_stream(
                question=question,
                auto_visualize=auto_visualize
            ):
                if "final_result" in result:
                    # 转换最终结果为字典格式
                    final_result = result["final_result"]
                    yield {
                        "final_result": {
                            "success": final_result.success,
                            "question": final_result.question,
                            "sql_query": final_result.sql_query,
                            "data": final_result.data,
                            "analysis": final_result.analysis,
                            "chart_info": final_result.chart_info,
                            "error": final_result.error,
                            "execution_time": final_result.execution_time,
                            "metadata": final_result.metadata,
                            "user_id": final_result.user_id,
                            "accessible_schemas": final_result.accessible_schemas,
                            "permission_filtered": final_result.permission_filtered
                        }
                    }
                else:
                    # 传递步骤信息
                    yield result
                    
        except Exception as e:
            logger.error(f"认证流式查询执行异常: {str(e)}")
            yield {
                "final_result": {
                    "success": False,
                    "error": f"流式查询执行失败: {str(e)}",
                    "user_id": user_id
                }
            }
    
    @require_authentication
    def get_user_schema_info(self, session_token: str, table_name: str = None, 
                            user_id: str = None) -> Dict[str, Any]:
        """
        获取用户可访问的Schema信息
        
        Args:
            session_token: 用户会话令牌
            table_name: 特定表名（可选）
            user_id: 用户ID（由装饰器自动注入）
            
        Returns:
            Dict[str, Any]: Schema信息
        """
        try:
            # 创建认证包装器
            auth_orchestrator = self.integration.wrap_orchestrator(
                self.base_orchestrator, session_token
            )
            
            if not auth_orchestrator:
                return {
                    "success": False,
                    "error": "创建认证包装器失败",
                    "requires_login": True
                }
            
            # 获取schema信息
            schema_info = auth_orchestrator.get_schema_info(table_name)
            
            return {
                "success": True,
                "schema_info": schema_info,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"获取用户Schema信息异常: {str(e)}")
            return {
                "success": False,
                "error": f"获取Schema信息失败: {str(e)}",
                "user_id": user_id
            }
    
    @require_authentication
    @require_schema_permission("user_data", "read")
    def query_user_data(self, session_token: str, user_filter: str = None, 
                       user_id: str = None) -> Dict[str, Any]:
        """
        查询用户数据（需要特定schema权限）
        
        Args:
            session_token: 用户会话令牌
            user_filter: 用户过滤条件
            user_id: 用户ID（由装饰器自动注入）
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            # 构建查询问题
            question = "查询用户数据"
            if user_filter:
                question += f"，条件：{user_filter}"
            
            # 执行查询
            return self.query_with_auth(
                session_token=session_token,
                question=question,
                auto_visualize=False
            )
            
        except Exception as e:
            logger.error(f"查询用户数据异常: {str(e)}")
            return {
                "success": False,
                "error": f"查询用户数据失败: {str(e)}",
                "user_id": user_id
            }
    
    @require_authentication
    def add_query_feedback(self, session_token: str, question: str, sql: str, 
                          feedback_type: str = "positive", description: str = None,
                          user_id: str = None) -> Dict[str, Any]:
        """
        添加查询反馈
        
        Args:
            session_token: 用户会话令牌
            question: 原始问题
            sql: SQL查询
            feedback_type: 反馈类型
            description: 描述信息
            user_id: 用户ID（由装饰器自动注入）
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 创建认证包装器
            auth_orchestrator = self.integration.wrap_orchestrator(
                self.base_orchestrator, session_token
            )
            
            if not auth_orchestrator:
                return {
                    "success": False,
                    "error": "创建认证包装器失败",
                    "requires_login": True
                }
            
            # 添加反馈
            if feedback_type == "positive":
                success = auth_orchestrator.add_positive_feedback(
                    question=question,
                    sql=sql,
                    description=description
                )
            else:
                # 其他类型的反馈可以在这里扩展
                success = False
            
            return {
                "success": success,
                "message": "反馈添加成功" if success else "反馈添加失败",
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"添加查询反馈异常: {str(e)}")
            return {
                "success": False,
                "error": f"添加反馈失败: {str(e)}",
                "user_id": user_id
            }
    
    def get_user_permissions_info(self, session_token: str) -> Dict[str, Any]:
        """
        获取用户权限信息（不需要认证装饰器，因为直接使用集成适配器）
        
        Args:
            session_token: 用户会话令牌
            
        Returns:
            Dict[str, Any]: 用户权限信息
        """
        try:
            # 验证会话
            session_result = self.integration.validate_user_session(session_token)
            
            if not session_result["valid"]:
                return {
                    "success": False,
                    "error": session_result["message"],
                    "requires_login": True
                }
            
            user_id = session_result["user_id"]
            
            # 获取权限信息
            permissions_info = self.integration.get_user_permissions(user_id)
            
            return {
                "success": True,
                "permissions": permissions_info,
                "session_info": {
                    "user_id": user_id,
                    "expires_at": session_result["expires_at"]
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户权限信息异常: {str(e)}")
            return {
                "success": False,
                "error": f"获取权限信息失败: {str(e)}"
            }


# 使用示例函数
def example_usage():
    """使用示例"""
    
    # 创建服务实例
    service = AuthenticatedChatBIService()
    
    # 模拟会话令牌
    session_token = "example_session_token"
    
    # 示例1: 执行带认证的查询
    print("=== 示例1: 带认证的查询 ===")
    result = service.query_with_auth(
        session_token=session_token,
        question="查询最近一周的销售数据",
        auto_visualize=True
    )
    print(f"查询结果: {result}")
    
    # 示例2: 执行流式查询
    print("\n=== 示例2: 流式查询 ===")
    for step in service.query_stream_with_auth(
        session_token=session_token,
        question="分析用户行为数据"
    ):
        if "step_info" in step:
            print(f"步骤: {step['step_info']}")
        elif "final_result" in step:
            print(f"最终结果: {step['final_result']['success']}")
    
    # 示例3: 获取Schema信息
    print("\n=== 示例3: 获取Schema信息 ===")
    schema_result = service.get_user_schema_info(
        session_token=session_token
    )
    print(f"Schema信息: {schema_result}")
    
    # 示例4: 查询特定schema数据
    print("\n=== 示例4: 查询特定schema数据 ===")
    user_data_result = service.query_user_data(
        session_token=session_token,
        user_filter="活跃用户"
    )
    print(f"用户数据查询结果: {user_data_result}")
    
    # 示例5: 添加查询反馈
    print("\n=== 示例5: 添加查询反馈 ===")
    feedback_result = service.add_query_feedback(
        session_token=session_token,
        question="查询销售数据",
        sql="SELECT * FROM sales WHERE date >= '2024-01-01'",
        feedback_type="positive",
        description="查询结果准确，SQL生成正确"
    )
    print(f"反馈结果: {feedback_result}")
    
    # 示例6: 获取用户权限信息
    print("\n=== 示例6: 获取用户权限信息 ===")
    permissions_result = service.get_user_permissions_info(session_token)
    print(f"权限信息: {permissions_result}")


if __name__ == "__main__":
    # 运行使用示例
    example_usage()