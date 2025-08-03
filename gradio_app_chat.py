#!/usr/bin/env python3
"""
ChatBI 对话式Gradio前端界面
提供人机交互式的智能数据查询体验，支持用户认证和权限管理
"""

import os
import sys
import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    import gradio as gr
    from chatbi.config import config
    from chatbi.orchestrator import get_orchestrator
    from chatbi.database import get_database_connector, get_schema_manager, get_table_metadata_manager
    # 导入认证相关组件
    from chatbi.auth import (
        UserManager, SessionManager, AuthDatabase, 
        get_integration_adapter, require_authentication
    )
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install gradio openai")
    sys.exit(1)

class ChatBIApp:
    """ChatBI 对话式应用，支持用户认证和权限管理"""
    
    def __init__(self):
        """初始化应用"""
        # 基础ChatBI组件
        self.base_orchestrator = None
        self.connector = None
        self.schema_manager = None
        self.metadata_manager = None
        
        # 认证相关组件
        try:
            from chatbi.config import config
            from chatbi.auth.config import get_auth_config
            
            print("🔧 正在初始化认证系统...")
            
            # 使用主配置中的数据库配置
            database_config = config.database
            print(f"📊 数据库配置: {database_config.host}:{database_config.port}/{database_config.database}")
            
            self.auth_database = AuthDatabase(database_config)
            print("✅ 认证数据库初始化成功")
            
            self.user_manager = UserManager(self.auth_database)
            print("✅ 用户管理器初始化成功")
            
            self.session_manager = SessionManager(self.auth_database)
            print("✅ 会话管理器初始化成功")
            
            self.integration_adapter = get_integration_adapter(database_config)
            print("✅ 集成适配器初始化成功")
            
            print("🎉 认证系统初始化完成")
            
        except Exception as e:
            # 如果认证组件初始化失败，设置为None
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"认证组件初始化失败: {str(e)}")
            print(f"❌ 认证组件初始化失败: {str(e)}")
            traceback.print_exc()
            self.auth_database = None
            self.user_manager = None
            self.session_manager = None
            self.integration_adapter = None
        
        # 应用状态
        self.current_user = None
        self.current_session_token = None
        self.authenticated_orchestrator = None
        self.chat_history = []
        self.last_query_result = None  # 存储最后一次查询结果，用于反馈
        
        # 尝试初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化ChatBI组件"""
        try:
            self.base_orchestrator = get_orchestrator()
            self.connector = get_database_connector()
            self.schema_manager = get_schema_manager()
            self.metadata_manager = get_table_metadata_manager()
            return True, "✅ ChatBI系统初始化成功"
        except Exception as e:
            error_msg = f"❌ 系统初始化失败: {str(e)}"
            return False, error_msg
    
    def login_user(self, employee_id: str, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        用户登录
        
        Args:
            employee_id: 工号
            password: 密码
            
        Returns:
            Tuple[bool, str, Dict]: (是否成功, 消息, 用户信息)
        """
        try:
            if not self.user_manager or not self.session_manager or not self.integration_adapter:
                return False, "认证系统未初始化，请检查配置", {}
            
            if not employee_id.strip() or not password.strip():
                return False, "请输入工号和密码", {}
            
            # 验证用户身份
            auth_result = self.user_manager.authenticate_user(employee_id.strip(), password)
            
            if not auth_result.success:
                return False, f"登录失败: {auth_result.message}", {}
            
            # 创建会话
            session_result = self.session_manager.create_session(
                user_id=auth_result.user.id,
                ip_address="127.0.0.1"  # 在实际应用中应该获取真实IP
            )
            
            if not session_result.success:
                return False, f"创建会话失败: {session_result.message}", {}
            
            # 设置当前用户和会话
            self.current_user = auth_result.user
            self.current_session_token = session_result.session_token
            
            # 创建认证包装器
            self.authenticated_orchestrator = self.integration_adapter.wrap_orchestrator(
                self.base_orchestrator, self.current_session_token
            )
            
            if not self.authenticated_orchestrator:
                return False, "创建认证包装器失败", {}
            
            # 返回用户信息
            user_info = {
                "employee_id": self.current_user.employee_id,
                "full_name": self.current_user.full_name or "未设置",
                "email": self.current_user.email or "未设置",
                "is_admin": self.current_user.is_admin,
                "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return True, f"欢迎，{self.current_user.employee_id}！", user_info
            
        except Exception as e:
            return False, f"登录过程中发生错误: {str(e)}", {}
    
    def logout_user(self) -> Tuple[bool, str]:
        """
        用户登出
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if self.current_session_token and self.session_manager:
                # 销毁会话
                self.session_manager.destroy_session(self.current_session_token)
            
            # 清除状态
            self.current_user = None
            self.current_session_token = None
            self.authenticated_orchestrator = None
            self.chat_history = []
            self.last_query_result = None
            
            return True, "已成功登出"
            
        except Exception as e:
            return False, f"登出过程中发生错误: {str(e)}"
    
    def register_user(self, employee_id: str, password: str, confirm_password: str, 
                     email: str = "", full_name: str = "") -> Tuple[bool, str]:
        """
        用户注册
        
        Args:
            employee_id: 工号
            password: 密码
            confirm_password: 确认密码
            email: 邮箱（可选）
            full_name: 姓名（可选）
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if not self.user_manager:
                return False, "认证系统未初始化，请检查配置"
            
            if not employee_id.strip() or not password.strip():
                return False, "工号和密码不能为空"
            
            if password != confirm_password:
                return False, "两次输入的密码不一致"
            
            # 注册用户
            registration_result = self.user_manager.register_user(
                employee_id=employee_id.strip(),
                password=password,
                email=email.strip() if email else None,
                full_name=full_name.strip() if full_name else None
            )
            
            if registration_result.success:
                return True, f"注册成功！用户ID: {registration_result.user_id}"
            else:
                return False, f"注册失败: {registration_result.message}"
                
        except Exception as e:
            return False, f"注册过程中发生错误: {str(e)}"
    
    def is_authenticated(self) -> bool:
        """检查用户是否已认证"""
        return (self.current_user is not None and 
                self.current_session_token is not None and 
                self.authenticated_orchestrator is not None and
                self.user_manager is not None)
    
    def get_user_info(self) -> Dict[str, Any]:
        """获取当前用户信息"""
        if not self.current_user:
            return {}
        
        return {
            "employee_id": self.current_user.employee_id,
            "full_name": self.current_user.full_name or "未设置",
            "email": self.current_user.email or "未设置",
            "is_admin": self.current_user.is_admin,
            "is_active": self.current_user.is_active,
            "created_at": self.current_user.created_at.strftime("%Y-%m-%d") if self.current_user.created_at else "未知"
        }
    
    def chat_query(self, message: str, history: List, auto_viz: bool = True, enable_analysis: bool = True, analysis_level: str = "standard"):
        """处理对话式查询 - 支持流式输出、RAG状态指示和用户权限检查"""
        if not message.strip():
            history.append([message, "❌ 请输入有效的查询问题"])
            yield history, "", None
            return
        
        # 检查用户是否已认证
        if not self.is_authenticated():
            history.append([message, "❌ 请先登录后再进行查询"])
            yield history, "", None
            return
        
        try:
            if not self.authenticated_orchestrator:
                history.append([message, "❌ 认证系统未初始化，请重新登录"])
                yield history, "", None
                return
            
            # 初始化流式响应
            current_response = f"🤖 **正在为用户 {self.current_user.employee_id} 处理查询...**\n\n"
            history.append([message, current_response])
            yield history, "", None
            
            # 使用认证包装器执行流式查询
            final_analysis_level = analysis_level if enable_analysis else "none"
            for step_update in self.authenticated_orchestrator.query_stream(
                question=message,
                auto_visualize=auto_viz,
                analysis_level=final_analysis_level
            ):
                # 更新当前响应
                if step_update.get('step_info'):
                    current_response += step_update['step_info'] + "\n"
                    history[-1][1] = current_response
                    yield history, "", None
                
                # 如果是最终结果
                if step_update.get('final_result'):
                    result = step_update['final_result']
                    break
            else:
                # 如果没有最终结果，说明出错了
                current_response += "❌ **查询过程中断**\n"
                history[-1][1] = current_response
                yield history, "", None
                return
            
            if not result.success:
                error_response = f"❌ 查询失败\n\n**错误信息**: {result.error}"
                if hasattr(result, 'permission_filtered') and result.permission_filtered:
                    error_response += "\n\n💡 **提示**: 这可能是权限问题，请联系管理员检查您的数据库访问权限。"
                current_response += error_response
                history[-1][1] = current_response
                yield history, "", None
                return
            
            # 构建最终的完整回复，包含用户权限信息
            final_response = self._build_authenticated_response(result, auto_viz)
            
            # 更新历史记录为最终完整回复
            history[-1][1] = final_response
            
            # 准备图表数据
            chart_data = None
            if result.data and len(result.data) > 0:
                df = pd.DataFrame(result.data)
                metadata = result.metadata or {}
                
                if auto_viz and result.chart_info and result.chart_info.get('success'):
                    chart_data = self._create_plotly_chart(df, result.chart_info)
                elif auto_viz and metadata.get('visualization_suggestion'):
                    chart_data = self._create_chart_from_suggestion(df, metadata['visualization_suggestion'])
            
            # 保存查询结果用于反馈
            self.last_query_result = result
            
            # 添加到内部历史
            self.chat_history.append({
                "question": message,
                "sql": result.sql_query,
                "success": True,
                "rows": len(result.data) if result.data and isinstance(result.data, list) else 0,
                "user_id": self.current_user.id,
                "accessible_schemas": getattr(result, 'accessible_schemas', [])
            })
            
            yield history, "", chart_data
            
        except Exception as e:
            error_response = f"❌ **系统错误**\n\n```\n{str(e)}\n```"
            history.append([message, error_response])
            return history, "", None
    
    def _create_plotly_chart(self, df: pd.DataFrame, chart_info: Dict) -> Optional[go.Figure]:
        """创建Plotly图表"""
        try:
            if not chart_info or not isinstance(chart_info, dict):
                return None
                
            if df is None or df.empty:
                return None
                
            chart_type = chart_info.get('chart_type', 'bar')
            title = chart_info.get('title', '数据可视化')
            x_col = chart_info.get('x_column') or chart_info.get('x_axis')
            y_col = chart_info.get('y_column') or chart_info.get('y_axis')
            
            if not x_col or not y_col or x_col not in df.columns or y_col not in df.columns:
                x_col, y_col = self._auto_select_columns(df)
            
            if not x_col or not y_col:
                return None
            
            # 根据图表类型创建图表
            if chart_type == 'bar':
                fig = px.bar(df, x=x_col, y=y_col, title=title)
            elif chart_type == 'line':
                fig = px.line(df, x=x_col, y=y_col, title=title)
            elif chart_type == 'scatter':
                fig = px.scatter(df, x=x_col, y=y_col, title=title)
            elif chart_type == 'pie':
                fig = px.pie(df, names=x_col, values=y_col, title=title)
            else:
                fig = px.bar(df, x=x_col, y=y_col, title=title)
            
            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            print(f"图表创建失败: {e}")
            return None
    
    def _create_chart_from_suggestion(self, df: pd.DataFrame, suggestion: Dict) -> Optional[go.Figure]:
        """根据可视化建议创建图表"""
        try:
            if not suggestion or not isinstance(suggestion, dict):
                return None
                
            chart_type = suggestion.get('chart_type', 'bar')
            
            if chart_type == 'none':
                return None
            
            x_col = suggestion.get('x_axis') or suggestion.get('category')
            y_col = suggestion.get('y_axis') or suggestion.get('value')
            
            if not x_col or not y_col:
                auto_x, auto_y = self._auto_select_columns(df)
                x_col = x_col or auto_x
                y_col = y_col or auto_y
            
            if not x_col or not y_col:
                return None
            
            title = suggestion.get('title', f'{chart_type.title()}图表')
            
            chart_config = {
                'chart_type': chart_type,
                'title': title,
                'x_column': x_col,
                'y_column': y_col,
                'x_axis': x_col,
                'y_axis': y_col,
                'category': x_col,
                'value': y_col
            }
            
            return self._create_plotly_chart(df, chart_config)
            
        except Exception as e:
            print(f"从建议创建图表失败: {e}")
            return None
    
    def _auto_select_columns(self, df: pd.DataFrame) -> tuple[str, str]:
        """自动选择合适的列进行绘图"""
        try:
            columns = df.columns.tolist()
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()
            
            y_col = numeric_cols[0] if numeric_cols else None
            
            if categorical_cols:
                x_col = categorical_cols[0]
            elif len(columns) > 1:
                x_col = columns[0] if columns[0] != y_col else columns[1]
            else:
                x_col = columns[0] if columns else None
            
            return x_col, y_col
            
        except Exception as e:
            print(f"自动选择列失败: {e}")
            return None, None
    
    def _build_authenticated_response(self, result, auto_viz: bool) -> str:
        """构建带认证信息的对话回复"""
        response_parts = []
        
        # 1. 查询摘要
        metadata = result.metadata or {}
        response_parts.append(f"✅ **查询完成** (耗时: {result.execution_time:.2f}秒)")
        response_parts.append(f"📊 获得 **{metadata.get('row_count', 0)}** 行数据")
        
        # 添加用户权限信息
        if hasattr(result, 'accessible_schemas') and result.accessible_schemas:
            response_parts.append(f"🔐 **可访问的Schema**: {', '.join(result.accessible_schemas)}")
        
        response_parts.append("")
        
        # 2. SQL查询展示
        if result.sql_query:
            response_parts.append("### 🔧 生成的SQL查询")
            response_parts.append(f"```sql\n{result.sql_query}\n```")
            
            # 显示涉及的表
            if metadata.get('schema_tables_used'):
                tables_used = metadata['schema_tables_used']
                response_parts.append(f"**涉及的表**: {', '.join(tables_used)}")
            response_parts.append("")
        
        # 3. 数据结果预览
        if result.data and len(result.data) > 0:
            df = pd.DataFrame(result.data)
            
            response_parts.append("### 📊 数据结果")
            response_parts.append(f"**字段**: {', '.join(df.columns)}")
            
            # 数据预览
            display_df = df.head(50)
            formatted_df = display_df.copy()
            for col in formatted_df.columns:
                if formatted_df[col].dtype in ['int64', 'float64']:
                    formatted_df[col] = formatted_df[col].apply(self._format_number)
            
            response_parts.append("\n**数据预览**:")
            response_parts.append(formatted_df.to_markdown(index=False))
            
            if len(df) > 50:
                response_parts.append(f"\n*显示前50行，总共{len(df)}行*")
            response_parts.append("")
        else:
            # 处理无数据的情况
            response_parts.append("### 📊 数据结果")
            response_parts.append("⚠️ **查询执行成功，但未返回任何数据**")
            response_parts.append("")
            response_parts.append("**可能的原因**:")
            response_parts.append("- 查询条件过于严格，没有匹配的记录")
            response_parts.append("- 相关表中暂无数据")
            response_parts.append("- JOIN条件可能需要调整")
            response_parts.append("- 您可能没有访问相关数据的权限")
            response_parts.append("")
            response_parts.append("**建议**:")
            response_parts.append("- 尝试放宽查询条件")
            response_parts.append("- 检查表中是否有数据")
            response_parts.append("- 询问具体的表结构和数据情况")
            response_parts.append("- 联系管理员检查数据访问权限")
            response_parts.append("")
        
        # 4. 智能分析
        if result.analysis:
            response_parts.append("### 🔍 智能分析")
            response_parts.append(result.analysis)
            response_parts.append("")
        
        # 5. 可视化说明
        if auto_viz:
            viz_suggestion = metadata.get('visualization_suggestion') or {}
            chart_type = viz_suggestion.get('chart_type', 'none') if viz_suggestion else 'none'
            
            if chart_type != 'none' and result.data and len(result.data) > 0:
                response_parts.append("### 🎨 数据可视化")
                if result.chart_info and result.chart_info.get("success"):
                    response_parts.append(f"✅ 已生成 **{chart_type}** 图表")
                    if viz_suggestion.get('reason'):
                        response_parts.append(f"**选择理由**: {viz_suggestion['reason']}")
                else:
                    response_parts.append(f"⚠️ 建议使用 **{chart_type}** 图表，但生成失败")
            elif result.data and len(result.data) > 0:
                response_parts.append("### 🎨 数据可视化")
                response_parts.append("ℹ️ 当前数据不适合可视化展示")
            else:
                response_parts.append("### 🎨 数据可视化")
                response_parts.append("ℹ️ 无数据可视化")
        
        return "\n".join(response_parts)

    def _build_complete_response(self, result, auto_viz: bool, rag_status: str = None) -> str:
        """构建完整的对话回复，包含RAG状态信息（保持向后兼容）"""
        response_parts = []
        
        # 1. 查询摘要
        metadata = result.metadata or {}
        response_parts.append(f"✅ **查询完成** (耗时: {result.execution_time:.2f}秒)")
        response_parts.append(f"📊 获得 **{metadata.get('row_count', 0)}** 行数据")
        
        # 添加RAG状态信息
        if rag_status:
            response_parts.append(f"🧠 **RAG状态**: {rag_status}")
        
        response_parts.append("")
        
        # 2. SQL查询展示
        if result.sql_query:
            response_parts.append("### 🔧 生成的SQL查询")
            response_parts.append(f"```sql\n{result.sql_query}\n```")
            
            # 显示涉及的表
            if metadata.get('schema_tables_used'):
                tables_used = metadata['schema_tables_used']
                response_parts.append(f"**涉及的表**: {', '.join(tables_used)}")
            response_parts.append("")
        
        # 3. 数据结果预览
        if result.data and len(result.data) > 0:
            df = pd.DataFrame(result.data)
            
            response_parts.append("### 📊 数据结果")
            response_parts.append(f"**字段**: {', '.join(df.columns)}")
            
            # 数据预览
            display_df = df.head(50)
            formatted_df = display_df.copy()
            for col in formatted_df.columns:
                if formatted_df[col].dtype in ['int64', 'float64']:
                    formatted_df[col] = formatted_df[col].apply(self._format_number)
            
            response_parts.append("\n**数据预览**:")
            response_parts.append(formatted_df.to_markdown(index=False))
            
            if len(df) > 50:
                response_parts.append(f"\n*显示前50行，总共{len(df)}行*")
            response_parts.append("")
        else:
            # 处理无数据的情况
            response_parts.append("### 📊 数据结果")
            response_parts.append("⚠️ **查询执行成功，但未返回任何数据**")
            response_parts.append("")
            response_parts.append("**可能的原因**:")
            response_parts.append("- 查询条件过于严格，没有匹配的记录")
            response_parts.append("- 相关表中暂无数据")
            response_parts.append("- JOIN条件可能需要调整")
            response_parts.append("")
            response_parts.append("**建议**:")
            response_parts.append("- 尝试放宽查询条件")
            response_parts.append("- 检查表中是否有数据")
            response_parts.append("- 询问具体的表结构和数据情况")
            response_parts.append("")
        
        # 4. 智能分析
        if result.analysis:
            response_parts.append("### 🔍 智能分析")
            response_parts.append(result.analysis)
            response_parts.append("")
        
        # 5. 可视化说明
        if auto_viz:
            viz_suggestion = metadata.get('visualization_suggestion') or {}
            chart_type = viz_suggestion.get('chart_type', 'none') if viz_suggestion else 'none'
            
            if chart_type != 'none' and result.data and len(result.data) > 0:
                response_parts.append("### 🎨 数据可视化")
                if result.chart_info and result.chart_info.get("success"):
                    response_parts.append(f"✅ 已生成 **{chart_type}** 图表")
                    if viz_suggestion.get('reason'):
                        response_parts.append(f"**选择理由**: {viz_suggestion['reason']}")
                else:
                    response_parts.append(f"⚠️ 建议使用 **{chart_type}** 图表，但生成失败")
            elif result.data and len(result.data) > 0:
                response_parts.append("### 🎨 数据可视化")
                response_parts.append("ℹ️ 当前数据不适合可视化展示")
            else:
                response_parts.append("### 🎨 数据可视化")
                response_parts.append("ℹ️ 无数据可视化")
        
        return "\n".join(response_parts)

    def _format_number(self, value):
        """格式化数字显示"""
        try:
            if pd.isna(value):
                return "N/A"
            
            num = float(value)
            
            if num.is_integer():
                num = int(num)
                if abs(num) >= 1000:
                    return f"{num:,}"
                else:
                    return str(num)
            
            if abs(num) >= 1e6:
                if abs(num) >= 1e8:
                    return f"{num/1e8:.2f}亿"
                elif abs(num) >= 1e4:
                    return f"{num/1e4:.2f}万"
                else:
                    return f"{num:,.2f}"
            elif abs(num) < 0.01 and abs(num) > 0:
                return f"{num:.6f}".rstrip('0').rstrip('.')
            else:
                return f"{num:.2f}".rstrip('0').rstrip('.')
                
        except (ValueError, TypeError):
            return str(value)
    
    def handle_query_with_feedback(self, question: str) -> Tuple[str, str, bool]:
        """处理查询并提供反馈机制的完整流程"""
        try:
            # 使用认证后的orchestrator或基础orchestrator
            orchestrator = self.authenticated_orchestrator or self.base_orchestrator
            if not orchestrator:
                return "❌ 系统未初始化，请稍后重试"
            
            # 执行查询
            result = orchestrator.query(
                question=question,
                auto_visualize=True,
                analysis_level="standard"
            )
            
            if not result.success:
                return f"❌ 查询失败: {result.error}", "", False
            
            # 构建响应
            response = self._build_complete_response(result, True)
            
            # 保存查询结果用于反馈
            self.last_query_result = result
            
            # 返回响应、空的反馈描述、以及是否可以反馈
            return response, "", True
            
        except Exception as e:
            return f"❌ 系统错误: {str(e)}", "", False

    def add_positive_feedback(self, description: str = "") -> str:
        """添加正面反馈到知识库"""
        if not self.is_authenticated():
            return "❌ 请先登录后再提供反馈"
        
        if not self.authenticated_orchestrator:
            return "❌ 认证系统未初始化"
        
        if not self.last_query_result or not self.last_query_result.success:
            return "❌ 没有可反馈的查询结果"
        
        try:
            success = self.authenticated_orchestrator.add_positive_feedback(
                question=self.last_query_result.question,
                sql=self.last_query_result.sql_query,
                description=description or f"用户 {self.current_user.employee_id} 点赞的高质量查询"
            )
            
            if success:
                return "✅ 感谢反馈！已将此查询添加到知识库，将帮助改进未来的查询生成"
            else:
                return "⚠️ 反馈添加失败，可能是知识库未启用"
        
        except Exception as e:
            return f"❌ 反馈添加失败: {str(e)}"
    
    def get_knowledge_stats(self) -> str:
        """获取知识库统计信息"""
        try:
            # 使用认证包装器或基础orchestrator
            orchestrator = self.authenticated_orchestrator if self.is_authenticated() else self.base_orchestrator
            if not orchestrator:
                return "❌ 系统未初始化"
            
            stats = orchestrator.get_knowledge_stats()
            
            if stats.get("enabled"):
                user_info = f" (当前用户: {self.current_user.employee_id})" if self.is_authenticated() else ""
                return f"""
### 📊 SQL知识库统计{user_info}

- **总条目数**: {stats.get('total_items', 0)}
- **平均评分**: {stats.get('avg_rating', 0):.2f}
- **总使用次数**: {stats.get('total_usage', 0)}
- **高评分条目**: {stats.get('top_rated_count', 0)}
- **集合名称**: {stats.get('collection_name', 'N/A')}
- **状态**: ✅ 启用

### 💡 知识库说明
知识库通过收集用户反馈的高质量查询，使用RAG技术提升SQL生成的准确性和一致性。当您对查询结果满意时，请点击"👍 添加到知识库"按钮。

### 🔄 RAG工作流程
1. **智能检索**: 用户提问时，系统首先搜索知识库中的相似问题
2. **相似度判断**: 计算问题间的语义相似度
3. **策略选择**: 
   - 高相似度(>0.8): 直接使用缓存SQL
   - 中相似度(0.6-0.8): 使用相似示例辅助生成
   - 低相似度(<0.6): 常规生成流程
4. **持续学习**: 用户点赞的查询自动加入知识库

### 🔐 权限说明
- 登录用户的查询会根据其数据库访问权限进行过滤
- 反馈的查询会记录提交用户信息
- 管理员可以查看所有用户的反馈记录
                """
            else:
                return f"""
### ❌ SQL知识库未启用

**原因**: {stats.get('reason', '未知原因')}

### 🔧 启用方法
1. 安装依赖: `pip install chromadb sentence-transformers`
2. 设置API密钥: 确保DASHSCOPE_API_KEY已配置
3. 重启应用

### 📚 功能说明
SQL知识库是ChatBI的核心功能之一，通过RAG技术：
- 🧠 智能检索匹配历史查询
- 👍 收集用户反馈持续改进
- 🚀 提升SQL生成准确性和一致性

### 🔐 认证功能
- 支持用户登录和权限管理
- 根据用户权限过滤数据库访问
- 记录用户操作审计日志
                """
        except Exception as e:
            return f"❌ 获取知识库统计失败: {str(e)}"
    
    def get_knowledge_table(self) -> pd.DataFrame:
        """获取知识库表格数据"""
        try:
            # 使用认证后的orchestrator或基础orchestrator
            orchestrator = self.authenticated_orchestrator or self.base_orchestrator
            if not orchestrator:
                return pd.DataFrame(columns=['ID', '问题', 'SQL查询', '描述', '标签', '评分', '使用次数', '创建时间'])
            
            items = orchestrator.knowledge_manager.get_all_knowledge_items()
            
            if not items:
                return pd.DataFrame(columns=['ID', '问题', 'SQL查询', '描述', '标签', '评分', '使用次数', '创建时间'])
            
            # 转换为DataFrame
            df_data = []
            for item in items:
                tags_str = ', '.join(item['tags']) if item['tags'] else ''
                created_time = item['created_at'][:19] if item['created_at'] else ''  # 只显示日期时间部分
                
                df_data.append([
                    item['id'],
                    item['question'],
                    item['sql'],
                    item['description'],
                    tags_str,
                    item['rating'],
                    item['usage_count'],
                    created_time
                ])
            
            df = pd.DataFrame(df_data, columns=[
                'ID', '问题', 'SQL查询', '描述', '标签', '评分', '使用次数', '创建时间'
            ])
            
            return df
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"获取知识库表格失败: {str(e)}")
            return pd.DataFrame(columns=['ID', '问题', 'SQL查询', '描述', '标签', '评分', '使用次数', '创建时间'])
    
    def add_knowledge_item(self, question: str, sql: str, description: str = "", tags: str = "") -> str:
        """添加知识库条目"""
        if not question.strip() or not sql.strip():
            return "❌ 问题和SQL查询不能为空"
        
        try:
            # 使用认证后的orchestrator或基础orchestrator
            orchestrator = self.authenticated_orchestrator or self.base_orchestrator
            if not orchestrator:
                return "❌ 系统未初始化，请稍后重试"
            
            # 解析标签
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []
            
            success = orchestrator.knowledge_manager.add_knowledge_item(
                question=question.strip(),
                sql=sql.strip(),
                description=description.strip(),
                tags=tag_list,
                rating=1.0
            )
            
            if success:
                return "✅ 知识库条目添加成功"
            else:
                return "❌ 添加失败，请检查知识库状态"
                
        except Exception as e:
            return f"❌ 添加失败: {str(e)}"
    
    def update_knowledge_item(self, item_id: str, question: str, sql: str, 
                             description: str = "", tags: str = "") -> str:
        """更新知识库条目"""
        if not item_id or not question.strip() or not sql.strip():
            return "❌ ID、问题和SQL查询不能为空"
        
        try:
            # 使用认证后的orchestrator或基础orchestrator
            orchestrator = self.authenticated_orchestrator or self.base_orchestrator
            if not orchestrator:
                return "❌ 系统未初始化，请稍后重试"
            
            # 解析标签
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []
            
            success = orchestrator.knowledge_manager.update_knowledge_item(
                item_id=item_id,
                question=question.strip(),
                sql=sql.strip(),
                description=description.strip(),
                tags=tag_list
            )
            
            if success:
                return "✅ 知识库条目更新成功"
            else:
                return "❌ 更新失败，条目可能不存在"
                
        except Exception as e:
            return f"❌ 更新失败: {str(e)}"
    
    def delete_knowledge_item(self, item_id: str) -> str:
        """删除知识库条目"""
        if not item_id:
            return "❌ 请提供条目ID"
        
        try:
            # 使用认证后的orchestrator或基础orchestrator
            orchestrator = self.authenticated_orchestrator or self.base_orchestrator
            if not orchestrator:
                return "❌ 系统未初始化，请稍后重试"
            
            success = orchestrator.knowledge_manager.delete_knowledge_item(item_id)
            
            if success:
                return "✅ 知识库条目删除成功"
            else:
                return "❌ 删除失败，条目可能不存在"
                
        except Exception as e:
            return f"❌ 删除失败: {str(e)}"
    
    def get_knowledge_item_by_id(self, item_id: str) -> tuple:
        """根据ID获取知识库条目详情"""
        try:
            # 使用认证后的orchestrator或基础orchestrator
            orchestrator = self.authenticated_orchestrator or self.base_orchestrator
            if not orchestrator:
                return None
            
            items = orchestrator.knowledge_manager.get_all_knowledge_items()
            
            for item in items:
                if item['id'] == item_id:
                    tags_str = ', '.join(item['tags']) if item['tags'] else ''
                    return (
                        item['question'],
                        item['sql'],
                        item['description'],
                        tags_str,
                        f"✅ 已加载条目: {item_id}"
                    )
            
            return "", "", "", "", f"❌ 未找到条目: {item_id}"
            
        except Exception as e:
            return "", "", "", "", f"❌ 获取条目失败: {str(e)}"
    
    def export_knowledge_base(self) -> Tuple[str, str]:
        """导出知识库数据"""
        try:
            # 使用认证后的orchestrator或基础orchestrator
            orchestrator = self.authenticated_orchestrator or self.base_orchestrator
            if not orchestrator:
                return "❌ 导出失败", "系统未初始化"
            
            if not orchestrator.knowledge_manager.enabled:
                return "❌ 导出失败", "知识库未启用"
            
            # 获取所有知识库条目
            items = orchestrator.knowledge_manager.get_all_knowledge_items()
            
            if not items:
                return "⚠️ 无数据", "知识库中没有数据可导出"
            
            # 构建导出数据
            export_data = {
                "version": "1.0",
                "export_time": datetime.now().isoformat(),
                "total_items": len(items),
                "items": items
            }
            
            # 转换为JSON字符串
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            
            return "✅ 导出成功", json_str
            
        except Exception as e:
            return "❌ 导出失败", f"导出过程中出错: {str(e)}"
    
    def import_knowledge_base(self, json_data: str) -> str:
        """导入知识库数据"""
        try:
            # 使用认证后的orchestrator或基础orchestrator
            orchestrator = self.authenticated_orchestrator or self.base_orchestrator
            if not orchestrator:
                return "❌ 系统未初始化，无法导入数据"
            
            if not orchestrator.knowledge_manager.enabled:
                return "❌ 知识库未启用，无法导入数据"
            
            if not json_data.strip():
                return "❌ 请提供有效的JSON数据"
            
            # 解析JSON数据
            try:
                import_data = json.loads(json_data)
            except json.JSONDecodeError as e:
                return f"❌ JSON格式错误: {str(e)}"
            
            # 验证数据格式
            if not isinstance(import_data, dict) or 'items' not in import_data:
                return "❌ 数据格式错误，缺少必要的'items'字段"
            
            items = import_data.get('items', [])
            if not isinstance(items, list):
                return "❌ 'items'字段必须是数组格式"
            
            # 导入数据
            success_count = 0
            error_count = 0
            
            for item in items:
                try:
                    # 验证必要字段
                    if not item.get('question') or not item.get('sql'):
                        error_count += 1
                        continue
                    
                    # 添加到知识库
                    success = orchestrator.knowledge_manager.add_positive_feedback(
                        question=item['question'],
                        sql=item['sql'],
                        description=item.get('description', '导入的知识库条目'),
                        metadata={
                            'imported': True,
                            'import_time': datetime.now().isoformat(),
                            'original_tags': item.get('tags', []),
                            'original_rating': item.get('rating', 1.0),
                            'original_usage_count': item.get('usage_count', 0)
                        }
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"导入单个条目失败: {str(e)}")
                    error_count += 1
            
            # 返回导入结果
            if success_count > 0:
                result_msg = f"✅ 导入完成：成功 {success_count} 条"
                if error_count > 0:
                    result_msg += f"，失败 {error_count} 条"
                return result_msg
            else:
                return f"❌ 导入失败：所有 {error_count} 条数据都导入失败"
                
        except Exception as e:
            return f"❌ 导入失败: {str(e)}"

    # 系统管理功能
    def test_connection(self) -> Tuple[str, str]:
        """测试数据库连接（根据用户权限）"""    
        try:
            if self.is_authenticated():
                # 使用认证包装器测试连接
                if not self.authenticated_orchestrator:
                    return "❌ 连接失败", "认证系统未初始化"
                
                # 尝试获取用户可访问的schema信息来测试连接
                schema_info = self.authenticated_orchestrator.get_schema_info()
                
                if "error" in schema_info:
                    return "❌ 连接失败", f"用户连接测试失败: {schema_info['error']}"
                
                # 获取用户可访问的schema数量
                accessible_schemas = getattr(self.last_query_result, 'accessible_schemas', []) if self.last_query_result else []
                schema_count = len(accessible_schemas)
                
                info = f"""
### 🔗 数据库连接成功 (用户: {self.current_user.employee_id})
- **数据库类型**: {config.database.type}
- **主机**: {config.database.host}:{config.database.port}
- **数据库**: {config.database.database}
- **可访问Schema数量**: {schema_count}个
- **可访问Schema**: {', '.join(accessible_schemas) if accessible_schemas else '无'}
- **连接状态**: ✅ 正常
- **权限状态**: ✅ 已认证
                """
                
                return "✅ 连接成功", info
            else:
                # 未认证用户，测试基础连接
                if not self.connector:
                    return "❌ 连接失败", "数据库连接器未初始化，请先登录"
                
                return "⚠️ 未认证", "请先登录以测试您的数据库访问权限"
                
        except Exception as e:
            return "❌ 连接失败", f"连接测试失败: {str(e)}"
    
    def get_schema_info(self) -> Tuple[str, str]:
        """获取数据库Schema信息（根据用户权限过滤）"""
        try:
            if self.is_authenticated():
                # 使用认证包装器获取过滤后的schema信息
                schema_info = self.authenticated_orchestrator.get_schema_info()
                
                if "error" in schema_info:
                    return "❌ 获取失败", schema_info["error"]
                
                # 构建用户特定的schema信息显示
                user_info = f"### 📊 数据库Schema信息 (用户: {self.current_user.employee_id})\n\n"
                
                # 获取用户可访问的schema列表
                accessible_schemas = getattr(self.last_query_result, 'accessible_schemas', []) if self.last_query_result else []
                if accessible_schemas:
                    user_info += f"🔐 **您可访问的Schema**: {', '.join(accessible_schemas)}\n\n"
                
                # 这里需要根据实际的schema_info结构来格式化显示
                if isinstance(schema_info, dict):
                    info_parts = [user_info]
                    
                    # 简单的schema信息显示
                    for key, value in schema_info.items():
                        if key != "error":
                            info_parts.append(f"**{key}**: {str(value)[:500]}...")
                    
                    return "✅ 获取成功", "\n".join(info_parts)
                else:
                    return "✅ 获取成功", user_info + str(schema_info)
            else:
                # 未认证用户，使用基础schema管理器
                if not self.schema_manager:
                    return "❌ 获取失败", "Schema管理器未初始化，请先登录"
                
                return "⚠️ 未认证", "请先登录以查看您有权限访问的Schema信息"
            
        except Exception as e:
            error_detail = f"获取Schema失败: {str(e)}\n\n详细错误:\n```\n{traceback.format_exc()}\n```"
            return "❌ 获取失败", error_detail
    
    def refresh_schema(self) -> Tuple[str, str]:
        """刷新Schema缓存"""
        try:
            # 使用认证包装器或基础orchestrator
            orchestrator = self.authenticated_orchestrator if self.is_authenticated() else self.base_orchestrator
            if not orchestrator:
                return "❌ 错误", "系统未初始化，请先登录"
            
            success = orchestrator.refresh_schema()
            
            if success:
                user_info = f" (用户: {self.current_user.employee_id})" if self.is_authenticated() else ""
                return "✅ 刷新成功", f"Schema缓存已刷新{user_info}"
            else:
                return "❌ 刷新失败", "Schema缓存刷新失败"
                
        except Exception as e:
            return "❌ 刷新失败", f"刷新失败: {str(e)}"
    
    # 表元数据管理功能
    def get_table_list(self) -> List[str]:
        """获取所有表名列表"""
        try:
            if not self.schema_manager:
                print("Schema管理器未初始化")
                return []
            
            # 首先尝试直接获取表列表
            tables = self.schema_manager.get_all_tables()
            
            # 如果获取不到表，尝试强制刷新
            if not tables:
                print("表列表为空，尝试强制刷新...")
                tables = self.schema_manager.get_all_tables(force_refresh=True)
            
            print(f"获取到 {len(tables)} 个表")
            return tables
            
        except Exception as e:
            print(f"获取表列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """获取指定表的字段列表"""
        try:
            if not self.schema_manager or not table_name:
                return []
            
            table_schema = self.schema_manager.get_table_schema(table_name)
            columns = table_schema.get("columns", [])
            return [col.get("name", "") for col in columns if col.get("name")]
            
        except Exception as e:
            print(f"获取表字段失败: {e}")
            return []
    
    def get_table_metadata_info(self, table_name: str) -> Tuple[str, str, str, str, str]:
        """获取表的元数据信息"""
        try:
            if not self.metadata_manager or not table_name:
                return "", "", "", "", "请选择一个表"
            
            metadata = self.metadata_manager.get_table_metadata(table_name)
            
            if metadata:
                return (
                    metadata.business_name,
                    metadata.description, 
                    metadata.business_meaning,
                    metadata.category,
                    f"✅ 已加载表 {table_name} 的元数据"
                )
            else:
                return "", "", "", "", f"表 {table_name} 暂无自定义元数据"
                
        except Exception as e:
            return "", "", "", "", f"获取元数据失败: {str(e)}"
    
    def update_table_metadata_info(self, table_name: str, business_name: str, 
                                  description: str, business_meaning: str, 
                                  category: str) -> str:
        """更新表的元数据信息"""
        try:
            if not self.metadata_manager:
                return "❌ 元数据管理器未初始化"
            
            if not table_name:
                return "❌ 请选择一个表"
            
            success = self.metadata_manager.update_table_metadata(
                table_name=table_name,
                business_name=business_name.strip(),
                description=description.strip(),
                business_meaning=business_meaning.strip(),
                category=category.strip()
            )
            
            if success:
                return f"✅ 表 {table_name} 的元数据已更新"
            else:
                return f"❌ 更新表 {table_name} 的元数据失败"
                
        except Exception as e:
            return f"❌ 更新失败: {str(e)}"
    
    def get_column_metadata_info(self, table_name: str, column_name: str) -> Tuple[str, str, str, str, str]:
        """获取字段的元数据信息"""
        try:
            if not self.metadata_manager or not table_name or not column_name:
                return "", "", "", "", "请选择表和字段"
            
            metadata = self.metadata_manager.get_table_metadata(table_name)
            
            if metadata and column_name in metadata.columns:
                col_metadata = metadata.columns[column_name]
                examples_text = ", ".join(col_metadata.data_examples)
                return (
                    col_metadata.business_name,
                    col_metadata.description,
                    col_metadata.business_meaning,
                    examples_text,
                    f"✅ 已加载字段 {column_name} 的元数据"
                )
            else:
                return "", "", "", "", f"字段 {column_name} 暂无自定义元数据"
                
        except Exception as e:
            return "", "", "", "", f"获取字段元数据失败: {str(e)}"
    
    def update_column_metadata_info(self, table_name: str, column_name: str,
                                   business_name: str, description: str,
                                   business_meaning: str, data_examples: str) -> str:
        """更新字段的元数据信息"""
        try:
            if not self.metadata_manager:
                return "❌ 元数据管理器未初始化"
            
            if not table_name or not column_name:
                return "❌ 请选择表和字段"
            
            # 处理数据示例
            examples_list = []
            if data_examples.strip():
                examples_list = [ex.strip() for ex in data_examples.split(",") if ex.strip()]
            
            success = self.metadata_manager.update_column_metadata(
                table_name=table_name,
                column_name=column_name,
                business_name=business_name.strip(),
                description=description.strip(),
                business_meaning=business_meaning.strip(),
                data_examples=examples_list
            )
            
            if success:
                return f"✅ 字段 {table_name}.{column_name} 的元数据已更新"
            else:
                return f"❌ 更新字段 {table_name}.{column_name} 的元数据失败"
                
        except Exception as e:
            return f"❌ 更新失败: {str(e)}"
    
    def export_table_metadata(self) -> Tuple[str, str]:
        """导出表元数据"""
        try:
            if not self.metadata_manager:
                return "❌ 导出失败", "元数据管理器未初始化"
            
            metadata = self.metadata_manager.export_metadata()
            
            if metadata:
                # 转换为JSON字符串
                json_str = json.dumps(metadata, ensure_ascii=False, indent=2)
                return "✅ 导出成功", json_str
            else:
                return "⚠️ 无数据", "暂无元数据可导出"
                
        except Exception as e:
            return "❌ 导出失败", f"导出失败: {str(e)}"
    
    def import_table_metadata(self, json_data: str) -> str:
        """导入表元数据"""
        try:
            if not self.metadata_manager:
                return "❌ 元数据管理器未初始化"
            
            if not json_data.strip():
                return "❌ 请输入有效的JSON数据"
            
            # 解析JSON数据
            import_data = json.loads(json_data)
            
            success = self.metadata_manager.import_metadata(import_data)
            
            if success:
                return "✅ 元数据导入成功"
            else:
                return "❌ 元数据导入失败"
                
        except json.JSONDecodeError as e:
            return f"❌ JSON格式错误: {str(e)}"
        except Exception as e:
            return f"❌ 导入失败: {str(e)}"
    
    def get_columns_dataframe(self, table_name: str) -> Tuple[pd.DataFrame, str]:
        """获取表的字段信息DataFrame，从数据库字段备注加载描述信息"""
        try:
            if not table_name:
                return pd.DataFrame(), "请选择一个表"
            
            if not self.schema_manager:
                return pd.DataFrame(), "Schema管理器未初始化"
            
            # 获取表结构信息
            table_schema = self.schema_manager.get_table_schema(table_name)
            columns = table_schema.get("columns", [])
            
            if not columns:
                return pd.DataFrame(), f"表 {table_name} 没有字段信息"
            
            # 获取表的元数据
            table_metadata = None
            if self.metadata_manager:
                table_metadata = self.metadata_manager.get_table_metadata(table_name)
            
            # 构建DataFrame数据
            df_data = []
            for col in columns:
                col_name = col.get("name", "")
                col_type = col.get("type", "")
                db_comment = col.get("comment", "")  # 从数据库获取字段备注
                
                # 获取字段的元数据
                business_name = ""
                description = db_comment  # 默认使用数据库备注作为描述
                business_meaning = ""
                data_examples = ""
                
                if table_metadata and col_name in table_metadata.columns:
                    col_metadata = table_metadata.columns[col_name]
                    business_name = col_metadata.business_name
                    # 如果有自定义描述，使用自定义描述，否则使用数据库备注
                    if col_metadata.description:
                        description = col_metadata.description
                    business_meaning = col_metadata.business_meaning
                    data_examples = ", ".join(col_metadata.data_examples)
                
                df_data.append([
                    col_name,
                    col_type,
                    business_name,
                    description,
                    business_meaning,
                    data_examples
                ])
            
            df = pd.DataFrame(df_data, columns=[
                "字段名", "数据类型", "业务名称", "字段描述", "业务含义", "数据示例"
            ])
            
            return df, f"✅ 已加载表 {table_name} 的 {len(df)} 个字段（包含数据库备注信息）"
            
        except Exception as e:
            return pd.DataFrame(), f"获取字段信息失败: {str(e)}"
    
    def update_columns_from_dataframe(self, table_name: str, df: pd.DataFrame) -> str:
        """从DataFrame更新字段元数据，同时更新数据库字段备注"""
        try:
            if not table_name:
                return "❌ 请选择一个表"
            
            if not self.metadata_manager:
                return "❌ 元数据管理器未初始化"
            
            if not self.connector:
                return "❌ 数据库连接器未初始化"
            
            if df is None or df.empty:
                return "❌ 没有数据可更新"
            
            success_count = 0
            error_count = 0
            db_update_count = 0
            
            for index, row in df.iterrows():
                try:
                    col_name = str(row.get("字段名", "")).strip()
                    if not col_name:
                        continue
                    
                    business_name = str(row.get("业务名称", "")).strip()
                    description = str(row.get("字段描述", "")).strip()
                    business_meaning = str(row.get("业务含义", "")).strip()
                    data_examples_str = str(row.get("数据示例", "")).strip()
                    
                    # 处理数据示例
                    data_examples = []
                    if data_examples_str:
                        data_examples = [ex.strip() for ex in data_examples_str.split(",") if ex.strip()]
                    
                    # 更新字段元数据到本地缓存
                    metadata_success = self.metadata_manager.update_column_metadata(
                        table_name=table_name,
                        column_name=col_name,
                        business_name=business_name,
                        description=description,
                        business_meaning=business_meaning,
                        data_examples=data_examples
                    )
                    
                    # 如果字段描述不为空，同时更新数据库字段备注
                    db_success = True
                    if description and hasattr(self.connector, 'update_column_comment'):
                        try:
                            db_success = self.connector.update_column_comment(
                                table_name=table_name,
                                column_name=col_name,
                                comment=description
                            )
                            if db_success:
                                db_update_count += 1
                        except Exception as e:
                            print(f"更新数据库字段备注失败 {col_name}: {e}")
                            db_success = False
                    
                    if metadata_success:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    print(f"更新字段 {col_name} 失败: {e}")
            
            # 构建返回消息
            result_parts = []
            if error_count == 0:
                result_parts.append(f"✅ 成功更新 {success_count} 个字段的元数据")
            else:
                result_parts.append(f"⚠️ 元数据更新：成功 {success_count} 个，失败 {error_count} 个")
            
            if db_update_count > 0:
                result_parts.append(f"📝 同时更新了 {db_update_count} 个字段的数据库备注")
            
            return "；".join(result_parts)
                
        except Exception as e:
            return f"❌ 批量更新失败: {str(e)}"
    
    def refresh_data_examples(self, table_name: str) -> Tuple[pd.DataFrame, str]:
        """刷新表的数据示例"""
        try:
            if not table_name:
                return pd.DataFrame(), "请选择一个表"
            
            if not self.connector:
                return pd.DataFrame(), "数据库连接器未初始化"
            
            # 执行查询获取示例数据
            sql_query = f"SELECT * FROM {table_name} LIMIT 2"
            
            try:
                # 使用SQL执行器获取数据
                from chatbi.database import get_sql_executor
                sql_executor = get_sql_executor()
                result = sql_executor.execute(sql_query)
                
                if not result.success or not result.data:
                    # 即使没有数据，也返回当前的字段信息
                    df, status = self.get_columns_dataframe(table_name)
                    return df, f"⚠️ 表 {table_name} 中没有数据或查询失败，但已显示字段结构"
                
                # 处理示例数据
                examples_dict = {}
                for row in result.data:
                    for col_name, value in row.items():
                        if col_name not in examples_dict:
                            examples_dict[col_name] = []
                        
                        # 格式化值
                        if value is not None:
                            formatted_value = str(value).strip()
                            if formatted_value and formatted_value not in examples_dict[col_name]:
                                examples_dict[col_name].append(formatted_value)
                
                # 更新元数据中的数据示例
                if self.metadata_manager:
                    for col_name, examples in examples_dict.items():
                        # 获取现有的元数据
                        existing_metadata = self.metadata_manager.get_table_metadata(table_name)
                        existing_col_metadata = None
                        if existing_metadata and col_name in existing_metadata.columns:
                            existing_col_metadata = existing_metadata.columns[col_name]
                        
                        # 保留现有的业务信息，只更新数据示例
                        self.metadata_manager.update_column_metadata(
                            table_name=table_name,
                            column_name=col_name,
                            business_name=existing_col_metadata.business_name if existing_col_metadata else "",
                            description=existing_col_metadata.description if existing_col_metadata else "",
                            business_meaning=existing_col_metadata.business_meaning if existing_col_metadata else "",
                            data_examples=examples
                        )
                
                # 重新获取更新后的字段信息
                df, _ = self.get_columns_dataframe(table_name)
                return df, f"✅ 已刷新表 {table_name} 的数据示例，获取了 {len(result.data)} 行示例数据"
                
            except Exception as e:
                # 查询失败时，仍然返回字段结构
                df, _ = self.get_columns_dataframe(table_name)
                return df, f"⚠️ 获取数据示例失败: {str(e)}，但已显示字段结构"
                
        except Exception as e:
            return pd.DataFrame(), f"刷新数据示例失败: {str(e)}"
    
    def load_table_with_examples(self, table_name: str) -> Tuple[pd.DataFrame, str]:
        """加载表字段信息并自动获取数据示例"""
        try:
            if not table_name:
                return pd.DataFrame(), "请选择一个表"
            
            # 首先加载字段信息
            df, status = self.get_columns_dataframe(table_name)
            
            if df.empty:
                return df, status
            
            # 自动获取数据示例
            try:
                df_with_examples, example_status = self.refresh_data_examples(table_name)
                if not df_with_examples.empty:
                    return df_with_examples, f"✅ 已加载表 {table_name} 的字段信息并自动获取数据示例"
                else:
                    return df, f"✅ 已加载表 {table_name} 的字段信息，但无法获取数据示例"
            except Exception as e:
                return df, f"✅ 已加载表 {table_name} 的字段信息，数据示例获取失败: {str(e)}"
                
        except Exception as e:
            return pd.DataFrame(), f"加载表信息失败: {str(e)}"


def create_authenticated_chatbi_app() -> gr.Blocks:
    """创建带认证功能的ChatBI应用"""
    
    # 创建应用实例
    app = ChatBIApp()
    
    # 自定义CSS样式
    custom_css = """
    .user-info-box {
        background-color: #f0f8ff;
        border: 1px solid #4CAF50;
        border-radius: 8px;
        padding: 10px;
        margin: 10px 0;
    }
    .login-box {
        background-color: #fff8dc;
        border: 1px solid #ffa500;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .error-message {
        color: #d32f2f;
        font-weight: bold;
    }
    .success-message {
        color: #388e3c;
        font-weight: bold;
    }
    """
    
    with gr.Blocks(
        title="ChatBI 智能数据查询系统",
        theme=gr.themes.Soft(),
        css=custom_css
    ) as demo:
        
        # 应用状态
        user_state = gr.State({})
        login_state = gr.State(False)
        
        # 标题
        gr.Markdown("# 🤖 ChatBI 智能数据查询系统")
        gr.Markdown("基于自然语言的智能数据分析平台，支持用户认证和权限管理")
        
        # 用户信息显示区域
        with gr.Row():
            user_info_display = gr.Markdown("", elem_classes=["user-info-box"], visible=False)
        
        # 主要内容区域
        with gr.Tab("💬 智能查询") as chat_tab:
            with gr.Row():
                with gr.Column(scale=3):
                    # 聊天界面
                    chatbot = gr.Chatbot(
                        label="ChatBI 对话",
                        height=500,
                        show_label=True,
                        container=True,
                        bubble_full_width=False
                    )
                    
                    # 输入区域
                    with gr.Row():
                        msg_input = gr.Textbox(
                            label="输入您的问题",
                            placeholder="例如：显示不同物料的预算情况（请先登录）",
                            scale=4,
                            container=False
                        )
                        send_btn = gr.Button("发送", variant="primary", scale=1)
                    
                    # 查询选项
                    with gr.Row():
                        auto_viz_checkbox = gr.Checkbox(
                            label="自动生成可视化",
                            value=True
                        )
                        enable_analysis_checkbox = gr.Checkbox(
                            label="启用数据分析",
                            value=False
                        )
                        analysis_level_dropdown = gr.Dropdown(
                            label="分析级别",
                            choices=["basic", "standard", "detailed"],
                            value="standard"
                        )
                
                with gr.Column(scale=1):
                    # 可视化显示区域
                    plot_output = gr.Plot(
                        label="数据可视化",
                        visible=True
                    )
                    
                    # 反馈区域
                    gr.Markdown("### 📝 查询反馈")
                    feedback_description = gr.Textbox(
                        label="反馈描述（可选）",
                        placeholder="请描述您对查询结果的看法"
                    )
                    
                    with gr.Row():
                        like_btn = gr.Button("👍 点赞", variant="secondary")
                        feedback_output = gr.Textbox(
                            label="反馈状态",
                            interactive=False,
                            max_lines=2
                        )
        
        # 登录/注册标签页
        with gr.Tab("🔐 用户认证") as auth_tab:
            with gr.Row():
                # 登录区域
                with gr.Column(scale=1):
                    gr.Markdown("### 用户登录")
                    
                    login_employee_id = gr.Textbox(
                        label="工号",
                        placeholder="请输入您的工号"
                    )
                    login_password = gr.Textbox(
                        label="密码",
                        type="password",
                        placeholder="请输入密码"
                    )
                    
                    with gr.Row():
                        login_btn = gr.Button("登录", variant="primary")
                        logout_btn = gr.Button("登出", variant="secondary", visible=False)
                    
                    login_message = gr.Textbox(
                        label="登录状态",
                        interactive=False,
                        max_lines=3
                    )
                
                # 注册区域
                with gr.Column(scale=1):
                    gr.Markdown("### 用户注册")
                    
                    reg_employee_id = gr.Textbox(
                        label="工号",
                        placeholder="请输入您的工号"
                    )
                    reg_password = gr.Textbox(
                        label="密码",
                        type="password",
                        placeholder="请输入密码"
                    )
                    reg_confirm_password = gr.Textbox(
                        label="确认密码",
                        type="password",
                        placeholder="请再次输入密码"
                    )
                    reg_email = gr.Textbox(
                        label="邮箱（可选）",
                        placeholder="请输入邮箱地址"
                    )
                    reg_full_name = gr.Textbox(
                        label="姓名（可选）",
                        placeholder="请输入您的姓名"
                    )
                    
                    register_btn = gr.Button("注册", variant="primary")
                    register_message = gr.Textbox(
                        label="注册状态",
                        interactive=False,
                        max_lines=3
                    )
        
        # SQL知识库管理标签页
        with gr.Tab("🐬 SQL知识库") as knowledge_tab:
            gr.Markdown("""
            ## 🌿 SQL知识库管理
            
            通过RAG技术提升SQL生成的准确性和一致性。
            """)
            
            with gr.Row():
                with gr.Column():
                    # 知识库表格管理
                    gr.Markdown("### 📊 知识库条目管理")
                    with gr.Row():
                        refresh_table_btn = gr.Button("🔄 刷新表格", variant="secondary", size="sm")
                        add_new_btn = gr.Button("➕ 添加新条目", variant="primary", size="sm")
                    
                    knowledge_table = gr.Dataframe(
                        headers=['ID', '问题', 'SQL查询', '描述', '标签', '评分', '使用次数', '创建时间'],
                        datatype=['str', 'str', 'str', 'str', 'str', 'number', 'number', 'str'],
                        interactive=False,
                        wrap=True
                    )
                    
                    # 编辑面板
                    gr.Markdown("### ✏️ 编辑条目")
                    
                    selected_id = gr.Textbox(
                        label="条目ID",
                        placeholder="从表格中选择条目后自动填充",
                        interactive=False
                    )
                    
                    with gr.Row():
                        with gr.Column():
                            edit_question = gr.Textbox(
                                label="问题",
                                placeholder="输入自然语言问题",
                                lines=2
                            )
                            
                            edit_sql = gr.Textbox(
                                label="SQL查询",
                                placeholder="输入SQL查询语句",
                                lines=3
                            )
                        
                        with gr.Column():
                            edit_description = gr.Textbox(
                                label="描述",
                                placeholder="输入查询描述（可选）",
                                lines=2
                            )
                            
                            edit_tags = gr.Textbox(
                                label="标签",
                                placeholder="输入标签，用逗号分隔",
                                lines=1
                            )
                    
                    with gr.Row():
                        update_btn = gr.Button("💾 更新", variant="primary", size="sm")
                        delete_btn = gr.Button("🗑️ 删除", variant="stop", size="sm")
                    
                    edit_result = gr.Markdown("")
                    
                    # 添加新条目面板
                    gr.Markdown("### ➕ 添加新条目")
                    
                    with gr.Row():
                        with gr.Column():
                            new_question = gr.Textbox(
                                label="问题",
                                placeholder="输入自然语言问题",
                                lines=2
                            )
                            
                            new_sql = gr.Textbox(
                                label="SQL查询",
                                placeholder="输入SQL查询语句",
                                lines=3
                            )
                        
                        with gr.Column():
                            new_description = gr.Textbox(
                                label="描述",
                                placeholder="输入查询描述（可选）",
                                lines=2
                            )
                            
                            new_tags = gr.Textbox(
                                label="标签",
                                placeholder="输入标签，用逗号分隔（可选）",
                                lines=1
                            )
                    
                    add_btn = gr.Button("➕ 添加到知识库", variant="primary")
                    add_result = gr.Markdown("")
                    
                    # 知识库统计
                    gr.Markdown("### 📊 知识库统计")
                    refresh_stats_btn = gr.Button("🔄 刷新统计", variant="secondary")
                    knowledge_stats = gr.Markdown("点击'刷新统计'查看知识库状态")
                    
                    # 数据导入导出
                    gr.Markdown("### 📤 数据导入导出")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("**📤 导出知识库**")
                            export_kb_btn = gr.Button("📤 导出知识库", variant="secondary", size="sm")
                            export_kb_status = gr.Textbox(label="导出状态", interactive=False, lines=1)
                            export_kb_data = gr.Textbox(
                                label="导出数据",
                                lines=8,
                                interactive=False,
                                placeholder="导出的JSON数据将显示在这里，可复制保存"
                            )
                        
                        with gr.Column():
                            gr.Markdown("**📥 导入知识库**")
                            import_kb_data = gr.Textbox(
                                label="导入数据",
                                lines=8,
                                placeholder="请粘贴要导入的JSON数据"
                            )
                            import_kb_btn = gr.Button("📥 导入知识库", variant="primary", size="sm")
                            import_kb_status = gr.Textbox(label="导入状态", interactive=False, lines=1)
                    
                    # 使用说明
                    gr.Markdown("""
                    ### 💡 使用说明
                    
                    **如何使用知识库功能：**
                    1. 在对话界面进行查询
                    2. 如果结果满意，点击"👍 添加到知识库"按钮
                    3. 可选择添加描述信息，帮助系统更好地理解查询用途
                    4. 系统会自动学习，提升后续相似查询的准确性
                    
                    **RAG工作原理：**
                    - 🔍 **智能检索**: 自动搜索相似的历史查询
                    - 🎯 **策略选择**: 根据相似度选择最佳生成策略
                    - 📈 **持续改进**: 基于用户反馈不断优化
                    - 🚀 **性能提升**: 减少重复生成，提高响应速度
                    """)

        # 表信息维护标签页
        with gr.Tab("📝 表信息维护") as metadata_tab:
            gr.Markdown("""
            ## 📝 表信息维护
            
            通过维护表和字段的业务信息，提高SQL生成的准确率和可理解性。
            """)
            
            with gr.Tabs():
                # 表信息管理
                with gr.TabItem("📊 表信息管理"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 选择表")
                            table_dropdown = gr.Dropdown(
                                label="选择表",
                                choices=app.get_table_list(),
                                interactive=True,
                                allow_custom_value=False
                            )
                            
                            load_table_btn = gr.Button("加载表信息", variant="primary")
                            table_status = gr.Textbox(label="状态", interactive=False)
                        
                        with gr.Column(scale=2):
                            gr.Markdown("### 表元数据")
                            
                            table_business_name = gr.Textbox(
                                label="业务名称",
                                placeholder="例如：用户信息表",
                                lines=1
                            )
                            
                            table_description = gr.Textbox(
                                label="表描述",
                                placeholder="例如：存储系统用户的基本信息",
                                lines=2
                            )
                            
                            table_business_meaning = gr.Textbox(
                                label="业务含义",
                                placeholder="例如：记录注册用户的详细资料，包括个人信息和账户状态",
                                lines=3
                            )
                            
                            table_category = gr.Textbox(
                                label="业务分类",
                                placeholder="例如：用户管理、基础数据",
                                lines=1
                            )
                            
                            save_table_btn = gr.Button("保存表信息", variant="primary")
                
                # 字段信息管理
                with gr.TabItem("🏷️ 字段信息管理"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 表选择与操作")
                            
                            column_table_dropdown = gr.Dropdown(
                                label="选择表",
                                choices=app.get_table_list(),
                                interactive=True,
                                allow_custom_value=False
                            )
                            
                            with gr.Row():
                                load_columns_btn = gr.Button("📋 加载字段", variant="primary", size="sm")
                                refresh_examples_btn = gr.Button("🔄 刷新示例", variant="secondary", size="sm")
                            
                            column_status = gr.Textbox(label="操作状态", interactive=False, lines=3)
                            
                            gr.Markdown("### 💡 使用说明")
                            gr.Markdown("""
                            **操作步骤：**
                            1. 选择要管理的表
                            2. 点击"📋 加载字段"获取字段列表和数据库备注
                            3. 点击"🔄 刷新示例"自动获取真实数据示例
                            4. 直接在表格中编辑字段元数据信息
                            5. 修改后自动保存到本地缓存和数据库
                            
                            **字段说明：**
                            - **字段名**：数据库字段名（只读）
                            - **数据类型**：字段数据类型（只读）
                            - **业务名称**：字段的中文业务名称
                            - **字段描述**：会同步更新到数据库字段备注
                            - **业务含义**：字段在业务场景中的具体含义
                            - **数据示例**：自动从数据库获取的真实数据样例
                            
                            **重要提示：**
                            - 字段描述会同时更新数据库的COMMENT信息
                            - 所有元数据会用于AI生成SQL时的参考
                            - 建议填写准确、详细的业务信息以提高查询效果
                            """)
                        
                        with gr.Column(scale=3):
                            gr.Markdown("### 📊 字段元数据管理")
                            gr.Markdown("*在下方表格中直接编辑字段信息，修改后会自动保存到系统中*")
                            
                            columns_dataframe = gr.Dataframe(
                                headers=["字段名", "数据类型", "业务名称", "字段描述", "业务含义", "数据示例"],
                                datatype=["str", "str", "str", "str", "str", "str"],
                                interactive=True,
                                wrap=True,
                                label="字段信息表格"
                            )
                
                # 数据导入导出
                with gr.TabItem("📤 数据管理"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 📤 导出元数据")
                            export_btn = gr.Button("导出元数据", variant="primary")
                            export_status = gr.Textbox(label="导出状态", interactive=False)
                            export_data = gr.Textbox(
                                label="导出数据",
                                lines=10,
                                interactive=False,
                                placeholder="导出的JSON数据将显示在这里"
                            )
                        
                        with gr.Column():
                            gr.Markdown("### 📥 导入元数据")
                            import_data = gr.Textbox(
                                label="导入数据",
                                lines=10,
                                placeholder="请粘贴要导入的JSON数据"
                            )
                            import_btn = gr.Button("导入元数据", variant="primary")
                            import_status = gr.Textbox(label="导入状态", interactive=False)

        # 系统信息标签页
        with gr.Tab("ℹ️ 系统信息") as info_tab:
            gr.Markdown("### 系统状态")
            
            with gr.Row():
                test_conn_btn = gr.Button("测试数据库连接")
                refresh_schema_btn = gr.Button("刷新Schema缓存")
                get_schema_btn = gr.Button("获取Schema信息")
            
            system_status = gr.Textbox(
                label="系统状态",
                interactive=False,
                max_lines=10
            )
            
            gr.Markdown("### 知识库信息")
            knowledge_stats_btn = gr.Button("获取知识库统计")
            knowledge_stats_output = gr.Textbox(
                label="知识库统计",
                interactive=False,
                max_lines=15
            )
            
            gr.Markdown("### 使用说明")
            gr.Markdown("""
            **使用步骤：**
            1. 在"用户认证"标签页中登录或注册账户
            2. 登录成功后，在"智能查询"标签页中输入自然语言问题
            3. 系统会根据您的权限自动过滤可访问的数据
            4. 查看查询结果和可视化图表
            5. 可以对查询结果进行反馈
            
            **权限说明：**
            - 不同用户具有不同的数据库访问权限
            - 系统会自动过滤您无权访问的数据
            - 如有权限问题，请联系管理员
            
            **注意事项：**
            - 请妥善保管您的登录凭据
            - 定期更换密码以确保账户安全
            - 如遇问题请及时联系技术支持
            """)
        
        # 事件处理函数
        def handle_login(employee_id, password):
            """处理登录"""
            success, message, user_info = app.login_user(employee_id, password)
            
            if success:
                # 更新界面状态
                user_display = f"""
                **当前用户:** {user_info['employee_id']} ({user_info['full_name']})
                **邮箱:** {user_info['email']}
                **管理员:** {'是' if user_info['is_admin'] else '否'}
                **登录时间:** {user_info['login_time']}
                """
                
                return (
                    True,  # login_state
                    user_info,  # user_state
                    user_display,  # user_info_display
                    message,  # login_message
                    "",  # clear employee_id
                    "",  # clear password
                    gr.update(visible=False),  # login_btn
                    gr.update(visible=True),   # logout_btn
                    "例如：显示最近一周的销售数据"  # update placeholder
                )
            else:
                return (
                    False,  # login_state
                    {},  # user_state
                    "",  # user_info_display
                    message,  # login_message
                    employee_id,  # keep employee_id
                    "",  # clear password
                    gr.update(visible=True),   # login_btn
                    gr.update(visible=False),  # logout_btn
                    "例如：显示最近一周的销售数据（请先登录）"  # keep placeholder
                )
        
        def handle_logout():
            """处理登出"""
            success, message = app.logout_user()
            
            return (
                False,  # login_state
                {},  # user_state
                "",  # user_info_display
                message,  # login_message
                "",  # clear employee_id
                "",  # clear password
                gr.update(visible=True),   # login_btn
                gr.update(visible=False),  # logout_btn
                "例如：显示最近一周的销售数据（请先登录）",  # update placeholder
                []  # clear chatbot
            )
        
        def handle_register(employee_id, password, confirm_password, email, full_name):
            """处理注册"""
            success, message = app.register_user(
                employee_id, password, confirm_password, email, full_name
            )
            
            if success:
                return message, "", "", "", "", ""  # clear all fields
            else:
                return message, employee_id, "", "", email, full_name  # keep non-password fields
        
        def handle_chat(message, history, auto_viz, enable_analysis, analysis_level):
            """处理聊天查询"""
            if not app.is_authenticated():
                history.append([message, "❌ 请先登录后再进行查询"])
                return history, "", None
            
            # 使用生成器处理流式响应
            for result in app.chat_query(message, history, auto_viz, enable_analysis, analysis_level):
                yield result
        
        def handle_feedback(description):
            """处理反馈"""
            result = app.add_positive_feedback(description)
            return result, ""  # clear description
        
        def handle_test_connection():
            """处理数据库连接测试"""
            status, info = app.test_connection()
            return f"{status}\n\n{info}"
        
        def handle_refresh_schema():
            """处理Schema刷新"""
            status, info = app.refresh_schema()
            return f"{status}\n\n{info}"
        
        def handle_get_schema():
            """处理获取Schema信息"""
            status, info = app.get_schema_info()
            return f"{status}\n\n{info}"
        
        def handle_knowledge_stats():
            """处理获取知识库统计"""
            return app.get_knowledge_stats()
        
        # 绑定事件
        login_btn.click(
            handle_login,
            inputs=[login_employee_id, login_password],
            outputs=[
                login_state, user_state, user_info_display,
                login_message, login_employee_id, login_password,
                login_btn, logout_btn, msg_input
            ]
        )
        
        logout_btn.click(
            handle_logout,
            outputs=[
                login_state, user_state, user_info_display,
                login_message, login_employee_id, login_password,
                login_btn, logout_btn, msg_input, chatbot
            ]
        )
        
        register_btn.click(
            handle_register,
            inputs=[reg_employee_id, reg_password, reg_confirm_password, reg_email, reg_full_name],
            outputs=[register_message, reg_employee_id, reg_password, reg_confirm_password, reg_email, reg_full_name]
        )
        
        # 聊天事件
        send_btn.click(
            handle_chat,
            inputs=[msg_input, chatbot, auto_viz_checkbox, enable_analysis_checkbox, analysis_level_dropdown],
            outputs=[chatbot, msg_input, plot_output]
        )
        
        msg_input.submit(
            handle_chat,
            inputs=[msg_input, chatbot, auto_viz_checkbox, enable_analysis_checkbox, analysis_level_dropdown],
            outputs=[chatbot, msg_input, plot_output]
        )
        
        # 反馈事件
        like_btn.click(
            handle_feedback,
            inputs=[feedback_description],
            outputs=[feedback_output, feedback_description]
        )
        
        # 系统信息事件
        test_conn_btn.click(
            handle_test_connection,
            outputs=[system_status]
        )
        
        refresh_schema_btn.click(
            handle_refresh_schema,
            outputs=[system_status]
        )
        
        get_schema_btn.click(
            handle_get_schema,
            outputs=[system_status]
        )
        
        knowledge_stats_btn.click(
            handle_knowledge_stats,
            outputs=[knowledge_stats_output]
        )
        
        # 知识库管理功能事件绑定
        refresh_stats_btn.click(
            fn=app.get_knowledge_stats,
            outputs=[knowledge_stats]
        )
        
        # 知识库导入导出功能
        export_kb_btn.click(
            fn=app.export_knowledge_base,
            outputs=[export_kb_status, export_kb_data]
        )
        
        import_kb_btn.click(
            fn=app.import_knowledge_base,
            inputs=[import_kb_data],
            outputs=[import_kb_status]
        ).then(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        ).then(
            fn=lambda: "",
            outputs=[import_kb_data]
        )
        
        # 知识库表格管理功能
        refresh_table_btn.click(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        )
        
        # 表格行选择事件
        def on_table_select(evt: gr.SelectData):
            if evt.index is not None and evt.index[0] is not None:
                # 获取选中行的数据
                df = app.get_knowledge_table()
                if not df.empty and evt.index[0] < len(df):
                    row = df.iloc[evt.index[0]]
                    return (
                        row['ID'],
                        row['问题'],
                        row['SQL查询'],
                        row['描述'],
                        row['标签'],
                        f"✅ 已选择条目: {row['ID']}"
                    )
            return "", "", "", "", "", "❌ 请选择有效的表格行"
        
        knowledge_table.select(
            fn=on_table_select,
            outputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags, edit_result]
        )
        
        # 更新条目
        update_btn.click(
            fn=app.update_knowledge_item,
            inputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags],
            outputs=[edit_result]
        ).then(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        )
        
        # 删除条目
        delete_btn.click(
            fn=app.delete_knowledge_item,
            inputs=[selected_id],
            outputs=[edit_result]
        ).then(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        ).then(
            fn=lambda: ("", "", "", "", ""),
            outputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags]
        )
        
        # 添加新条目
        add_btn.click(
            fn=app.add_knowledge_item,
            inputs=[new_question, new_sql, new_description, new_tags],
            outputs=[add_result]
        ).then(
            fn=lambda: ("", "", "", ""),
            outputs=[new_question, new_sql, new_description, new_tags]
        )
        
        # 快速添加按钮 - 清空编辑表单
        add_new_btn.click(
            fn=lambda: ("", "", "", "", ""),
            outputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags]
        )
        
        # 表信息维护功能事件绑定
        
        # 表信息管理
        load_table_btn.click(
            fn=app.get_table_metadata_info,
            inputs=[table_dropdown],
            outputs=[table_business_name, table_description, table_business_meaning, table_category, table_status]
        )
        
        save_table_btn.click(
            fn=app.update_table_metadata_info,
            inputs=[table_dropdown, table_business_name, table_description, table_business_meaning, table_category],
            outputs=[table_status]
        )
        
        # 字段信息管理 - 表格模式
        load_columns_btn.click(
            fn=app.load_table_with_examples,
            inputs=[column_table_dropdown],
            outputs=[columns_dataframe, column_status]
        )
        
        refresh_examples_btn.click(
            fn=app.refresh_data_examples,
            inputs=[column_table_dropdown],
            outputs=[columns_dataframe, column_status]
        )
        
        # 当表格数据变化时自动保存
        columns_dataframe.change(
            fn=app.update_columns_from_dataframe,
            inputs=[column_table_dropdown, columns_dataframe],
            outputs=[column_status]
        )
        
        # 数据导入导出
        export_btn.click(
            fn=app.export_table_metadata,
            outputs=[export_status, export_data]
        )
        
        import_btn.click(
            fn=app.import_table_metadata,
            inputs=[import_data],
            outputs=[import_status]
        )
        
        # 启动时初始化
        def load_initial_data():
            """启动时加载初始数据"""
            try:
                # 加载知识库统计
                stats = app.get_knowledge_stats()
                # 加载知识库表格
                kb_table = app.get_knowledge_table()
                return stats, kb_table
            except Exception as e:
                return f"❌ 初始化失败: {str(e)}", pd.DataFrame()
        
        demo.load(
            fn=load_initial_data,
            outputs=[knowledge_stats, knowledge_table]
        )
    
    return demo


def create_chat_interface():
    """创建对话式界面"""
    app = ChatBIApp()
    
    # 自定义CSS
    css = """
    .gradio-container {
        max-width: 1400px !important;
    }
    .chat-container {
        height: 600px !important;
    }
    .system-panel {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        background-color: #f8f9fa;
    }
    .input-row {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
    }
    .options-panel {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .feedback-panel {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
    }
    .chart-panel {
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px;
        background: #fafafa;
    }
    """
    
    with gr.Blocks(title="ChatBI 智能对话查询", css=css, theme=gr.themes.Soft()) as interface:
        
        gr.Markdown("""
        # 🤖 ChatBI 智能对话查询系统
        
        与AI助手对话，用自然语言查询数据库，获得SQL、数据、分析和可视化的完整回答。
        """)
        
        with gr.Tabs():
            # 主对话界面
            with gr.TabItem("💬 智能对话", elem_id="chat-tab"):
                with gr.Row():
                    with gr.Column(scale=3):
                        # 对话界面
                        chatbot = gr.Chatbot(
                            label="ChatBI 助手",
                            height=500,
                            show_label=True,
                            container=True,
                            bubble_full_width=False
                        )
                        
                        # 输入区域
                        with gr.Group(elem_classes="input-row"):
                            with gr.Row():
                                msg_input = gr.Textbox(
                                    label="输入您的问题",
                                    placeholder="例如：显示销售额最高的前10个区域",
                                    lines=2,
                                    scale=4,
                                    show_label=False
                                )
                                with gr.Column(scale=1):
                                    send_btn = gr.Button("🚀 发送", variant="primary", size="lg")
                                    clear_btn = gr.Button("🗑️ 清空对话", variant="secondary", size="sm")
                        
                        # 查询选项面板
                        with gr.Group(elem_classes="options-panel"):
                            gr.Markdown("### ⚙️ 查询选项")
                            with gr.Row():
                                auto_viz = gr.Checkbox(
                                    label="📊 自动可视化", 
                                    value=True,
                                    info="自动为查询结果生成图表"
                                )
                                enable_analysis = gr.Checkbox(
                                    label="🧠 智能分析", 
                                    value=False,
                                    info="对查询结果进行AI分析"
                                )
                            with gr.Row():
                                analysis_level = gr.Dropdown(
                                    label="分析级别",
                                    choices=[
                                        ("基础分析", "basic"), 
                                        ("标准分析", "standard"), 
                                        ("详细分析", "detailed")
                                    ],
                                    value="standard",
                                    info="选择数据分析的详细程度"
                                )
                        
                        # 反馈区域
                        with gr.Group(elem_classes="feedback-panel"):
                            gr.Markdown("### 💝 查询反馈")
                            with gr.Row():
                                with gr.Column(scale=3):
                                    feedback_description = gr.Textbox(
                                        label="反馈描述",
                                        placeholder="描述这个查询的用途或特点...",
                                        lines=1,
                                        show_label=False
                                    )
                                with gr.Column(scale=1):
                                    like_btn = gr.Button("👍 添加到知识库", variant="secondary", size="sm")
                            
                            feedback_result = gr.Markdown("", visible=False)
                    
                    with gr.Column(scale=2):
                        # 可视化展示区域
                        with gr.Group(elem_classes="chart-panel"):
                            gr.Markdown("### 📊 数据可视化")
                            chart_display = gr.Plot(
                                label="图表",
                                show_label=False,
                                container=True
                            )
                        
                        # 快速查询示例
                        with gr.Group():
                            gr.Markdown("### 💡 快速查询示例")
                            
                            example_btns = []
                            examples = [
                                "📊 显示所有表的记录数",
                                "🌍 按地区统计销售总额", 
                                "🏆 销售额最高的前10个客户",
                                "📈 最近一个月的销售趋势",
                                "👥 统计活跃用户数量",
                                "💰 查询今日销售额"
                            ]
                            
                            # 分两列显示示例按钮
                            with gr.Row():
                                with gr.Column():
                                    for i in range(0, len(examples), 2):
                                        btn = gr.Button(
                                            examples[i], 
                                            variant="outline", 
                                            size="sm",
                                            scale=1
                                        )
                                        example_btns.append(btn)
                                with gr.Column():
                                    for i in range(1, len(examples), 2):
                                        btn = gr.Button(
                                            examples[i], 
                                            variant="outline", 
                                            size="sm",
                                            scale=1
                                        )
                                        example_btns.append(btn)
            
            # SQL知识库界面
            with gr.TabItem("🐬 SQL知识库", elem_id="knowledge-tab"):
                gr.Markdown("""
                ## 🌿 SQL知识库管理
                
                通过RAG技术提升SQL生成的准确性和一致性。
                """)
                
                with gr.Row():
                    with gr.Column():
                        # 知识库表格管理
                        gr.Markdown("### 📊 知识库条目管理")
                        with gr.Row():
                            refresh_table_btn = gr.Button("🔄 刷新表格", variant="secondary", size="sm")
                            add_new_btn = gr.Button("➕ 添加新条目", variant="primary", size="sm")
                        
                        knowledge_table = gr.Dataframe(
                            headers=['ID', '问题', 'SQL查询', '描述', '标签', '评分', '使用次数', '创建时间'],
                            datatype=['str', 'str', 'str', 'str', 'str', 'number', 'number', 'str'],
                            interactive=False,
                            wrap=True
                        )
                        
                        # 编辑面板
                        gr.Markdown("### ✏️ 编辑条目")
                        
                        selected_id = gr.Textbox(
                            label="条目ID",
                            placeholder="从表格中选择条目后自动填充",
                            interactive=False
                        )
                        
                        with gr.Row():
                            with gr.Column():
                                edit_question = gr.Textbox(
                                    label="问题",
                                    placeholder="输入自然语言问题",
                                    lines=2
                                )
                                
                                edit_sql = gr.Textbox(
                                    label="SQL查询",
                                    placeholder="输入SQL查询语句",
                                    lines=3
                                )
                            
                            with gr.Column():
                                edit_description = gr.Textbox(
                                    label="描述",
                                    placeholder="输入查询描述（可选）",
                                    lines=2
                                )
                                
                                edit_tags = gr.Textbox(
                                    label="标签",
                                    placeholder="输入标签，用逗号分隔",
                                    lines=1
                                )
                        
                        with gr.Row():
                            update_btn = gr.Button("💾 更新", variant="primary", size="sm")
                            delete_btn = gr.Button("🗑️ 删除", variant="stop", size="sm")
                        
                        edit_result = gr.Markdown("")
                        
                        # 添加新条目面板
                        gr.Markdown("### ➕ 添加新条目")
                        
                        with gr.Row():
                            with gr.Column():
                                new_question = gr.Textbox(
                                    label="问题",
                                    placeholder="输入自然语言问题",
                                    lines=2
                                )
                                
                                new_sql = gr.Textbox(
                                    label="SQL查询",
                                    placeholder="输入SQL查询语句",
                                    lines=3
                                )
                            
                            with gr.Column():
                                new_description = gr.Textbox(
                                    label="描述",
                                    placeholder="输入查询描述（可选）",
                                    lines=2
                                )
                                
                                new_tags = gr.Textbox(
                                    label="标签",
                                    placeholder="输入标签，用逗号分隔（可选）",
                                    lines=1
                                )
                        
                        add_btn = gr.Button("➕ 添加到知识库", variant="primary")
                        add_result = gr.Markdown("")
                        
                        # 知识库统计
                        gr.Markdown("### 📊 知识库统计")
                        refresh_stats_btn = gr.Button("🔄 刷新统计", variant="secondary")
                        knowledge_stats = gr.Markdown("点击'刷新统计'查看知识库状态")
                        
                        # 数据导入导出
                        gr.Markdown("### 📤 数据导入导出")
                        
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("**📤 导出知识库**")
                                export_kb_btn = gr.Button("📤 导出知识库", variant="secondary", size="sm")
                                export_kb_status = gr.Textbox(label="导出状态", interactive=False, lines=1)
                                export_kb_data = gr.Textbox(
                                    label="导出数据",
                                    lines=8,
                                    interactive=False,
                                    placeholder="导出的JSON数据将显示在这里，可复制保存"
                                )
                            
                            with gr.Column():
                                gr.Markdown("**📥 导入知识库**")
                                import_kb_data = gr.Textbox(
                                    label="导入数据",
                                    lines=8,
                                    placeholder="请粘贴要导入的JSON数据"
                                )
                                import_kb_btn = gr.Button("📥 导入知识库", variant="primary", size="sm")
                                import_kb_status = gr.Textbox(label="导入状态", interactive=False, lines=1)
                        
                        # 使用说明
                        gr.Markdown("""
                        ### 💡 使用说明
                        
                        **如何使用知识库功能：**
                        1. 在对话界面进行查询
                        2. 如果结果满意，点击"👍 添加到知识库"按钮
                        3. 可选择添加描述信息，帮助系统更好地理解查询用途
                        4. 系统会自动学习，提升后续相似查询的准确性
                        
                        **RAG工作原理：**
                        - 🔍 **智能检索**: 自动搜索相似的历史查询
                        - 🎯 **策略选择**: 根据相似度选择最佳生成策略
                        - 📈 **持续改进**: 基于用户反馈不断优化
                        - 🚀 **性能提升**: 减少重复生成，提高响应速度
                        """)
            
            # 系统管理界面
            with gr.TabItem("🔧 系统管理", elem_id="system-tab"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("## 🔗 数据库连接")
                        
                        with gr.Row():
                            test_conn_btn = gr.Button("测试连接", variant="primary")
                            refresh_schema_btn = gr.Button("刷新Schema", variant="secondary")
                        
                        conn_status = gr.Textbox(label="连接状态", interactive=False)
                        conn_info = gr.Markdown("点击'测试连接'检查数据库状态")
                    
                    with gr.Column():
                        gr.Markdown("## 📊 Schema信息")
                        
                        get_schema_btn = gr.Button("获取Schema", variant="primary")
                        schema_status = gr.Textbox(label="获取状态", interactive=False)
                
                # Schema详细信息
                with gr.Row():
                    schema_display = gr.Markdown("点击'获取Schema'查看数据库结构")
            
            # 表信息维护界面
            with gr.TabItem("📝 表信息维护", elem_id="metadata-tab"):
                gr.Markdown("""
                ## 📝 表信息维护
                
                通过维护表和字段的业务信息，提高SQL生成的准确率和可理解性。
                """)
                
                with gr.Tabs():
                    # 表信息管理
                    with gr.TabItem("📊 表信息管理"):
                        with gr.Row():
                            with gr.Column(scale=1):
                                gr.Markdown("### 选择表")
                                table_dropdown = gr.Dropdown(
                                    label="选择表",
                                    choices=app.get_table_list(),
                                    interactive=True,
                                    allow_custom_value=False
                                )
                                
                                load_table_btn = gr.Button("加载表信息", variant="primary")
                                table_status = gr.Textbox(label="状态", interactive=False)
                            
                            with gr.Column(scale=2):
                                gr.Markdown("### 表元数据")
                                
                                table_business_name = gr.Textbox(
                                    label="业务名称",
                                    placeholder="例如：用户信息表",
                                    lines=1
                                )
                                
                                table_description = gr.Textbox(
                                    label="表描述",
                                    placeholder="例如：存储系统用户的基本信息",
                                    lines=2
                                )
                                
                                table_business_meaning = gr.Textbox(
                                    label="业务含义",
                                    placeholder="例如：记录注册用户的详细资料，包括个人信息和账户状态",
                                    lines=3
                                )
                                
                                table_category = gr.Textbox(
                                    label="业务分类",
                                    placeholder="例如：用户管理、基础数据",
                                    lines=1
                                )
                                
                                save_table_btn = gr.Button("保存表信息", variant="primary")
                    
                    # 字段信息管理
                    with gr.TabItem("🏷️ 字段信息管理"):
                        with gr.Row():
                            with gr.Column(scale=1):
                                gr.Markdown("### 表选择与操作")
                                
                                column_table_dropdown = gr.Dropdown(
                                    label="选择表",
                                    choices=app.get_table_list(),
                                    interactive=True,
                                    allow_custom_value=False
                                )
                                
                                with gr.Row():
                                    load_columns_btn = gr.Button("📋 加载字段", variant="primary", size="sm")
                                    refresh_examples_btn = gr.Button("🔄 刷新示例", variant="secondary", size="sm")
                                
                                column_status = gr.Textbox(label="操作状态", interactive=False, lines=3)
                                
                                gr.Markdown("### 💡 使用说明")
                                gr.Markdown("""
                                **操作步骤：**
                                1. 选择要管理的表
                                2. 点击"📋 加载字段"获取字段列表和数据库备注
                                3. 点击"🔄 刷新示例"自动获取真实数据示例
                                4. 直接在表格中编辑字段元数据信息
                                5. 修改后自动保存到本地缓存和数据库
                                
                                **字段说明：**
                                - **字段名**：数据库字段名（只读）
                                - **数据类型**：字段数据类型（只读）
                                - **业务名称**：字段的中文业务名称
                                - **字段描述**：会同步更新到数据库字段备注
                                - **业务含义**：字段在业务场景中的具体含义
                                - **数据示例**：自动从数据库获取的真实数据样例
                                
                                **重要提示：**
                                - 字段描述会同时更新数据库的COMMENT信息
                                - 所有元数据会用于AI生成SQL时的参考
                                - 建议填写准确、详细的业务信息以提高查询效果
                                """)
                            
                            with gr.Column(scale=3):
                                gr.Markdown("### 📊 字段元数据管理")
                                gr.Markdown("*在下方表格中直接编辑字段信息，修改后会自动保存到系统中*")
                                
                                columns_dataframe = gr.Dataframe(
                                    headers=["字段名", "数据类型", "业务名称", "字段描述", "业务含义", "数据示例"],
                                    datatype=["str", "str", "str", "str", "str", "str"],
                                    interactive=True,
                                    wrap=True,
                                    label="字段信息表格"
                                )
                    
                    # 数据导入导出
                    with gr.TabItem("📤 数据管理"):
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("### 📤 导出元数据")
                                export_btn = gr.Button("导出元数据", variant="primary")
                                export_status = gr.Textbox(label="导出状态", interactive=False)
                                export_data = gr.Textbox(
                                    label="导出数据",
                                    lines=10,
                                    interactive=False,
                                    placeholder="导出的JSON数据将显示在这里"
                                )
                            
                            with gr.Column():
                                gr.Markdown("### 📥 导入元数据")
                                import_data = gr.Textbox(
                                    label="导入数据",
                                    lines=10,
                                    placeholder="请粘贴要导入的JSON数据"
                                )
                                import_btn = gr.Button("导入元数据", variant="primary")
                                import_status = gr.Textbox(label="导入状态", interactive=False)
        
        # 事件绑定
        
        # 对话功能 - 支持流式输出
        msg_input.submit(
            app.chat_query,
            inputs=[msg_input, chatbot, auto_viz, enable_analysis, analysis_level],
            outputs=[chatbot, msg_input, chart_display]
        )
        
        send_btn.click(
            app.chat_query,
            inputs=[msg_input, chatbot, auto_viz, enable_analysis, analysis_level],
            outputs=[chatbot, msg_input, chart_display]
        )
        
        # 清空对话
        clear_btn.click(
            lambda: ([], None),
            outputs=[chatbot, chart_display]
        )
        
        # 反馈功能
        def handle_feedback(description):
            result = app.add_positive_feedback(description)
            return result, gr.update(visible=True), ""  # 清空描述框
        
        like_btn.click(
            fn=handle_feedback,
            inputs=[feedback_description],
            outputs=[feedback_result, feedback_result, feedback_description]
        )
        
        # 示例按钮
        def handle_example(example_text):
            # 直接调用chat_query生成器，取最后一个结果
            for result in app.chat_query(example_text, [], True, True, "standard"):
                final_result = result
            return final_result
        
        for i, btn in enumerate(example_btns):
            btn.click(
                lambda x=examples[i]: handle_example(x),
                outputs=[chatbot, msg_input, chart_display]
            )
        
        # 系统管理功能
        test_conn_btn.click(
            fn=app.test_connection,
            outputs=[conn_status, conn_info]
        )
        
        refresh_schema_btn.click(
            fn=app.refresh_schema,
            outputs=[conn_status, conn_info]
        )
        
        get_schema_btn.click(
            fn=app.get_schema_info,
            outputs=[schema_status, schema_display]
        )
        
        # 知识库功能
        refresh_stats_btn.click(
            fn=app.get_knowledge_stats,
            outputs=[knowledge_stats]
        )
        
        # 知识库导入导出功能
        export_kb_btn.click(
            fn=app.export_knowledge_base,
            outputs=[export_kb_status, export_kb_data]
        )
        
        import_kb_btn.click(
            fn=app.import_knowledge_base,
            inputs=[import_kb_data],
            outputs=[import_kb_status]
        ).then(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        ).then(
            fn=lambda: "",
            outputs=[import_kb_data]
        )
        
        # 知识库表格管理功能
        refresh_table_btn.click(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        )
        
        # 表格行选择事件
        def on_table_select(evt: gr.SelectData):
            if evt.index is not None and evt.index[0] is not None:
                # 获取选中行的数据
                df = app.get_knowledge_table()
                if not df.empty and evt.index[0] < len(df):
                    row = df.iloc[evt.index[0]]
                    return (
                        row['ID'],
                        row['问题'],
                        row['SQL查询'],
                        row['描述'],
                        row['标签'],
                        f"✅ 已选择条目: {row['ID']}"
                    )
            return "", "", "", "", "", "❌ 请选择有效的表格行"
        
        knowledge_table.select(
            fn=on_table_select,
            outputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags, edit_result]
        )
        
        # 更新条目
        update_btn.click(
            fn=app.update_knowledge_item,
            inputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags],
            outputs=[edit_result]
        ).then(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        )
        
        # 删除条目
        delete_btn.click(
            fn=app.delete_knowledge_item,
            inputs=[selected_id],
            outputs=[edit_result]
        ).then(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        ).then(
            fn=lambda: ("", "", "", "", ""),
            outputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags]
        )
        
        # 添加新条目
        add_btn.click(
            fn=app.add_knowledge_item,
            inputs=[new_question, new_sql, new_description, new_tags],
            outputs=[add_result]
        ).then(
            fn=lambda: ("", "", "", ""),
            outputs=[new_question, new_sql, new_description, new_tags]
        )
        
        # 快速添加按钮 - 清空编辑表单
        add_new_btn.click(
            fn=lambda: ("", "", "", "", ""),
            outputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags]
        )
        
        # 表信息维护功能事件绑定
        
        # 表信息管理
        load_table_btn.click(
            fn=app.get_table_metadata_info,
            inputs=[table_dropdown],
            outputs=[table_business_name, table_description, table_business_meaning, table_category, table_status]
        )
        
        save_table_btn.click(
            fn=app.update_table_metadata_info,
            inputs=[table_dropdown, table_business_name, table_description, table_business_meaning, table_category],
            outputs=[table_status]
        )
        
        # 字段信息管理 - 表格模式
        load_columns_btn.click(
            fn=app.load_table_with_examples,
            inputs=[column_table_dropdown],
            outputs=[columns_dataframe, column_status]
        )
        
        refresh_examples_btn.click(
            fn=app.refresh_data_examples,
            inputs=[column_table_dropdown],
            outputs=[columns_dataframe, column_status]
        )
        
        # 当表格数据变化时自动保存
        columns_dataframe.change(
            fn=app.update_columns_from_dataframe,
            inputs=[column_table_dropdown, columns_dataframe],
            outputs=[column_status]
        )
        
        # 数据导入导出
        export_btn.click(
            fn=app.export_table_metadata,
            outputs=[export_status, export_data]
        )
        
        import_btn.click(
            fn=app.import_table_metadata,
            inputs=[import_data],
            outputs=[import_status]
        )
        
        # 启动时的欢迎信息和知识库统计
        def load_welcome():
            welcome_msg = """👋 您好！我是ChatBI智能助手。

🚀 **核心功能**：
- 🔍 **自然语言查询**: 用中文提问，自动生成SQL
- 📊 **智能可视化**: 自动选择最适合的图表类型
- 🧠 **AI数据分析**: 深度解读数据，提供业务洞察
- 🎯 **RAG智能学习**: 基于用户反馈持续改进

💡 **使用提示**：
- 可在右侧选项面板中调整可视化和分析设置
- 对满意的查询结果点赞，帮助AI学习改进
- 点击下方示例按钮快速开始

请输入您的问题开始智能对话！"""
            stats = app.get_knowledge_stats()
            return [["", welcome_msg]], None, stats
        
        interface.load(
            load_welcome,
            outputs=[chatbot, chart_display, knowledge_stats]
        ).then(
            fn=app.get_knowledge_table,
            outputs=[knowledge_table]
        )
    
    return interface

if __name__ == "__main__":
    # 使用带认证功能的应用
    interface = create_authenticated_chatbi_app()
    
    print("🚀 启动ChatBI带认证功能的对话式界面...")
    print(f"📊 数据库类型: {config.database.type}")
    print(f"🤖 AI模型: {config.llm.model_name}")
    print("🔐 认证功能: 已启用")
    print("📋 功能说明:")
    print("  - 用户认证和权限管理")
    print("  - 智能数据查询和分析")
    print("  - 自动可视化生成")
    print("  - 查询反馈和优化")
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=False,
        show_error=True
    )