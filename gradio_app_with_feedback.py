#!/usr/bin/env python3
"""
带反馈功能的ChatBI Gradio应用
演示SQL知识库和用户反馈功能
"""

import gradio as gr
import logging
import json
from typing import Dict, Any, Optional, Tuple

from chatbi.orchestrator import get_orchestrator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatBIWithFeedback:
    """带反馈功能的ChatBI应用"""
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self.last_query_result = None
    
    def query_with_feedback(self, question: str) -> Tuple[str, str, str, str]:
        """
        执行查询并返回结果，支持反馈
        
        Returns:
            Tuple: (sql_query, data_display, analysis, feedback_info)
        """
        if not question.strip():
            return "", "请输入问题", "", "请先提出问题"
        
        try:
            # 执行查询
            result = self.orchestrator.query(
                question=question,
                auto_visualize=False,  # 简化演示
                analysis_level="standard"
            )
            
            # 保存查询结果用于反馈
            self.last_query_result = result
            
            if result.success:
                # 格式化SQL
                sql_display = f"```sql\n{result.sql_query}\n```"
                
                # 格式化数据
                if result.data:
                    data_display = self._format_data_table(result.data[:10])  # 只显示前10行
                    if len(result.data) > 10:
                        data_display += f"\n\n... (共 {len(result.data)} 行数据)"
                else:
                    data_display = "查询结果为空"
                
                # 分析结果
                analysis = result.analysis or "无分析结果"
                
                # 反馈信息
                feedback_info = "✅ 查询成功！如果结果满意，请点击👍按钮将此查询添加到知识库"
                
                return sql_display, data_display, analysis, feedback_info
            
            else:
                return "", f"❌ 查询失败: {result.error}", "", "查询失败，无法提供反馈"
        
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            return "", f"❌ 系统错误: {str(e)}", "", "系统错误，无法提供反馈"
    
    def add_positive_feedback(self, description: str = "") -> str:
        """添加正面反馈"""
        if not self.last_query_result or not self.last_query_result.success:
            return "❌ 没有可反馈的查询结果"
        
        try:
            success = self.orchestrator.add_positive_feedback(
                question=self.last_query_result.question,
                sql=self.last_query_result.sql_query,
                description=description or "用户点赞的查询"
            )
            
            if success:
                return "✅ 感谢反馈！已将此查询添加到知识库，将帮助改进未来的查询生成"
            else:
                return "⚠️ 反馈添加失败，可能是知识库未启用"
        
        except Exception as e:
            logger.error(f"添加反馈失败: {str(e)}")
            return f"❌ 反馈添加失败: {str(e)}"
    
    def get_knowledge_stats(self) -> str:
        """获取知识库统计"""
        try:
            stats = self.orchestrator.get_knowledge_stats()
            
            if stats.get("enabled"):
                return f"""
📊 **知识库统计**

- 总条目数: {stats.get('total_items', 0)}
- 平均评分: {stats.get('avg_rating', 0):.2f}
- 总使用次数: {stats.get('total_usage', 0)}
- 高评分条目: {stats.get('top_rated_count', 0)}
- 集合名称: {stats.get('collection_name', 'N/A')}
                """
            else:
                return f"❌ 知识库未启用: {stats.get('reason', '未知原因')}"
        
        except Exception as e:
            return f"❌ 获取统计失败: {str(e)}"
    
    def _format_data_table(self, data) -> str:
        """格式化数据表格"""
        if not data:
            return "无数据"
        
        # 获取列名
        columns = list(data[0].keys())
        
        # 创建表格
        table_lines = []
        
        # 表头
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        
        table_lines.append(header)
        table_lines.append(separator)
        
        # 数据行
        for row in data:
            row_data = []
            for col in columns:
                value = row.get(col, "")
                # 处理None值和长文本
                if value is None:
                    value = "NULL"
                else:
                    value = str(value)
                    if len(value) > 50:
                        value = value[:47] + "..."
                row_data.append(value)
            
            table_lines.append("| " + " | ".join(row_data) + " |")
        
        return "\n".join(table_lines)

def create_interface():
    """创建Gradio界面"""
    app = ChatBIWithFeedback()
    
    with gr.Blocks(title="ChatBI with Feedback", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🤖 ChatBI - 智能数据查询 (带反馈功能)")
        gr.Markdown("通过自然语言查询数据库，并可以对满意的结果进行反馈，帮助改进AI的查询生成能力")
        
        with gr.Row():
            with gr.Column(scale=2):
                # 查询输入
                question_input = gr.Textbox(
                    label="💬 请输入您的问题",
                    placeholder="例如：查询用户总数、统计每月订单量、显示最近7天的销售趋势...",
                    lines=2
                )
                
                query_btn = gr.Button("🚀 执行查询", variant="primary")
                
                # 查询结果显示
                with gr.Tab("SQL查询"):
                    sql_output = gr.Markdown(label="生成的SQL")
                
                with gr.Tab("查询数据"):
                    data_output = gr.Markdown(label="查询结果")
                
                with gr.Tab("智能分析"):
                    analysis_output = gr.Markdown(label="数据分析")
            
            with gr.Column(scale=1):
                # 反馈区域
                gr.Markdown("## 📝 查询反馈")
                
                feedback_info = gr.Markdown("请先执行查询")
                
                feedback_description = gr.Textbox(
                    label="反馈描述 (可选)",
                    placeholder="描述这个查询的用途或特点...",
                    lines=2
                )
                
                like_btn = gr.Button("👍 满意，添加到知识库", variant="secondary")
                
                feedback_result = gr.Markdown()
                
                # 知识库统计
                gr.Markdown("## 📊 知识库状态")
                stats_btn = gr.Button("刷新统计", size="sm")
                stats_output = gr.Markdown()
        
        # 事件绑定
        query_btn.click(
            fn=app.query_with_feedback,
            inputs=[question_input],
            outputs=[sql_output, data_output, analysis_output, feedback_info]
        )
        
        like_btn.click(
            fn=app.add_positive_feedback,
            inputs=[feedback_description],
            outputs=[feedback_result]
        )
        
        stats_btn.click(
            fn=app.get_knowledge_stats,
            outputs=[stats_output]
        )
        
        # 页面加载时显示统计
        interface.load(
            fn=app.get_knowledge_stats,
            outputs=[stats_output]
        )
        
        # 示例问题
        gr.Examples(
            examples=[
                ["查询用户总数"],
                ["统计活跃用户数量"],
                ["按月统计订单数量"],
                ["查询最近7天的销售额"],
                ["显示用户注册趋势"],
                ["查找高价值客户"]
            ],
            inputs=[question_input]
        )
    
    return interface

if __name__ == "__main__":
    print("🚀 启动带反馈功能的ChatBI应用")
    
    # 检查依赖
    try:
        import chromadb
        print("✅ ChromaDB已安装，知识库功能可用")
    except ImportError:
        print("⚠️ ChromaDB未安装，知识库功能将被禁用")
        print("   安装命令: pip install chromadb sentence-transformers")
    
    # 创建并启动界面
    interface = create_interface()
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        debug=True
    )