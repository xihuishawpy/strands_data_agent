#!/usr/bin/env python3
"""
ChatBI 对话式Gradio前端界面
提供人机交互式的智能数据查询体验
"""

import os
import sys
import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    import gradio as gr
    from chatbi.config import config
    from chatbi.orchestrator import get_orchestrator
    from chatbi.database import get_database_connector, get_schema_manager
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install gradio openai")
    sys.exit(1)

class ChatBIApp:
    """ChatBI 对话式应用"""
    
    def __init__(self):
        """初始化应用"""
        self.orchestrator = None
        self.connector = None
        self.schema_manager = None
        self.chat_history = []
        
        # 尝试初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化ChatBI组件"""
        try:
            self.orchestrator = get_orchestrator()
            self.connector = get_database_connector()
            self.schema_manager = get_schema_manager()
            return True, "✅ ChatBI系统初始化成功"
        except Exception as e:
            error_msg = f"❌ 系统初始化失败: {str(e)}"
            return False, error_msg
    
    def chat_query(self, message: str, history: List, auto_viz: bool = True, analysis_level: str = "standard"):
        """处理对话式查询"""
        if not message.strip():
            history.append([message, "❌ 请输入有效的查询问题"])
            return history, "", None
        
        try:
            if not self.orchestrator:
                history.append([message, "❌ 系统未初始化，请检查配置"])
                return history, "", None
            
            # 执行查询
            result = self.orchestrator.query(
                question=message,
                auto_visualize=auto_viz,
                analysis_level=analysis_level
            )
            
            if not result.success:
                error_response = f"❌ 查询失败\n\n**错误信息**: {result.error}"
                history.append([message, error_response])
                return history, "", None
            
            # 构建对话式回复
            response_parts = []
            
            # 1. 查询摘要
            metadata = result.metadata or {}
            response_parts.append(f"✅ **查询完成** (耗时: {result.execution_time:.2f}秒)")
            response_parts.append(f"📊 获得 **{metadata.get('row_count', 0)}** 行数据")
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
            chart_data = None
            if result.data and len(result.data) > 0:
                df = pd.DataFrame(result.data)
                
                response_parts.append("### 📊 数据结果")
                response_parts.append(f"**字段**: {', '.join(df.columns)}")
                
                # 数据预览（前5行）
                display_df = df.head(5)
                formatted_df = display_df.copy()
                for col in formatted_df.columns:
                    if formatted_df[col].dtype in ['int64', 'float64']:
                        formatted_df[col] = formatted_df[col].apply(self._format_number)
                
                response_parts.append("\n**数据预览**:")
                response_parts.append(formatted_df.to_markdown(index=False))
                
                if len(df) > 5:
                    response_parts.append(f"\n*显示前5行，总共{len(df)}行*")
                response_parts.append("")
                
                # 准备图表数据
                if auto_viz and result.chart_info and result.chart_info.get('success'):
                    chart_data = self._create_plotly_chart(df, result.chart_info)
                elif auto_viz and metadata.get('visualization_suggestion'):
                    chart_data = self._create_chart_from_suggestion(df, metadata['visualization_suggestion'])
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
                    if chart_data:
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
            
            # 更新历史记录
            full_response = "\n".join(response_parts)
            history.append([message, full_response])
            
            # 添加到内部历史
            self.chat_history.append({
                "question": message,
                "sql": result.sql_query,
                "success": True,
                "rows": len(result.data) if result.data and isinstance(result.data, list) else 0
            })
            
            return history, "", chart_data
            
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
    
    # 系统管理功能
    def test_connection(self) -> Tuple[str, str]:
        """测试数据库连接"""    
        try:
            if not self.connector:
                return "❌ 连接失败", "数据库连接器未初始化"
            
            success = self.connector.connect()
            if success:
                tables = self.connector.get_table_names()
                table_count = len(tables) if tables else 0
                
                info = f"""
### 🔗 数据库连接成功
- **数据库类型**: {config.database.type}
- **主机**: {config.database.host}:{config.database.port}
- **数据库**: {config.database.database}
- **表数量**: {table_count}个
- **连接状态**: ✅ 正常
                """
                
                return "✅ 连接成功", info
            else:
                return "❌ 连接失败", "无法连接到数据库，请检查配置"
                
        except Exception as e:
            return "❌ 连接失败", f"连接测试失败: {str(e)}"
    
    def get_schema_info(self) -> Tuple[str, str]:
        """获取数据库Schema信息"""
        try:
            if not self.schema_manager:
                return "❌ 获取失败", "Schema管理器未初始化"
            
            schema = self.schema_manager.get_database_schema()
            
            if not schema or not schema.get("tables"):
                return "⚠️ 无数据", "数据库中没有找到表"
            
            info_parts = ["### 📊 数据库Schema信息\n"]
            
            tables = schema.get("tables", {})
            table_names = list(tables.keys())
            
            for table_name in table_names[:10]:
                table_info = tables[table_name]
                
                info_parts.append(f"#### 表: `{table_name}`")
                
                columns = table_info.get('columns', [])
                if columns:
                    info_parts.append("**字段:**")
                    for col in columns[:8]:
                        col_info = f"- `{col.get('name', 'Unknown')}` ({col.get('type', 'Unknown')})"
                        if not col.get('nullable', True):
                            col_info += " [NOT NULL]"
                        info_parts.append(col_info)
                    
                    if len(columns) > 8:
                        info_parts.append(f"- ... 还有 {len(columns) - 8} 个字段")
                
                primary_keys = table_info.get('primary_keys', [])
                if primary_keys:
                    info_parts.append(f"**主键:** {', '.join(primary_keys)}")
                
                info_parts.append("")
            
            if len(table_names) > 10:
                info_parts.append(f"*... 还有 {len(table_names) - 10} 个表*")
            
            return "✅ 获取成功", "\n".join(info_parts)
            
        except Exception as e:
            error_detail = f"获取Schema失败: {str(e)}\n\n详细错误:\n```\n{traceback.format_exc()}\n```"
            return "❌ 获取失败", error_detail
    
    def refresh_schema(self) -> Tuple[str, str]:
        """刷新Schema缓存"""
        try:
            if not self.orchestrator:
                return "❌ 错误", "系统未初始化"
            
            success = self.orchestrator.refresh_schema()
            
            if success:
                return "✅ 刷新成功", "Schema缓存已刷新"
            else:
                return "❌ 刷新失败", "Schema缓存刷新失败"
                
        except Exception as e:
            return "❌ 刷新失败", f"刷新失败: {str(e)}"

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
                        
                        with gr.Row():
                            msg_input = gr.Textbox(
                                label="输入您的问题",
                                placeholder="例如：显示销售额最高的前10个区域",
                                lines=2,
                                scale=4
                            )
                            send_btn = gr.Button("发送", variant="primary", scale=1)
                        
                        # 查询选项
                        with gr.Row():
                            auto_viz = gr.Checkbox(label="自动可视化", value=True)
                            analysis_level = gr.Dropdown(
                                label="分析级别",
                                choices=["basic", "standard", "detailed"],
                                value="standard"
                            )
                            clear_btn = gr.Button("清空对话", variant="secondary")
                    
                    with gr.Column(scale=2):
                        # 可视化展示区域
                        gr.Markdown("### 📊 数据可视化")
                        chart_display = gr.Plot(
                            label="图表",
                            show_label=False,
                            container=True
                        )
                        
                        # 快速查询示例
                        gr.Markdown("""
                        ### 💡 查询示例
                        
                        点击下方示例快速开始：
                        """)
                        
                        example_btns = []
                        examples = [
                            "显示所有表的记录数",
                            "按地区统计销售总额", 
                            "销售额最高的前10个客户",
                            "最近一个月的销售趋势"
                        ]
                        
                        for example in examples:
                            btn = gr.Button(example, variant="secondary", size="sm")
                            example_btns.append(btn)
            
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
        
        # 事件绑定
        
        # 对话功能
        def respond(message, history, auto_viz, analysis_level):
            try:
                updated_history, cleared_input, chart = app.chat_query(message, history, auto_viz, analysis_level)
                return updated_history, "", chart  # 返回更新的历史、清空输入框、图表
            except Exception as e:
                # 处理异常情况
                error_msg = f"❌ 处理错误: {str(e)}"
                history.append([message, error_msg])
                return history, "", None
        
        msg_input.submit(
            respond,
            inputs=[msg_input, chatbot, auto_viz, analysis_level],
            outputs=[chatbot, msg_input, chart_display]
        )
        
        send_btn.click(
            respond,
            inputs=[msg_input, chatbot, auto_viz, analysis_level],
            outputs=[chatbot, msg_input, chart_display]
        )
        
        # 清空对话
        clear_btn.click(
            lambda: ([], None),
            outputs=[chatbot, chart_display]
        )
        
        # 示例按钮
        def handle_example(example_text):
            return respond(example_text, [], True, "standard")
        
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
        
        # 启动时的欢迎信息
        def load_welcome():
            welcome_msg = "👋 您好！我是ChatBI智能助手。\n\n我可以帮您：\n- 🔍 用自然语言查询数据库\n- 📊 自动生成SQL和执行查询\n- 🎨 创建数据可视化图表\n- 🔍 提供智能数据分析\n\n请输入您的问题开始对话！"
            return [["", welcome_msg]], None
        
        interface.load(
            load_welcome,
            outputs=[chatbot, chart_display]
        )
    
    return interface

if __name__ == "__main__":
    interface = create_chat_interface()
    
    print("🚀 启动ChatBI对话式界面...")
    print(f"📊 数据库类型: {config.database.type}")
    print(f"🤖 AI模型: {config.llm.model_name}")
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=False,
        show_error=True
    )