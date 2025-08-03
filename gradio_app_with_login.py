#!/usr/bin/env python3
"""
ChatBI 带登录界面的对话式Gradio前端
用户必须先登录才能访问应用功能，只调整前端设计，不改变后端逻辑
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


class LoginFirstChatBIApp:
    """登录优先的ChatBI应用 - 用户必须先登录才能访问功能"""
    
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
        self.last_query_result = None
        
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
        """用户登录"""
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
                ip_address="127.0.0.1"
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
        """用户登出"""
        try:
            if self.current_session_token and self.session_manager:
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
        """用户注册"""
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
        """处理对话式查询 - 支持流式输出和用户权限检查"""
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


def create_login_first_app() -> gr.Blocks:
    """创建登录优先的ChatBI应用界面"""
    
    # 创建应用实例
    app = LoginFirstChatBIApp()
    
    # 自定义CSS样式
    custom_css = """
    .login-container {
        max-width: 500px;
        margin: 50px auto;
        padding: 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        color: white;
    }
    .login-title {
        text-align: center;
        font-size: 2.5em;
        margin-bottom: 10px;
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .login-subtitle {
        text-align: center;
        font-size: 1.2em;
        margin-bottom: 30px;
        color: rgba(255,255,255,0.9);
    }
    .user-info-header {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
    }
    .main-app-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
    }
    .chat-container {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .error-message {
        color: #d32f2f;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        background: rgba(211, 47, 47, 0.1);
        border-radius: 5px;
        margin: 10px 0;
    }
    .success-message {
        color: #388e3c;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        background: rgba(56, 142, 60, 0.1);
        border-radius: 5px;
        margin: 10px 0;
    }
    """
    
    with gr.Blocks(
        title="ChatBI 智能数据查询系统",
        theme=gr.themes.Soft(),
        css=custom_css
    ) as demo:
        
        # 应用状态
        is_logged_in = gr.State(False)
        user_info = gr.State({})
        
        # 登录界面
        with gr.Column(elem_classes=["login-container"], visible=True) as login_interface:
            gr.HTML("""
            <div class="login-title">🤖 ChatBI</div>
            <div class="login-subtitle">智能数据查询系统</div>
            """)
            
            with gr.Tabs():
                # 登录标签页
                with gr.Tab("🔐 用户登录"):
                    gr.Markdown("### 请登录以访问系统")
                    
                    login_employee_id = gr.Textbox(
                        label="工号",
                        placeholder="请输入您的工号",
                        container=True
                    )
                    login_password = gr.Textbox(
                        label="密码",
                        type="password",
                        placeholder="请输入密码",
                        container=True
                    )
                    
                    login_btn = gr.Button("登录", variant="primary", size="lg")
                    login_message = gr.HTML("")
                
                # 注册标签页
                with gr.Tab("📝 用户注册"):
                    gr.Markdown("### 新用户注册")
                    
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
                    
                    register_btn = gr.Button("注册", variant="secondary", size="lg")
                    register_message = gr.HTML("")
        
        # 主应用界面（登录后显示）
        with gr.Column(visible=False, elem_classes=["main-app-container"]) as main_interface:
            # 用户信息头部
            user_header = gr.HTML("", elem_classes=["user-info-header"])
            
            # 主要功能区域
            with gr.Row():
                with gr.Column(scale=3, elem_classes=["chat-container"]):
                    gr.Markdown("## 💬 智能数据查询")
                    
                    # 聊天界面
                    chatbot = gr.Chatbot(
                        label="ChatBI 对话",
                        height=500,
                        show_label=False,
                        container=True,
                        bubble_full_width=False
                    )
                    
                    # 输入区域
                    with gr.Row():
                        msg_input = gr.Textbox(
                            label="输入您的问题",
                            placeholder="例如：显示最近一周的销售数据",
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
                            value=True
                        )
                        analysis_level_dropdown = gr.Dropdown(
                            label="分析级别",
                            choices=["basic", "standard", "detailed"],
                            value="standard"
                        )
                    
                    # 用户操作区域
                    with gr.Row():
                        logout_btn = gr.Button("🚪 登出", variant="secondary")
                        clear_chat_btn = gr.Button("🗑️ 清空对话", variant="secondary")
                
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
                        placeholder="请描述您对查询结果的看法",
                        lines=2
                    )
                    
                    like_btn = gr.Button("👍 添加到知识库", variant="secondary")
                    feedback_output = gr.Textbox(
                        label="反馈状态",
                        interactive=False,
                        max_lines=3
                    )
        
        # 事件处理函数
        def handle_login(employee_id, password):
            """处理登录"""
            success, message, user_data = app.login_user(employee_id, password)
            
            if success:
                # 构建用户信息显示
                user_display = f"""
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>👤 {user_data['employee_id']}</strong> ({user_data['full_name']})
                        <br>📧 {user_data['email']} | 
                        {'👑 管理员' if user_data['is_admin'] else '👤 普通用户'}
                    </div>
                    <div style="text-align: right; font-size: 0.9em;">
                        🕒 登录时间: {user_data['login_time']}
                    </div>
                </div>
                """
                
                return (
                    True,  # is_logged_in
                    user_data,  # user_info
                    gr.update(visible=False),  # hide login_interface
                    gr.update(visible=True),   # show main_interface
                    user_display,  # user_header
                    f'<div class="success-message">✅ {message}</div>',  # login_message
                    "",  # clear employee_id
                    "",  # clear password
                    []   # clear chatbot
                )
            else:
                return (
                    False,  # is_logged_in
                    {},  # user_info
                    gr.update(visible=True),   # show login_interface
                    gr.update(visible=False),  # hide main_interface
                    "",  # user_header
                    f'<div class="error-message">❌ {message}</div>',  # login_message
                    employee_id,  # keep employee_id
                    "",  # clear password
                    []   # clear chatbot
                )
        
        def handle_logout():
            """处理登出"""
            success, message = app.logout_user()
            
            return (
                False,  # is_logged_in
                {},  # user_info
                gr.update(visible=True),   # show login_interface
                gr.update(visible=False),  # hide main_interface
                "",  # user_header
                f'<div class="success-message">✅ {message}</div>' if success else f'<div class="error-message">❌ {message}</div>',
                "",  # clear employee_id
                "",  # clear password
                []   # clear chatbot
            )
        
        def handle_register(employee_id, password, confirm_password, email, full_name):
            """处理注册"""
            success, message = app.register_user(
                employee_id, password, confirm_password, email, full_name
            )
            
            if success:
                return (
                    f'<div class="success-message">✅ {message}</div>',
                    "", "", "", "", ""  # clear all fields
                )
            else:
                return (
                    f'<div class="error-message">❌ {message}</div>',
                    employee_id, "", "", email, full_name  # keep non-password fields
                )
        
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
        
        def clear_chat():
            """清空对话"""
            return []
        
        # 绑定事件
        login_btn.click(
            handle_login,
            inputs=[login_employee_id, login_password],
            outputs=[
                is_logged_in, user_info, login_interface, main_interface,
                user_header, login_message, login_employee_id, login_password, chatbot
            ]
        )
        
        logout_btn.click(
            handle_logout,
            outputs=[
                is_logged_in, user_info, login_interface, main_interface,
                user_header, login_message, login_employee_id, login_password, chatbot
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
        
        # 清空对话事件
        clear_chat_btn.click(
            clear_chat,
            outputs=[chatbot]
        )
        
        # 回车键登录
        login_password.submit(
            handle_login,
            inputs=[login_employee_id, login_password],
            outputs=[
                is_logged_in, user_info, login_interface, main_interface,
                user_header, login_message, login_employee_id, login_password, chatbot
            ]
        )
    
    return demo


def launch_login_first_app(server_name: str = "127.0.0.1", server_port: int = 7860,
                          share: bool = False, debug: bool = False):
    """
    启动登录优先的ChatBI应用
    
    Args:
        server_name: 服务器地址
        server_port: 服务器端口
        share: 是否创建公共链接
        debug: 是否启用调试模式
    """
    try:
        app = create_login_first_app()
        
        print(f"🚀 启动ChatBI登录优先应用: http://{server_name}:{server_port}")
        print("📋 功能说明:")
        print("  - 🔐 用户必须先登录才能访问系统")
        print("  - 💬 智能数据查询和分析")
        print("  - 📊 自动可视化生成")
        print("  - 👍 查询反馈和知识库")
        print("  - 🔒 基于用户权限的数据访问控制")
        
        app.launch(
            server_name=server_name,
            server_port=server_port,
            share=share,
            debug=debug,
            show_error=True,
            quiet=False
        )
        
    except Exception as e:
        print(f"❌ 启动应用失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 设置日志
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动应用
    launch_login_first_app(debug=True)