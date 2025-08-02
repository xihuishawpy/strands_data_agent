#!/usr/bin/env python3
"""
ChatBI 带认证功能的对话式Gradio前端界面
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
    from chatbi.auth import (
        UserManager, SessionManager, AuthDatabase, 
        get_integration_adapter, require_authentication
    )
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install gradio openai")
    sys.exit(1)


class AuthenticatedChatBIApp:
    """带认证功能的ChatBI对话式应用"""
    
    def __init__(self):
        """初始化应用"""
        # 认证相关组件
        self.user_manager = UserManager()
        self.session_manager = SessionManager()
        self.auth_database = AuthDatabase()
        self.integration_adapter = get_integration_adapter()
        
        # ChatBI组件
        self.base_orchestrator = None
        self.connector = None
        self.schema_manager = None
        self.metadata_manager = None
        
        # 应用状态
        self.current_user = None
        self.current_session_token = None
        self.authenticated_orchestrator = None
        self.chat_history = []
        self.last_query_result = None
        
        # 尝试初始化基础组件
        self._initialize_base_components()
    
    def _initialize_base_components(self):
        """初始化基础ChatBI组件"""
        try:
            self.base_orchestrator = get_orchestrator()
            self.connector = get_database_connector()
            self.schema_manager = get_schema_manager()
            self.metadata_manager = get_table_metadata_manager()
            return True, "✅ ChatBI基础系统初始化成功"
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
            self.current_session_token = session_result.token
            
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
            if self.current_session_token:
                # 销毁会话
                self.session_manager.invalidate_session(self.current_session_token)
            
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
                self.authenticated_orchestrator is not None)
    
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
    
    def chat_query(self, message: str, history: List, auto_viz: bool = True, 
                  enable_analysis: bool = True, analysis_level: str = "standard"):
        """处理对话式查询 - 带权限检查"""
        if not self.is_authenticated():
            history.append([message, "❌ 请先登录后再进行查询"])
            yield history, "", None
            return
        
        if not message.strip():
            history.append([message, "❌ 请输入有效的查询问题"])
            yield history, "", None
            return
        
        try:
            # 初始化流式响应
            current_response = f"🤖 **正在为用户 {self.current_user.employee_id} 处理查询...**\n\n"
            history.append([message, current_response])
            yield history, "", None
            
            # 使用认证包装器执行查询
            for result in self.authenticated_orchestrator.query_stream(
                question=message,
                auto_visualize=auto_viz,
                analysis_level=analysis_level if enable_analysis else "none"
            ):
                if "step_info" in result:
                    current_response += result["step_info"] + "\n"
                    history[-1][1] = current_response
                    yield history, "", None
                
                elif "final_result" in result:
                    final_result = result["final_result"]
                    self.last_query_result = final_result
                    
                    if final_result.success:
                        # 构建成功响应
                        response_parts = [current_response]
                        
                        # SQL查询
                        if final_result.sql_query:
                            response_parts.append(f"\n📝 **生成的SQL查询:**\n```sql\n{final_result.sql_query}\n```")
                        
                        # 数据结果
                        if final_result.data:
                            response_parts.append(f"\n📊 **查询结果:** 共 {len(final_result.data)} 行数据")
                            
                            # 显示前几行数据
                            if len(final_result.data) > 0:
                                df = pd.DataFrame(final_result.data)
                                preview_rows = min(5, len(df))
                                response_parts.append(f"\n**数据预览 (前{preview_rows}行):**")
                                response_parts.append(df.head(preview_rows).to_markdown(index=False))
                        
                        # 数据分析
                        if final_result.analysis:
                            response_parts.append(f"\n🔍 **数据分析:**\n{final_result.analysis}")
                        
                        # 权限信息
                        if hasattr(final_result, 'accessible_schemas') and final_result.accessible_schemas:
                            response_parts.append(f"\n🔐 **可访问的Schema:** {', '.join(final_result.accessible_schemas)}")
                        
                        # 执行时间
                        if final_result.execution_time:
                            response_parts.append(f"\n⏱️ **执行时间:** {final_result.execution_time:.2f}秒")
                        
                        final_response = "\n".join(response_parts)
                        history[-1][1] = final_response
                        
                        # 返回图表信息
                        chart_data = None
                        if final_result.chart_info and final_result.chart_info.get("success"):
                            chart_data = final_result.chart_info
                        
                        yield history, "", chart_data
                    else:
                        # 错误响应
                        error_response = current_response + f"\n❌ **查询失败:** {final_result.error}"
                        if hasattr(final_result, 'permission_filtered') and final_result.permission_filtered:
                            error_response += "\n\n💡 **提示:** 这可能是权限问题，请联系管理员检查您的数据库访问权限。"
                        
                        history[-1][1] = error_response
                        yield history, "", None
                    
                    break
                    
        except Exception as e:
            error_msg = f"❌ 查询处理异常: {str(e)}"
            history[-1][1] = current_response + f"\n{error_msg}"
            yield history, "", None
    
    def get_user_schema_info(self) -> str:
        """获取用户可访问的Schema信息"""
        if not self.is_authenticated():
            return "请先登录后查看Schema信息"
        
        try:
            schema_info = self.authenticated_orchestrator.get_schema_info()
            if "error" in schema_info:
                return f"获取Schema信息失败: {schema_info['error']}"
            
            return "Schema信息获取成功，可在查询中使用"
            
        except Exception as e:
            return f"获取Schema信息异常: {str(e)}"
    
    def add_query_feedback(self, feedback_type: str = "positive", description: str = "") -> str:
        """添加查询反馈"""
        if not self.is_authenticated() or not self.last_query_result:
            return "无法添加反馈：请先登录并执行查询"
        
        try:
            if feedback_type == "positive":
                success = self.authenticated_orchestrator.add_positive_feedback(
                    question=self.last_query_result.question,
                    sql=self.last_query_result.sql_query or "",
                    description=description or "用户点赞"
                )
                
                if success:
                    return "✅ 感谢您的反馈！这将帮助改进系统"
                else:
                    return "❌ 反馈提交失败"
            else:
                return "暂时只支持正面反馈"
                
        except Exception as e:
            return f"提交反馈异常: {str(e)}"
def create_authenticated_app() -> gr.Blocks:
    """创建带认证功能的ChatBI应用"""
    
    # 创建应用实例
    app = AuthenticatedChatBIApp()
    
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
        
        # 系统信息标签页
        with gr.Tab("ℹ️ 系统信息") as info_tab:
            gr.Markdown("### 系统状态")
            system_status = gr.Textbox(
                label="系统状态",
                value="系统正常运行",
                interactive=False
            )
            
            gr.Markdown("### Schema信息")
            schema_info_btn = gr.Button("获取Schema信息")
            schema_info_output = gr.Textbox(
                label="Schema信息",
                interactive=False,
                max_lines=10
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
                    True,  # user_info_display visible
                    message,  # login_message
                    "",  # clear employee_id
                    "",  # clear password
                    gr.update(visible=False),  # login_btn
                    gr.update(visible=True),   # logout_btn
                    gr.update(interactive=False)  # disable auth inputs
                )
            else:
                return (
                    False,  # login_state
                    {},  # user_state
                    "",  # user_info_display
                    False,  # user_info_display visible
                    message,  # login_message
                    employee_id,  # keep employee_id
                    "",  # clear password
                    gr.update(visible=True),   # login_btn
                    gr.update(visible=False),  # logout_btn
                    gr.update(interactive=True)  # enable auth inputs
                )
        
        def handle_logout():
            """处理登出"""
            success, message = app.logout_user()
            
            return (
                False,  # login_state
                {},  # user_state
                "",  # user_info_display
                False,  # user_info_display visible
                message,  # login_message
                "",  # clear employee_id
                "",  # clear password
                gr.update(visible=True),   # login_btn
                gr.update(visible=False),  # logout_btn
                gr.update(interactive=True),  # enable auth inputs
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
            result = app.add_query_feedback("positive", description)
            return result, ""  # clear description
        
        def handle_schema_info():
            """处理Schema信息获取"""
            return app.get_user_schema_info()
        
        # 绑定事件
        login_btn.click(
            handle_login,
            inputs=[login_employee_id, login_password],
            outputs=[
                login_state, user_state, user_info_display, user_info_display,
                login_message, login_employee_id, login_password,
                login_btn, logout_btn, login_employee_id
            ]
        )
        
        logout_btn.click(
            handle_logout,
            outputs=[
                login_state, user_state, user_info_display, user_info_display,
                login_message, login_employee_id, login_password,
                login_btn, logout_btn, login_employee_id, chatbot
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
        
        # Schema信息事件
        schema_info_btn.click(
            handle_schema_info,
            outputs=[schema_info_output]
        )
    
    return demo


def launch_authenticated_app(server_name: str = "127.0.0.1", server_port: int = 7860,
                           share: bool = False, debug: bool = False):
    """
    启动带认证功能的ChatBI应用
    
    Args:
        server_name: 服务器地址
        server_port: 服务器端口
        share: 是否创建公共链接
        debug: 是否启用调试模式
    """
    try:
        app = create_authenticated_app()
        
        print(f"🚀 启动ChatBI认证应用: http://{server_name}:{server_port}")
        print("📋 功能说明:")
        print("  - 用户认证和权限管理")
        print("  - 智能数据查询和分析")
        print("  - 自动可视化生成")
        print("  - 查询反馈和优化")
        
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
    launch_authenticated_app(debug=True)