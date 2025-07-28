#!/usr/bin/env python3
"""
ChatBI 流式输出原型
演示如何实现对话式界面的流式响应
"""

import sys
import time
from pathlib import Path
from typing import List, Generator, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    import gradio as gr
    from chatbi.config import config
    from chatbi.orchestrator import get_orchestrator
except ImportError as e:
    print(f"导入错误: {e}")
    print("这是一个原型演示，需要安装gradio等依赖")
    sys.exit(1)

class StreamingChatBIApp:
    """流式输出ChatBI应用原型"""
    
    def __init__(self):
        self.orchestrator = None
        try:
            self.orchestrator = get_orchestrator()
        except Exception as e:
            print(f"初始化警告: {e}")
    
    def stream_chat_query(self, message: str, history: List) -> Generator[Tuple[List, str], None, None]:
        """流式处理查询"""
        if not message.strip():
            history.append([message, "❌ 请输入有效的查询问题"])
            yield history, None
            return
        
        try:
            # 阶段1: 开始处理
            history.append([message, "🚀 **开始处理您的查询...**"])
            yield history, None
            time.sleep(0.5)  # 模拟处理时间
            
            # 阶段2: Schema分析
            history[-1][1] = """🚀 **开始处理您的查询...**

📋 **正在分析数据库结构...**
- 检索相关表和字段
- 分析表之间的关系"""
            yield history, None
            time.sleep(1.0)
            
            # 阶段3: SQL生成
            history[-1][1] = """🚀 **开始处理您的查询...**

📋 ✅ **数据库结构分析完成**

🔧 **正在生成SQL查询...**
- 理解查询意图
- 构建SQL语句"""
            yield history, None
            time.sleep(1.5)
            
            # 如果有orchestrator，执行真实查询
            if self.orchestrator:
                result = self.orchestrator.query(
                    question=message,
                    auto_visualize=True,
                    analysis_level="standard"
                )
                
                # 阶段4: 显示SQL
                sql_display = f"```sql\n{result.sql_query}\n```" if result.sql_query else "SQL生成失败"
                history[-1][1] = f"""🚀 **开始处理您的查询...**

📋 ✅ **数据库结构分析完成**

🔧 ✅ **SQL查询生成完成**

### 生成的SQL查询
{sql_display}

⚡ **正在执行查询...**"""
                yield history, None
                time.sleep(1.0)
                
                # 阶段5: 执行结果
                if result.success:
                    metadata = result.metadata or {}
                    row_count = metadata.get('row_count', 0)
                    
                    history[-1][1] = f"""🚀 **开始处理您的查询...**

📋 ✅ **数据库结构分析完成**

🔧 ✅ **SQL查询生成完成**

### 生成的SQL查询
{sql_display}

⚡ ✅ **查询执行完成** - 获得 {row_count} 行数据

🔍 **正在分析数据...**"""
                    yield history, None
                    time.sleep(1.0)
                    
                    # 阶段6: 完整结果
                    final_response = self._build_complete_response(result)
                    history[-1][1] = final_response
                    
                    # 创建图表
                    chart_data = None
                    if result.data and len(result.data) > 0:
                        import pandas as pd
                        df = pd.DataFrame(result.data)
                        if result.chart_info and result.chart_info.get('success'):
                            chart_data = self._create_simple_chart(df, result.chart_info)
                    
                    yield history, chart_data
                else:
                    # 查询失败
                    history[-1][1] = f"""🚀 **开始处理您的查询...**

📋 ✅ **数据库结构分析完成**

🔧 ✅ **SQL查询生成完成**

### 生成的SQL查询
{sql_display}

⚡ ❌ **查询执行失败**

**错误信息**: {result.error}"""
                    yield history, None
            else:
                # 模拟模式
                history[-1][1] = self._build_demo_response(message)
                yield history, None
                
        except Exception as e:
            error_response = f"❌ **系统错误**\n\n```\n{str(e)}\n```"
            history.append([message, error_response])
            yield history, None
    
    def _build_complete_response(self, result) -> str:
        """构建完整的响应"""
        response_parts = []
        
        # 查询摘要
        metadata = result.metadata or {}
        response_parts.append(f"✅ **查询完成** (耗时: {result.execution_time:.2f}秒)")
        response_parts.append(f"📊 获得 **{metadata.get('row_count', 0)}** 行数据")
        response_parts.append("")
        
        # SQL查询
        if result.sql_query:
            response_parts.append("### 🔧 生成的SQL查询")
            response_parts.append(f"```sql\n{result.sql_query}\n```")
            response_parts.append("")
        
        # 数据结果
        if result.data and len(result.data) > 0:
            import pandas as pd
            df = pd.DataFrame(result.data)
            
            response_parts.append("### 📊 数据结果")
            response_parts.append(f"**字段**: {', '.join(df.columns)}")
            
            # 数据预览
            display_df = df.head(3)  # 流式输出时显示更少行
            response_parts.append("\n**数据预览**:")
            response_parts.append(display_df.to_markdown(index=False))
            
            if len(df) > 3:
                response_parts.append(f"\n*显示前3行，总共{len(df)}行*")
            response_parts.append("")
        
        # 智能分析
        if result.analysis:
            response_parts.append("### 🔍 智能分析")
            response_parts.append(result.analysis)
            response_parts.append("")
        
        # 可视化说明
        viz_suggestion = metadata.get('visualization_suggestion', {})
        if viz_suggestion and viz_suggestion.get('chart_type') != 'none':
            response_parts.append("### 🎨 数据可视化")
            response_parts.append(f"✅ 已生成 **{viz_suggestion.get('chart_type')}** 图表")
        
        return "\n".join(response_parts)
    
    def _build_demo_response(self, message: str) -> str:
        """构建演示响应"""
        return f"""✅ **查询完成** (演示模式)

### 🔧 生成的SQL查询
```sql
-- 这是一个演示查询，基于问题: {message}
SELECT column1, column2, COUNT(*) as count
FROM demo_table 
WHERE condition = 'value'
GROUP BY column1, column2
ORDER BY count DESC
LIMIT 10;
```

### 📊 数据结果
**字段**: column1, column2, count

**数据预览**:
| column1 | column2 | count |
|---------|---------|-------|
| 示例1   | 类型A   | 150   |
| 示例2   | 类型B   | 120   |
| 示例3   | 类型C   | 95    |

*显示前3行，总共10行*

### 🔍 智能分析
根据查询结果分析，数据显示了明显的分布特征。示例1的数量最多，占总数的约30%，这表明该类别在数据中占主导地位。

### 🎨 数据可视化
✅ 已生成 **bar** 图表 - 柱状图最适合展示不同类别的数量对比

---
*这是演示模式，请配置数据库连接以获得真实查询结果*"""
    
    def _create_simple_chart(self, df, chart_info):
        """创建简单图表"""
        try:
            import plotly.express as px
            
            chart_type = chart_info.get('chart_type', 'bar')
            x_col = df.columns[0] if len(df.columns) > 0 else None
            y_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            
            if chart_type == 'bar':
                fig = px.bar(df.head(10), x=x_col, y=y_col, title="数据可视化")
            else:
                fig = px.bar(df.head(10), x=x_col, y=y_col, title="数据可视化")
            
            fig.update_layout(height=400)
            return fig
        except Exception as e:
            print(f"图表创建失败: {e}")
            return None

def create_streaming_interface():
    """创建流式输出界面"""
    app = StreamingChatBIApp()
    
    css = """
    .gradio-container {
        max-width: 1200px !important;
    }
    .streaming-status {
        color: #1f77b4;
        font-weight: bold;
    }
    """
    
    with gr.Blocks(title="ChatBI 流式输出原型", css=css, theme=gr.themes.Soft()) as interface:
        
        gr.Markdown("""
        # 🚀 ChatBI 流式输出原型
        
        体验实时的AI数据查询处理过程！输入问题后，您将看到AI逐步处理的每个阶段。
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                # 对话界面
                chatbot = gr.Chatbot(
                    label="ChatBI 流式助手",
                    height=500,
                    show_label=True
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        label="输入您的问题",
                        placeholder="例如：显示销售额最高的前10个区域",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1)
                
                # 示例按钮
                with gr.Row():
                    examples = [
                        "显示所有表的记录数",
                        "按地区统计销售总额",
                        "销售额最高的前10个客户"
                    ]
                    
                    for example in examples:
                        btn = gr.Button(example, variant="secondary", size="sm")
                        btn.click(
                            lambda x=example: (x, []),
                            outputs=[msg_input, chatbot]
                        )
            
            with gr.Column(scale=1):
                # 图表展示
                gr.Markdown("### 📊 实时图表")
                chart_display = gr.Plot(show_label=False)
                
                # 状态说明
                gr.Markdown("""
                ### 💡 流式处理阶段
                
                1. 🚀 **开始处理** - 接收用户问题
                2. 📋 **Schema分析** - 分析数据库结构
                3. 🔧 **SQL生成** - 智能生成查询语句
                4. ⚡ **执行查询** - 安全执行SQL
                5. 🔍 **数据分析** - AI分析结果
                6. 🎨 **可视化** - 生成图表展示
                """)
        
        # 事件绑定
        def handle_submit(message, history):
            return app.stream_chat_query(message, history)
        
        msg_input.submit(
            handle_submit,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, chart_display]
        ).then(
            lambda: "",  # 清空输入框
            outputs=[msg_input]
        )
        
        send_btn.click(
            handle_submit,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, chart_display]
        ).then(
            lambda: "",  # 清空输入框
            outputs=[msg_input]
        )
        
        # 欢迎信息
        interface.load(
            lambda: [[
                "", 
                "👋 欢迎使用ChatBI流式输出原型！\n\n✨ **新特性**:\n- 🔄 实时显示处理过程\n- ⚡ 分阶段展示结果\n- 🎯 减少等待焦虑\n\n请输入您的数据查询问题，体验流式响应！"
            ]],
            outputs=[chatbot]
        )
    
    return interface

if __name__ == "__main__":
    print("🚀 启动ChatBI流式输出原型...")
    
    interface = create_streaming_interface()
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,  # 使用不同端口避免冲突
        share=False,
        debug=True,
        show_error=True
    )