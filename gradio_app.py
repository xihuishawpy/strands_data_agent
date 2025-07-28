#!/usr/bin/env python3
"""
ChatBI Gradio前端界面
提供用户友好的Web界面来使用ChatBI智能数据查询系统
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

class ChatBIGradioApp:
    """ChatBI Gradio应用"""
    
    def __init__(self):
        """初始化应用"""
        self.orchestrator = None
        self.connector = None
        self.schema_manager = None
        self.sql_fixer = None
        self.chat_history = []
        
        # 尝试初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化ChatBI组件"""
        try:
            self.orchestrator = get_orchestrator()
            self.connector = get_database_connector()
            self.schema_manager = get_schema_manager()
            
            # 导入SQL修复智能体
            from chatbi.agents import get_sql_fixer
            self.sql_fixer = get_sql_fixer()
            
            return True, "✅ ChatBI系统初始化成功"
        except Exception as e:
            error_msg = f"❌ 系统初始化失败: {str(e)}"
            return False, error_msg
    
    def test_connection(self) -> Tuple[str, str]:
        """测试数据库连接"""
        try:
            if not self.connector:
                return "❌ 连接失败", "数据库连接器未初始化"
            
            # 测试连接
            success = self.connector.connect()
            if success:
                # 获取基本信息
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
            
            # 获取完整的数据库Schema
            schema = self.schema_manager.get_database_schema()
            
            if not schema or not schema.get("tables"):
                return "⚠️ 无数据", "数据库中没有找到表"
            
            # 构建表信息展示
            info_parts = ["### 📊 数据库Schema信息\n"]
            
            tables = schema.get("tables", {})
            table_names = list(tables.keys())
            
            for table_name in table_names[:10]:  # 最多显示10个表
                table_info = tables[table_name]
                
                info_parts.append(f"#### 表: `{table_name}`")
                
                columns = table_info.get('columns', [])
                if columns:
                    info_parts.append("**字段:**")
                    for col in columns[:8]:  # 最多显示8个字段
                        col_info = f"- `{col.get('name', 'Unknown')}` ({col.get('type', 'Unknown')})"
                        if not col.get('nullable', True):
                            col_info += " [NOT NULL]"
                        info_parts.append(col_info)
                    
                    if len(columns) > 8:
                        info_parts.append(f"- ... 还有 {len(columns) - 8} 个字段")
                
                # 显示主键信息
                primary_keys = table_info.get('primary_keys', [])
                if primary_keys:
                    info_parts.append(f"**主键:** {', '.join(primary_keys)}")
                
                info_parts.append("")
            
            if len(table_names) > 10:
                info_parts.append(f"*... 还有 {len(table_names) - 10} 个表*")
            
            return "✅ 获取成功", "\n".join(info_parts)
            
        except Exception as e:
            import traceback
            error_detail = f"获取Schema失败: {str(e)}\n\n详细错误:\n```\n{traceback.format_exc()}\n```"
            return "❌ 获取失败", error_detail
    
    def process_query(self, question: str, auto_viz: bool = True, analysis_level: str = "standard") -> Tuple[str, str, str, Optional[Dict], str]:
        """处理用户查询"""
        if not question.strip():
            return "❌ 错误", "请输入查询问题", "", None, ""
        
        try:
            if not self.orchestrator:
                return "❌ 错误", "系统未初始化", "", None, ""
            
            # 执行查询
            print(f"[DEBUG] 开始执行查询: {question}")
            result = self.orchestrator.query(
                question=question,
                auto_visualize=auto_viz,
                analysis_level=analysis_level
            )
            print(f"[DEBUG] 查询结果: 成功={result.success}, SQL={result.sql_query}, 数据行数={len(result.data) if result.data else 0}")
            
            if not result.success:
                print(f"[DEBUG] 查询失败原因: {result.error}")
            
            if not result.success:
                return "❌ 查询失败", result.error or "未知错误", "", None, ""
            
            # 构建返回结果
            status = "✅ 查询成功"
            
            # SQL查询
            sql_display = f"```sql\n{result.sql_query}\n```" if result.sql_query else "无SQL查询"
            
            # 数据结果
            data_display = ""
            chart_data = None
            
            if result.data:
                # 创建DataFrame用于显示
                df = pd.DataFrame(result.data)
                
                # 限制显示行数
                display_df = df.head(20)
                data_display = f"### 📊 查询结果 (共{len(df)}行)\n\n"
                data_display += display_df.to_markdown(index=False)
                
                if len(df) > 20:
                    data_display += f"\n\n*仅显示前20行，总共{len(df)}行*"
                
                # 准备图表数据
                if auto_viz and result.chart_info and result.chart_info.get('success'):
                    chart_data = self._create_plotly_chart(df, result.chart_info)
            else:
                data_display = "查询未返回数据"
            
            # 分析结果
            analysis_display = ""
            if result.analysis:
                analysis_display = f"### 🔍 数据分析\n\n{result.analysis}"
            
            # 添加到聊天历史
            self.chat_history.append({
                "question": question,
                "sql": result.sql_query,
                "success": True,
                "rows": len(result.data) if result.data else 0
            })
            
            return status, sql_display, data_display, chart_data, analysis_display
            
        except Exception as e:
            error_msg = f"查询处理失败: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
            return "❌ 系统错误", error_msg, "", None, ""
    
    def _create_plotly_chart(self, df: pd.DataFrame, chart_info: Dict) -> Optional[go.Figure]:
        """创建Plotly图表"""
        try:
            chart_type = chart_info.get('chart_type', 'bar')
            title = chart_info.get('title', '数据可视化')
            x_col = chart_info.get('x_column')
            y_col = chart_info.get('y_column')
            
            if not x_col or not y_col or x_col not in df.columns or y_col not in df.columns:
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
    
    def explain_query(self, question: str) -> Tuple[str, str]:
        """解释查询计划"""
        if not question.strip():
            return "❌ 错误", "请输入查询问题"
        
        try:
            if not self.orchestrator:
                return "❌ 错误", "系统未初始化"
            
            explanation = self.orchestrator.explain_query(question)
            
            if "error" in explanation:
                return "❌ 解释失败", explanation["error"]
            
            # 构建解释信息
            info_parts = ["### 🔍 查询解释\n"]
            
            info_parts.append(f"**原始问题:** {explanation.get('question', 'N/A')}")
            
            if explanation.get('sql_query'):
                info_parts.append(f"**生成的SQL:**")
                info_parts.append(f"```sql\n{explanation['sql_query']}\n```")
            
            if explanation.get('sql_valid'):
                info_parts.append("**SQL有效性:** ✅ 有效")
            else:
                info_parts.append("**SQL有效性:** ❌ 无效")
            
            if explanation.get('tables_involved'):
                info_parts.append(f"**涉及的表:** {', '.join(explanation['tables_involved'])}")
            
            if explanation.get('execution_plan'):
                info_parts.append("**执行计划:**")
                info_parts.append(f"```\n{explanation['execution_plan']}\n```")
            
            return "✅ 解释成功", "\n".join(info_parts)
            
        except Exception as e:
            return "❌ 解释失败", f"查询解释失败: {str(e)}"
    
    def get_chat_history(self) -> str:
        """获取聊天历史"""
        if not self.chat_history:
            return "暂无查询历史"
        
        history_parts = ["### 📝 查询历史\n"]
        
        for i, item in enumerate(reversed(self.chat_history[-10:]), 1):
            status = "✅" if item['success'] else "❌"
            history_parts.append(f"**{i}.** {status} {item['question']}")
            
            if item.get('sql'):
                history_parts.append(f"   SQL: `{item['sql'][:100]}...`")
            
            if item.get('rows') is not None:
                history_parts.append(f"   结果: {item['rows']} 行")
            
            history_parts.append("")
        
        return "\n".join(history_parts)
    
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
    
    def optimize_sql(self, sql: str) -> Tuple[str, str]:
        """优化SQL查询"""
        if not sql.strip():
            return "❌ 错误", "请输入SQL查询"
        
        try:
            if not self.sql_fixer or not self.schema_manager:
                return "❌ 错误", "系统未初始化"
            
            # 获取Schema信息
            schema = self.schema_manager.get_database_schema()
            schema_summary = self.schema_manager.get_schema_summary()
            
            # 获取优化建议
            optimization = self.sql_fixer.suggest_query_improvements(sql, schema_summary)
            
            # 构建优化结果显示
            result_parts = ["### 🚀 SQL优化建议\n"]
            
            # 性能评分
            score = optimization.get("performance_score", 0.5)
            score_emoji = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🔴"
            result_parts.append(f"**性能评分**: {score_emoji} {score:.1f}/1.0\n")
            
            # 优化建议
            optimizations = optimization.get("optimizations", [])
            if optimizations:
                result_parts.append("**优化建议**:")
                for opt in optimizations:
                    impact = opt.get("impact", "未知")
                    impact_emoji = "🔥" if impact == "高" else "⚡" if impact == "中" else "💡"
                    result_parts.append(f"- {impact_emoji} **{opt.get('type', '优化')}**: {opt.get('description', '')}")
                result_parts.append("")
            
            # 优化后的SQL
            optimized_sql = optimization.get("optimized_sql", "")
            if optimized_sql and optimized_sql.strip() != sql.strip():
                result_parts.append("**优化后的SQL**:")
                result_parts.append(f"```sql\n{optimized_sql}\n```")
                result_parts.append("")
            
            # 详细说明
            explanation = optimization.get("explanation", "")
            if explanation:
                result_parts.append("**详细说明**:")
                result_parts.append(explanation)
            
            return "✅ 优化完成", "\n".join(result_parts)
            
        except Exception as e:
            return "❌ 优化失败", f"SQL优化失败: {str(e)}"

def create_gradio_interface():
    """创建Gradio界面"""
    app = ChatBIGradioApp()
    
    # 自定义CSS
    css = """
    .gradio-container {
        max-width: 1200px !important;
    }
    .panel {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    """
    
    with gr.Blocks(title="ChatBI 智能数据查询系统", css=css, theme=gr.themes.Soft()) as interface:
        
        gr.Markdown("""
        # 🤖 ChatBI 智能数据查询系统
        
        使用自然语言查询数据库，自动生成SQL、执行查询、分析数据并可视化展示。
        """)
        
        # 系统状态面板
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 🔧 系统状态")
                
                with gr.Row():
                    test_conn_btn = gr.Button("测试数据库连接", variant="secondary")
                    refresh_schema_btn = gr.Button("刷新Schema", variant="secondary")
                
                conn_status = gr.Textbox(label="连接状态", interactive=False)
                conn_info = gr.Markdown("点击'测试数据库连接'检查系统状态")
        
        # 主要功能区域
        gr.Markdown("## 💬 智能查询")
        
        with gr.Row():
            with gr.Column(scale=2):
                # 查询输入
                question_input = gr.Textbox(
                    label="输入您的问题",
                    placeholder="例如：显示销售额最高的前10个区域",
                    lines=3
                )
                
                with gr.Row():
                    query_btn = gr.Button("🔍 执行查询", variant="primary")
                    explain_btn = gr.Button("📋 解释查询", variant="secondary")
                
                # 查询选项
                with gr.Row():
                    auto_viz = gr.Checkbox(label="自动可视化", value=True)
                    analysis_level = gr.Dropdown(
                        label="分析级别",
                        choices=["basic", "standard", "detailed"],
                        value="standard"
                    )
            
            with gr.Column(scale=1):
                # 查询历史
                gr.Markdown("### 📝 查询历史")
                history_display = gr.Markdown("暂无查询历史")
                refresh_history_btn = gr.Button("刷新历史", size="sm")
        
        # 结果展示区域
        gr.Markdown("## 📊 查询结果")
        
        # 状态显示
        result_status = gr.Textbox(label="查询状态", interactive=False)
        
        with gr.Tabs():
            with gr.TabItem("SQL查询"):
                sql_display = gr.Markdown("等待查询...")
            
            with gr.TabItem("数据结果"):
                data_display = gr.Markdown("等待查询...")
            
            with gr.TabItem("数据可视化"):
                chart_display = gr.Plot(label="图表")
            
            with gr.TabItem("智能分析"):
                analysis_display = gr.Markdown("等待查询...")
        
        # Schema信息面板
        with gr.Accordion("🗄️ 数据库Schema信息", open=False):
            with gr.Row():
                get_schema_btn = gr.Button("获取Schema信息")
                schema_status = gr.Textbox(label="获取状态", interactive=False)
            schema_display = gr.Markdown("点击'获取Schema信息'查看数据库结构")
        
        # 查询解释面板
        with gr.Accordion("🔍 查询解释", open=False):
            explain_status = gr.Textbox(label="解释状态", interactive=False)
            explain_display = gr.Markdown("使用'解释查询'按钮获取详细解释")
        
        # SQL优化面板
        with gr.Accordion("🚀 SQL优化", open=False):
            with gr.Row():
                sql_input = gr.Textbox(
                    label="输入SQL查询",
                    placeholder="SELECT * FROM table_name WHERE condition",
                    lines=3
                )
                optimize_btn = gr.Button("优化SQL", variant="primary")
            optimize_status = gr.Textbox(label="优化状态", interactive=False)
            optimize_display = gr.Markdown("输入SQL查询并点击'优化SQL'获取优化建议")
        
        # 事件绑定
        test_conn_btn.click(
            fn=app.test_connection,
            outputs=[conn_status, conn_info]
        )
        
        refresh_schema_btn.click(
            fn=app.refresh_schema,
            outputs=[conn_status, conn_info]
        )
        
        query_btn.click(
            fn=app.process_query,
            inputs=[question_input, auto_viz, analysis_level],
            outputs=[result_status, sql_display, data_display, chart_display, analysis_display]
        )
        
        explain_btn.click(
            fn=app.explain_query,
            inputs=[question_input],
            outputs=[explain_status, explain_display]
        )
        
        get_schema_btn.click(
            fn=app.get_schema_info,
            outputs=[schema_status, schema_display]
        )
        
        refresh_history_btn.click(
            fn=app.get_chat_history,
            outputs=[history_display]
        )
        
        optimize_btn.click(
            fn=app.optimize_sql,
            inputs=[sql_input],
            outputs=[optimize_status, optimize_display]
        )
        
        # 示例查询
        gr.Markdown("""
        ## 💡 功能说明
        
        ### 🔍 智能查询
        您可以尝试以下类型的查询：
        - **数据概览**: "显示所有表的记录数"
        - **统计分析**: "按地区统计销售总额"  
        - **排名查询**: "销售额最高的前10个客户"
        - **时间分析**: "最近一个月的销售趋势"
        - **数据筛选**: "价格大于1000元的产品"
        
        ### 🚀 SQL优化
        - 输入您的SQL查询获取性能优化建议
        - 自动检测潜在的性能问题
        - 提供具体的优化方案和改进建议
        - 生成优化后的SQL语句
        
        ### 🔧 自动修复
        - 系统会自动检测并修复SQL错误
        - 智能分析语法错误、字段名错误等问题
        - 提供详细的错误分析和修复说明
        - 确保生成安全可执行的SQL语句
        """)
    
    return interface

if __name__ == "__main__":
    # 创建并启动界面
    interface = create_gradio_interface()
    
    print("🚀 启动ChatBI Gradio界面...")
    print(f"📊 数据库类型: {config.database.type}")
    print(f"🤖 AI模型: {config.llm.model_name}")
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=False,
        show_error=True
    ) 