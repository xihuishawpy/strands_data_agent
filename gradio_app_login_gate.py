#!/usr/bin/env python3
"""
ChatBI 登录门禁版本
用户必须通过登录门禁才能访问应用，只调整前端设计，不改变后端逻辑
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
    from gradio_app_chat import ChatBIApp  # 直接使用现有的ChatBIApp类
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install gradio openai")
    sys.exit(1)


def create_login_gate_app() -> gr.Blocks:
    """创建带登录门禁的ChatBI应用界面"""
    
    # 创建应用实例（使用现有的ChatBIApp）
    chatbi_app = ChatBIApp()
    
    # 自定义CSS样式
    custom_css = """
    .login-gate {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .login-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        max-width: 450px;
        width: 90%;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    .login-title {
        font-size: 2.5em;
        margin-bottom: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    .login-subtitle {
        color: #666;
        margin-bottom: 30px;
        font-size: 1.1em;
    }
    .user-header {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
    }
    .main-content {
        background: #f8f9fa;
        min-height: calc(100vh - 100px);
        padding: 20px;
        border-radius: 15px;
        margin-top: 10px;
    }
    .chat-panel {
        background: white;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .viz-panel {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    .error-msg {
        color: #d32f2f;
        background: rgba(211, 47, 47, 0.1);
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #d32f2f;
        margin: 10px 0;
    }
    .success-msg {
        color: #388e3c;
        background: rgba(56, 142, 60, 0.1);
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #388e3c;
        margin: 10px 0;
    }
    """
    
    with gr.Blocks(
        title="ChatBI 智能数据查询系统",
        theme=gr.themes.Soft(),
        css=custom_css
    ) as demo:
        
        # 应用状态
        is_authenticated = gr.State(False)
        current_user_info = gr.State({})
        
        # 登录门禁界面
        with gr.Column(elem_classes=["login-gate"], visible=True) as login_gate:
            with gr.Column(elem_classes=["login-card"]):
                gr.HTML("""
                <div class="login-title">🤖 ChatBI</div>
                <div class="login-subtitle">智能数据查询系统 - 请先登录</div>
                """)
                
                with gr.Tabs():
                    # 登录标签页
                    with gr.Tab("🔐 登录"):
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
                        login_status = gr.HTML("")
                    
                    # 注册标签页
                    with gr.Tab("📝 注册"):
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
                        register_status = gr.HTML("")
        
        # 主应用界面（登录后显示）
        with gr.Column(visible=False, elem_classes=["main-content"]) as main_app:
            # 用户信息头部
            with gr.Row(elem_classes=["user-header"]) as user_header:
                user_info_display = gr.HTML("")
                logout_btn = gr.Button("🚪 登出", variant="secondary", size="sm")
            
            # 主要功能标签页
            with gr.Tabs():
                # 智能查询标签页
                with gr.Tab("💬 智能查询") as chat_tab:
                    with gr.Row():
                        # 聊天面板
                        with gr.Column(scale=3, elem_classes=["chat-panel"]):
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
                                    placeholder="例如：显示不同物料的预算金额",
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
                            
                            # 操作按钮
                            with gr.Row():
                                clear_chat_btn = gr.Button("🗑️ 清空对话", variant="secondary")
                        
                        # 可视化和反馈面板
                        with gr.Column(scale=1, elem_classes=["viz-panel"]):
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
                                        choices=[],  # 初始为空，登录后动态加载
                                        interactive=True,
                                        allow_custom_value=False
                                    )
                                    
                                    with gr.Row():
                                        load_table_btn = gr.Button("加载表信息", variant="primary", size="sm")
                                        refresh_table_list_btn = gr.Button("🔄 刷新表列表", variant="secondary", size="sm")
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
                                        choices=[],  # 初始为空，登录后动态加载
                                        interactive=True,
                                        allow_custom_value=False
                                    )
                                    
                                    with gr.Row():
                                        load_columns_btn = gr.Button("📋 加载字段", variant="primary", size="sm")
                                        refresh_examples_btn = gr.Button("🔄 刷新示例", variant="secondary", size="sm")
                                    with gr.Row():
                                        refresh_column_table_list_btn = gr.Button("🔄 刷新表列表", variant="secondary", size="sm")
                                    
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
                                    export_metadata_btn = gr.Button("导出元数据", variant="primary")
                                    export_metadata_status = gr.Textbox(label="导出状态", interactive=False)
                                    export_metadata_data = gr.Textbox(
                                        label="导出数据",
                                        lines=10,
                                        interactive=False,
                                        placeholder="导出的JSON数据将显示在这里"
                                    )
                                
                                with gr.Column():
                                    gr.Markdown("### 📥 导入元数据")
                                    import_metadata_data = gr.Textbox(
                                        label="导入数据",
                                        lines=10,
                                        placeholder="请粘贴要导入的JSON数据"
                                    )
                                    import_metadata_btn = gr.Button("导入元数据", variant="primary")
                                    import_metadata_status = gr.Textbox(label="导入状态", interactive=False)

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
                    1. 登录成功后，在"智能查询"标签页中输入自然语言问题
                    2. 系统会根据您的权限自动过滤可访问的数据
                    3. 查看查询结果和可视化图表
                    4. 可以对查询结果进行反馈
                    
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
        def update_table_choices():
            """更新表选择下拉框的选项"""
            try:
                if chatbi_app.is_authenticated():
                    tables = chatbi_app.get_table_list()
                    return gr.update(choices=tables), gr.update(choices=tables)
                else:
                    return gr.update(choices=[]), gr.update(choices=[])
            except Exception as e:
                print(f"更新表列表失败: {e}")
                return gr.update(choices=[]), gr.update(choices=[])
        
        def handle_login(employee_id, password):
            """处理登录"""
            success, message, user_data = chatbi_app.login_user(employee_id, password)
            
            if success:
                # 构建用户信息显示
                user_display = f"""
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <div>
                        <strong>👤 {user_data['employee_id']}</strong> ({user_data['full_name']})
                        <br><small>📧 {user_data['email']} | 
                        {'👑 管理员' if user_data['is_admin'] else '👤 普通用户'}</small>
                    </div>
                    <div style="text-align: right; font-size: 0.9em;">
                        🕒 {user_data['login_time']}
                    </div>
                </div>
                """
                
                # 获取更新后的表列表
                table_choices_update1, table_choices_update2 = update_table_choices()
                
                return (
                    True,  # is_authenticated
                    user_data,  # current_user_info
                    gr.update(visible=False),  # hide login_gate
                    gr.update(visible=True),   # show main_app
                    user_display,  # user_info_display
                    f'<div class="success-msg">✅ {message}</div>',  # login_status
                    "",  # clear employee_id
                    "",  # clear password
                    [],  # clear chatbot
                    table_choices_update1,  # update table_dropdown
                    table_choices_update2   # update column_table_dropdown
                )
            else:
                return (
                    False,  # is_authenticated
                    {},  # current_user_info
                    gr.update(visible=True),   # show login_gate
                    gr.update(visible=False),  # hide main_app
                    "",  # user_info_display
                    f'<div class="error-msg">❌ {message}</div>',  # login_status
                    employee_id,  # keep employee_id
                    "",  # clear password
                    [],  # clear chatbot
                    gr.update(choices=[]),  # clear table_dropdown
                    gr.update(choices=[])   # clear column_table_dropdown
                )
        
        def handle_logout():
            """处理登出"""
            success, message = chatbi_app.logout_user()
            
            return (
                False,  # is_authenticated
                {},  # current_user_info
                gr.update(visible=True),   # show login_gate
                gr.update(visible=False),  # hide main_app
                "",  # user_info_display
                f'<div class="success-msg">✅ {message}</div>' if success else f'<div class="error-msg">❌ {message}</div>',
                "",  # clear employee_id
                "",  # clear password
                [],  # clear chatbot
                gr.update(choices=[]),  # clear table_dropdown
                gr.update(choices=[])   # clear column_table_dropdown
            )
        
        def handle_register(employee_id, password, confirm_password, email, full_name):
            """处理注册"""
            success, message = chatbi_app.register_user(
                employee_id, password, confirm_password, email, full_name
            )
            
            if success:
                return (
                    f'<div class="success-msg">✅ {message}</div>',
                    "", "", "", "", ""  # clear all fields
                )
            else:
                return (
                    f'<div class="error-msg">❌ {message}</div>',
                    employee_id, "", "", email, full_name  # keep non-password fields
                )
        
        def handle_chat(message, history, auto_viz, enable_analysis, analysis_level):
            """处理聊天查询"""
            if not chatbi_app.is_authenticated():
                history.append([message, "❌ 请先登录后再进行查询"])
                return history, "", None
            
            # 使用生成器处理流式响应
            for result in chatbi_app.chat_query(message, history, auto_viz, enable_analysis, analysis_level):
                yield result
        
        def handle_feedback(description):
            """处理反馈"""
            result = chatbi_app.add_positive_feedback(description)
            return result, ""  # clear description
        
        def clear_chat():
            """清空对话"""
            return []
        
        # 事件处理函数 - 系统管理功能
        def handle_test_connection():
            """处理数据库连接测试"""
            status, info = chatbi_app.test_connection()
            return f"{status}\n\n{info}"
        
        def handle_refresh_schema():
            """处理Schema刷新"""
            try:
                if not chatbi_app.is_authenticated():
                    return "⚠️ 请先登录后再刷新Schema"
                
                # 刷新Schema缓存
                status, info = chatbi_app.refresh_schema()
                
                # 如果刷新成功，获取最新的详细信息
                if "成功" in status:
                    detailed_info = get_detailed_schema_info(chatbi_app)
                    return f"{status}\n\n{detailed_info}"
                else:
                    return f"{status}\n\n{info}"
                    
            except Exception as e:
                return f"❌ Schema刷新失败: {str(e)}"
        
        def handle_get_schema():
            """处理获取Schema信息"""
            try:
                if not chatbi_app.is_authenticated():
                    return "⚠️ 请先登录以查看Schema信息"
                
                # 获取详细的Schema信息
                schema_info = get_detailed_schema_info(chatbi_app)
                return schema_info
            except Exception as e:
                return f"❌ 获取Schema信息失败: {str(e)}"
        
        def handle_knowledge_stats():
            """处理获取知识库统计"""
            return chatbi_app.get_knowledge_stats()
        
        def get_detailed_schema_info(app):
            """获取详细的Schema信息"""
            try:
                info_parts = []
                
                # 用户信息
                if app.current_user:
                    info_parts.append(f"### 📊 数据库Schema信息")
                    info_parts.append(f"**当前用户**: {app.current_user.employee_id}")
                    info_parts.append(f"**权限级别**: {'管理员' if app.current_user.is_admin else '普通用户'}")
                    info_parts.append("")
                
                # 数据库连接信息
                if app.connector:
                    try:
                        from chatbi.config import config
                        info_parts.append("### 🔗 数据库连接信息")
                        info_parts.append(f"**数据库类型**: {config.database.type}")
                        info_parts.append(f"**主机地址**: {config.database.host}:{config.database.port}")
                        info_parts.append(f"**数据库名**: {config.database.database}")
                        info_parts.append(f"**连接状态**: {'✅ 已连接' if app.connector.is_connected else '❌ 未连接'}")
                        info_parts.append("")
                    except Exception as e:
                        info_parts.append(f"**连接信息获取失败**: {str(e)}")
                        info_parts.append("")
                
                # 获取表列表
                if app.schema_manager:
                    try:
                        tables = app.get_table_list()
                        info_parts.append("### 📋 数据库表信息")
                        info_parts.append(f"**表总数**: {len(tables)}")
                        
                        if tables:
                            info_parts.append("")
                            info_parts.append("**表列表**:")
                            
                            # 按字母顺序排序表名
                            sorted_tables = sorted(tables)
                            
                            # 分组显示表名（每行5个）
                            for i in range(0, len(sorted_tables), 5):
                                table_group = sorted_tables[i:i+5]
                                info_parts.append("  " + " | ".join(f"`{table}`" for table in table_group))
                            
                            info_parts.append("")
                            
                            # 显示前几个表的详细信息
                            info_parts.append("**表结构示例** (前3个表):")
                            for table_name in sorted_tables[:3]:
                                try:
                                    table_schema = app.schema_manager.get_table_schema(table_name)
                                    columns = table_schema.get("columns", [])
                                    
                                    info_parts.append(f"\n📊 **{table_name}** ({len(columns)} 个字段)")
                                    
                                    # 显示前5个字段
                                    for col in columns[:5]:
                                        col_name = col.get("name", "")
                                        col_type = col.get("type", "")
                                        col_comment = col.get("comment", "")
                                        
                                        col_info = f"  - `{col_name}` ({col_type})"
                                        if col_comment:
                                            col_info += f" - {col_comment}"
                                        info_parts.append(col_info)
                                    
                                    if len(columns) > 5:
                                        info_parts.append(f"  - ... 还有 {len(columns) - 5} 个字段")
                                
                                except Exception as e:
                                    info_parts.append(f"  获取表 {table_name} 结构失败: {str(e)}")
                        else:
                            info_parts.append("⚠️ 未找到任何表")
                        
                        info_parts.append("")
                    except Exception as e:
                        info_parts.append(f"**表信息获取失败**: {str(e)}")
                        info_parts.append("")
                
                # 元数据统计
                if app.metadata_manager:
                    try:
                        # 获取有元数据的表数量
                        tables_with_metadata = 0
                        total_columns_with_metadata = 0
                        
                        for table_name in app.get_table_list():
                            metadata = app.metadata_manager.get_table_metadata(table_name)
                            if metadata:
                                tables_with_metadata += 1
                                total_columns_with_metadata += len(metadata.columns)
                        
                        info_parts.append("### 📝 元数据统计")
                        info_parts.append(f"**有元数据的表**: {tables_with_metadata}")
                        info_parts.append(f"**有元数据的字段**: {total_columns_with_metadata}")
                        info_parts.append("")
                    except Exception as e:
                        info_parts.append(f"**元数据统计失败**: {str(e)}")
                        info_parts.append("")
                
                # 权限信息
                if app.is_authenticated() and hasattr(app, 'last_query_result') and app.last_query_result:
                    accessible_schemas = getattr(app.last_query_result, 'accessible_schemas', [])
                    if accessible_schemas:
                        info_parts.append("### 🔐 用户权限信息")
                        info_parts.append(f"**可访问的Schema**: {', '.join(accessible_schemas)}")
                        info_parts.append("")
                
                # 系统状态
                info_parts.append("### ⚙️ 系统状态")
                info_parts.append(f"**认证状态**: {'✅ 已认证' if app.is_authenticated() else '❌ 未认证'}")
                info_parts.append(f"**基础编排器**: {'✅ 已初始化' if app.base_orchestrator else '❌ 未初始化'}")
                info_parts.append(f"**认证编排器**: {'✅ 已初始化' if app.authenticated_orchestrator else '❌ 未初始化'}")
                info_parts.append(f"**Schema管理器**: {'✅ 已初始化' if app.schema_manager else '❌ 未初始化'}")
                info_parts.append(f"**元数据管理器**: {'✅ 已初始化' if app.metadata_manager else '❌ 未初始化'}")
                
                # 操作建议
                info_parts.append("")
                info_parts.append("### 💡 操作建议")
                info_parts.append("- 如需刷新Schema信息，请点击'刷新Schema缓存'按钮")
                info_parts.append("- 可在'表信息维护'标签页中管理表和字段的业务信息")
                info_parts.append("- 建议定期维护表和字段的元数据以提高查询准确性")
                
                return "\n".join(info_parts)
                
            except Exception as e:
                return f"❌ 获取详细Schema信息失败: {str(e)}\n\n详细错误:\n```\n{traceback.format_exc()}\n```"
        
        # 绑定事件
        login_btn.click(
            handle_login,
            inputs=[login_employee_id, login_password],
            outputs=[
                is_authenticated, current_user_info, login_gate, main_app,
                user_info_display, login_status, login_employee_id, login_password, chatbot,
                table_dropdown, column_table_dropdown
            ]
        )
        
        logout_btn.click(
            handle_logout,
            outputs=[
                is_authenticated, current_user_info, login_gate, main_app,
                user_info_display, login_status, login_employee_id, login_password, chatbot,
                table_dropdown, column_table_dropdown
            ]
        )
        
        register_btn.click(
            handle_register,
            inputs=[reg_employee_id, reg_password, reg_confirm_password, reg_email, reg_full_name],
            outputs=[register_status, reg_employee_id, reg_password, reg_confirm_password, reg_email, reg_full_name]
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
            fn=chatbi_app.get_knowledge_stats,
            outputs=[knowledge_stats]
        )
        
        # 知识库导入导出功能
        export_kb_btn.click(
            fn=chatbi_app.export_knowledge_base,
            outputs=[export_kb_status, export_kb_data]
        )
        
        import_kb_btn.click(
            fn=chatbi_app.import_knowledge_base,
            inputs=[import_kb_data],
            outputs=[import_kb_status]
        ).then(
            fn=chatbi_app.get_knowledge_table,
            outputs=[knowledge_table]
        ).then(
            fn=lambda: "",
            outputs=[import_kb_data]
        )
        
        # 知识库表格管理功能
        refresh_table_btn.click(
            fn=chatbi_app.get_knowledge_table,
            outputs=[knowledge_table]
        )
        
        # 表格行选择事件
        def on_table_select(evt: gr.SelectData):
            if evt.index is not None and evt.index[0] is not None:
                # 获取选中行的数据
                df = chatbi_app.get_knowledge_table()
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
            fn=chatbi_app.update_knowledge_item,
            inputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags],
            outputs=[edit_result]
        ).then(
            fn=chatbi_app.get_knowledge_table,
            outputs=[knowledge_table]
        )
        
        # 删除条目
        delete_btn.click(
            fn=chatbi_app.delete_knowledge_item,
            inputs=[selected_id],
            outputs=[edit_result]
        ).then(
            fn=chatbi_app.get_knowledge_table,
            outputs=[knowledge_table]
        ).then(
            fn=lambda: ("", "", "", "", ""),
            outputs=[selected_id, edit_question, edit_sql, edit_description, edit_tags]
        )
        
        # 添加新条目
        add_btn.click(
            fn=chatbi_app.add_knowledge_item,
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
        
        # 刷新表列表功能
        def refresh_table_list():
            """刷新表列表"""
            try:
                if chatbi_app.is_authenticated():
                    # 强制刷新schema缓存
                    chatbi_app.refresh_schema()
                    # 获取最新的表列表
                    tables = chatbi_app.get_table_list()
                    return gr.update(choices=tables), "✅ 表列表已刷新"
                else:
                    return gr.update(choices=[]), "❌ 请先登录"
            except Exception as e:
                return gr.update(choices=[]), f"❌ 刷新失败: {str(e)}"
        
        def refresh_column_table_list():
            """刷新字段管理的表列表"""
            try:
                if chatbi_app.is_authenticated():
                    # 强制刷新schema缓存
                    chatbi_app.refresh_schema()
                    # 获取最新的表列表
                    tables = chatbi_app.get_table_list()
                    return gr.update(choices=tables), "✅ 表列表已刷新"
                else:
                    return gr.update(choices=[]), "❌ 请先登录"
            except Exception as e:
                return gr.update(choices=[]), f"❌ 刷新失败: {str(e)}"
        
        # 表信息管理
        load_table_btn.click(
            fn=chatbi_app.get_table_metadata_info,
            inputs=[table_dropdown],
            outputs=[table_business_name, table_description, table_business_meaning, table_category, table_status]
        )
        
        save_table_btn.click(
            fn=chatbi_app.update_table_metadata_info,
            inputs=[table_dropdown, table_business_name, table_description, table_business_meaning, table_category],
            outputs=[table_status]
        )
        
        # 刷新表列表事件
        refresh_table_list_btn.click(
            fn=refresh_table_list,
            outputs=[table_dropdown, table_status]
        )
        
        refresh_column_table_list_btn.click(
            fn=refresh_column_table_list,
            outputs=[column_table_dropdown, column_status]
        )
        
        # 字段信息管理 - 表格模式
        load_columns_btn.click(
            fn=chatbi_app.load_table_with_examples,
            inputs=[column_table_dropdown],
            outputs=[columns_dataframe, column_status]
        )
        
        refresh_examples_btn.click(
            fn=chatbi_app.refresh_data_examples,
            inputs=[column_table_dropdown],
            outputs=[columns_dataframe, column_status]
        )
        
        # 当表格数据变化时自动保存
        columns_dataframe.change(
            fn=chatbi_app.update_columns_from_dataframe,
            inputs=[column_table_dropdown, columns_dataframe],
            outputs=[column_status]
        )
        
        # 数据导入导出
        export_metadata_btn.click(
            fn=chatbi_app.export_table_metadata,
            outputs=[export_metadata_status, export_metadata_data]
        )
        
        import_metadata_btn.click(
            fn=chatbi_app.import_table_metadata,
            inputs=[import_metadata_data],
            outputs=[import_metadata_status]
        )
        
        # 回车键登录
        login_password.submit(
            handle_login,
            inputs=[login_employee_id, login_password],
            outputs=[
                is_authenticated, current_user_info, login_gate, main_app,
                user_info_display, login_status, login_employee_id, login_password, chatbot,
                table_dropdown, column_table_dropdown
            ]
        )
        
        # 启动时初始化
        def load_initial_data():
            """启动时加载初始数据"""
            try:
                # 加载知识库统计
                stats = chatbi_app.get_knowledge_stats()
                # 加载知识库表格
                kb_table = chatbi_app.get_knowledge_table()
                return stats, kb_table
            except Exception as e:
                return f"❌ 初始化失败: {str(e)}", pd.DataFrame()
        
        demo.load(
            fn=load_initial_data,
            outputs=[knowledge_stats, knowledge_table]
        )
    
    return demo


def launch_login_gate_app(server_name: str = "127.0.0.1", server_port: int = 7861,
                         share: bool = False, debug: bool = False):
    """
    启动登录门禁版ChatBI应用
    
    Args:
        server_name: 服务器地址
        server_port: 服务器端口
        share: 是否创建公共链接
        debug: 是否启用调试模式
    """
    try:
        app = create_login_gate_app()
        
        print(f"🚀 启动ChatBI登录门禁应用: http://{server_name}:{server_port}")
        print("📋 功能说明:")
        print("  - 🔐 用户必须通过登录门禁才能访问")
        print("  - 🎨 美观的全屏登录界面")
        print("  - 💬 完整的智能查询功能")
        print("  - 📊 自动可视化和数据分析")
        print("  - 👍 查询反馈和知识库")
        print("  - 🔒 基于用户权限的数据访问")
        print()
        print("🔑 使用方式:")
        print("  1. 首次访问会看到全屏登录界面")
        print("  2. 可以注册新账户或使用现有账户登录")
        print("  3. 登录成功后自动进入主应用界面")
        print("  4. 点击右上角登出按钮可返回登录界面")
        
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
    launch_login_gate_app(debug=True)