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
        self.last_query_result = None  # 存储最后一次查询结果，用于反馈
        
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
            print(f"[DEBUG] 🚀 开始智能查询流程: {question}")
            result = self.orchestrator.query(
                question=question,
                auto_visualize=auto_viz,
                analysis_level=analysis_level
            )
            
            # 详细的调试信息
            print(f"[DEBUG] 查询结果: 成功={result.success}")
            if result.sql_query:
                print(f"[DEBUG] 生成SQL: {result.sql_query}")
            if result.data:
                print(f"[DEBUG] 数据行数: {len(result.data)}")
            if result.analysis:
                print(f"[DEBUG] 分析完成: {len(result.analysis)} 字符")
            if result.chart_info:
                print(f"[DEBUG] 可视化: {result.chart_info.get('chart_type', 'none')}")
            
            if not result.success:
                print(f"[DEBUG] ❌ 查询失败: {result.error}")
                return "❌ 查询失败", result.error or "未知错误", "", None, ""
            
            # 构建返回结果
            status = "✅ 智能查询流程完成"
            
            # 添加流程摘要
            metadata = result.metadata or {}
            process_summary = []
            process_summary.append(f"📊 数据行数: {metadata.get('row_count', 0)}")
            process_summary.append(f"⏱️ 执行时间: {result.execution_time:.2f}秒")
            
            if metadata.get('visualization_suggestion'):
                viz_type = metadata['visualization_suggestion'].get('chart_type', 'none')
                process_summary.append(f"🎨 可视化建议: {viz_type}")
            
            status += f" ({', '.join(process_summary)})"
            
            # SQL查询
            if result.sql_query:
                sql_parts = ["### 🔧 生成的SQL查询\n"]
                sql_parts.append(f"```sql\n{result.sql_query}\n```")
                
                # 添加SQL分析信息
                if metadata.get('schema_tables_used'):
                    tables_used = metadata['schema_tables_used']
                    sql_parts.append(f"\n**涉及的表**: {', '.join(tables_used)}")
                
                sql_display = "\n".join(sql_parts)
            else:
                sql_display = "### ❌ SQL生成失败\n无法生成有效的SQL查询"
            
            # 数据结果
            data_display = ""
            chart_data = None
            
            if result.data:
                # 创建DataFrame用于显示
                df = pd.DataFrame(result.data)
                
                # 构建数据显示
                data_parts = ["### 📊 查询结果"]
                data_parts.append(f"**总行数**: {len(df)}")
                data_parts.append(f"**列数**: {len(df.columns)}")
                data_parts.append(f"**字段**: {', '.join(df.columns)}\n")
                
                # 限制显示行数并格式化数字
                display_df = df.head(20)
                
                # 格式化数字显示，避免科学计数法
                formatted_df = display_df.copy()
                for col in formatted_df.columns:
                    if formatted_df[col].dtype in ['int64', 'float64']:
                        # 对于数字列，格式化显示
                        formatted_df[col] = formatted_df[col].apply(self._format_number)
                
                data_parts.append("**数据预览**:")
                data_parts.append(formatted_df.to_markdown(index=False))
                
                if len(df) > 20:
                    data_parts.append(f"\n*仅显示前20行，总共{len(df)}行*")
                
                # 添加数据统计信息
                if len(df) > 0:
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        data_parts.append(f"\n**数值字段统计**:")
                        for col in numeric_cols[:3]:  # 最多显示3个数值字段的统计
                            stats = df[col].describe()
                            min_val = self._format_number(stats['min'])
                            max_val = self._format_number(stats['max'])
                            mean_val = self._format_number(stats['mean'])
                            data_parts.append(f"- **{col}**: 最小值={min_val}, 最大值={max_val}, 平均值={mean_val}")
                
                data_display = "\n".join(data_parts)
                
                # 准备图表数据
                chart_data = None
                if auto_viz and result.chart_info and result.chart_info.get('success'):
                    print(f"[DEBUG] 图表信息: {result.chart_info}")
                    chart_data = self._create_plotly_chart(df, result.chart_info)
                    print(f"[DEBUG] 图表创建结果: {chart_data is not None}")
                elif auto_viz and metadata.get('visualization_suggestion'):
                    # 如果chart_info不可用，尝试使用visualization_suggestion
                    print(f"[DEBUG] 使用可视化建议: {metadata['visualization_suggestion']}")
                    chart_data = self._create_chart_from_suggestion(df, metadata['visualization_suggestion'])
                    print(f"[DEBUG] 从建议创建图表结果: {chart_data is not None}")
                elif auto_viz and len(df.columns) >= 2:
                    # 如果没有建议，尝试创建默认图表
                    print(f"[DEBUG] 创建默认图表")
                    chart_data = self._create_default_chart(df)
                    print(f"[DEBUG] 默认图表创建结果: {chart_data is not None}")
            else:
                data_display = "### ⚠️ 无数据\n查询执行成功但未返回数据"
            
            # 分析结果
            analysis_display = ""
            if result.analysis:
                analysis_parts = ["### 🔍 智能数据分析"]
                analysis_parts.append(f"**分析级别**: {analysis_level}")
                analysis_parts.append("")
                analysis_parts.append(result.analysis)
                
                # 添加可视化建议信息
                if metadata.get('visualization_suggestion'):
                    viz_suggestion = metadata['visualization_suggestion']
                    analysis_parts.append("\n---")
                    analysis_parts.append("### 🎨 可视化建议")
                    analysis_parts.append(f"**推荐图表类型**: {viz_suggestion.get('chart_type', 'none')}")
                    
                    if viz_suggestion.get('reason'):
                        analysis_parts.append(f"**选择理由**: {viz_suggestion.get('reason')}")
                    
                    if auto_viz and result.chart_info:
                        if result.chart_info.get('success'):
                            analysis_parts.append("**状态**: ✅ 可视化已生成")
                        else:
                            analysis_parts.append(f"**状态**: ❌ 可视化生成失败 - {result.chart_info.get('error', '未知错误')}")
                    elif not auto_viz:
                        analysis_parts.append("**状态**: ⏸️ 自动可视化已关闭")
                
                analysis_display = "\n".join(analysis_parts)
            else:
                analysis_display = "### ℹ️ 无分析结果\n未执行数据分析或分析级别设置为'none'"
            
            # 保存查询结果用于反馈
            self.last_query_result = result
            
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
            x_col = chart_info.get('x_column') or chart_info.get('x_axis')
            y_col = chart_info.get('y_column') or chart_info.get('y_axis')
            
            print(f"[DEBUG] 图表参数: type={chart_type}, x={x_col}, y={y_col}, 可用列={list(df.columns)}")
            
            if not x_col or not y_col or x_col not in df.columns or y_col not in df.columns:
                # 尝试自动选择合适的列
                x_col, y_col = self._auto_select_columns(df)
                print(f"[DEBUG] 自动选择列: x={x_col}, y={y_col}")
            
            if not x_col or not y_col:
                print("[DEBUG] 无法确定绘图列")
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
            import traceback
            print(traceback.format_exc())
            return None
    
    def _auto_select_columns(self, df: pd.DataFrame) -> tuple[str, str]:
        """自动选择合适的列进行绘图"""
        try:
            columns = df.columns.tolist()
            
            # 查找数值列
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            # 查找非数值列（可能用作类别）
            categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()
            
            # 如果有数值列，选择第一个作为y轴
            y_col = numeric_cols[0] if numeric_cols else None
            
            # 选择x轴：优先选择非数值列，否则选择第一列
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
    
    def _create_chart_from_suggestion(self, df: pd.DataFrame, suggestion: Dict) -> Optional[go.Figure]:
        """根据可视化建议创建图表"""
        try:
            chart_type = suggestion.get('chart_type', 'bar')
            
            if chart_type == 'none':
                return None
            
            # 从建议中获取列名
            x_col = suggestion.get('x_axis') or suggestion.get('category')
            y_col = suggestion.get('y_axis') or suggestion.get('value')
            
            # 如果建议中没有指定列，自动选择
            if not x_col or not y_col:
                auto_x, auto_y = self._auto_select_columns(df)
                x_col = x_col or auto_x
                y_col = y_col or auto_y
            
            print(f"[DEBUG] 建议中的列: x_axis={suggestion.get('x_axis')}, y_axis={suggestion.get('y_axis')}")
            print(f"[DEBUG] 最终使用列: x={x_col}, y={y_col}")
            
            if not x_col or not y_col:
                return None
            
            # 创建图表配置，使用数据分析师建议的标题
            title = suggestion.get('title', f'{chart_type.title()}图表')
            
            chart_config = {
                'chart_type': chart_type,
                'title': title,
                'x_column': x_col,
                'y_column': y_col,
                'x_axis': x_col,  # 兼容不同的字段名
                'y_axis': y_col,
                'category': x_col,
                'value': y_col
            }
            
            return self._create_plotly_chart(df, chart_config)
            
        except Exception as e:
            print(f"从建议创建图表失败: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    

    
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
    
    def _create_default_chart(self, df: pd.DataFrame) -> Optional[go.Figure]:
        """创建默认图表"""
        try:
            # 自动选择列
            x_col, y_col = self._auto_select_columns(df)
            
            if not x_col or not y_col:
                return None
            
            # 根据数据类型选择图表类型
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()
            
            if categorical_cols and numeric_cols:
                chart_type = 'bar'
            elif len(numeric_cols) >= 2:
                chart_type = 'scatter'
            else:
                chart_type = 'bar'
            
            # 创建图表
            title = f"{y_col} vs {x_col}"
            
            if chart_type == 'bar':
                fig = px.bar(df, x=x_col, y=y_col, title=title)
            elif chart_type == 'scatter':
                fig = px.scatter(df, x=x_col, y=y_col, title=title)
            else:
                fig = px.bar(df, x=x_col, y=y_col, title=title)
            
            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            print(f"创建默认图表失败: {e}")
            return None
    
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
    
    def add_positive_feedback(self, description: str = "") -> str:
        """添加正面反馈到知识库"""
        if not self.last_query_result or not self.last_query_result.success:
            return "❌ 没有可反馈的查询结果"
        
        try:
            success = self.orchestrator.add_positive_feedback(
                question=self.last_query_result.question,
                sql=self.last_query_result.sql_query,
                description=description or "用户点赞的高质量查询"
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
            stats = self.orchestrator.get_knowledge_stats()
            
            if stats.get("enabled"):
                return f"""
### 📊 SQL知识库统计

- **总条目数**: {stats.get('total_items', 0)}
- **平均评分**: {stats.get('avg_rating', 0):.2f}
- **总使用次数**: {stats.get('total_usage', 0)}
- **高评分条目**: {stats.get('top_rated_count', 0)}
- **集合名称**: {stats.get('collection_name', 'N/A')}
- **状态**: ✅ 启用

### 💡 知识库说明
知识库通过收集用户反馈的高质量查询，使用RAG技术提升SQL生成的准确性和一致性。当您对查询结果满意时，请点击"👍 添加到知识库"按钮。
                """
            else:
                return f"""
### ❌ SQL知识库未启用

**原因**: {stats.get('reason', '未知原因')}

### 🔧 启用方法
1. 安装依赖: `pip install chromadb sentence-transformers`
2. 设置API密钥: 确保DASHSCOPE_API_KEY已配置
3. 重启应用
                """
        except Exception as e:
            return f"❌ 获取知识库统计失败: {str(e)}"
    
    def _format_number(self, value):
        """格式化数字显示，避免科学计数法"""
        try:
            if pd.isna(value):
                return "N/A"
            
            # 转换为数字
            num = float(value)
            
            # 如果是整数，直接显示为整数
            if num.is_integer():
                num = int(num)
                # 对大数字添加千分位分隔符
                if abs(num) >= 1000:
                    return f"{num:,}"
                else:
                    return str(num)
            
            # 对于小数
            # 如果数字很大或很小，但在合理范围内，避免科学计数法
            if abs(num) >= 1e6:
                # 大于百万的数字，显示为百万、千万、亿等
                if abs(num) >= 1e8:  # 亿
                    return f"{num/1e8:.2f}亿"
                elif abs(num) >= 1e4:  # 万
                    return f"{num/1e4:.2f}万"
                else:
                    return f"{num:,.2f}"
            elif abs(num) < 0.01 and abs(num) > 0:
                # 很小的小数，保留更多位数
                return f"{num:.6f}".rstrip('0').rstrip('.')
            else:
                # 正常范围的小数，保留2位
                return f"{num:.2f}".rstrip('0').rstrip('.')
                
        except (ValueError, TypeError):
            return str(value)

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
        
        # 反馈区域
        with gr.Row():
            with gr.Column(scale=3):
                feedback_info = gr.Markdown("执行查询后，如果结果满意，可以添加到知识库以改进AI性能")
            with gr.Column(scale=1):
                feedback_description = gr.Textbox(
                    label="反馈描述 (可选)",
                    placeholder="描述这个查询的用途...",
                    lines=1
                )
                like_btn = gr.Button("👍 添加到知识库", variant="secondary", size="sm")
        
        feedback_result = gr.Markdown("")
        
        with gr.Tabs():
            with gr.TabItem("SQL查询"):
                sql_display = gr.Markdown("等待查询...")
            
            with gr.TabItem("数据结果"):
                data_display = gr.Markdown("等待查询...")
            
            with gr.TabItem("数据可视化"):
                chart_display = gr.Plot(label="图表")
            
            with gr.TabItem("智能分析"):
                analysis_display = gr.Markdown("等待查询...")
            
            with gr.TabItem("📚 知识库"):
                with gr.Row():
                    refresh_stats_btn = gr.Button("刷新统计", size="sm")
                knowledge_stats = gr.Markdown("点击'刷新统计'查看知识库状态")
        
        # Schema信息面板
        with gr.Accordion("🗄️ 数据库Schema信息", open=False):
            with gr.Row():
                get_schema_btn = gr.Button("获取Schema信息")
                schema_status = gr.Textbox(label="获取状态", interactive=False)
            schema_display = gr.Markdown("点击'获取Schema信息'查看数据库结构")
        

        
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
        show_error=True,
        pwa=True
    ) 