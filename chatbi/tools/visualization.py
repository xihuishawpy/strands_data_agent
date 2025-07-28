"""
数据可视化工具
支持生成各种类型的图表和可视化
"""

import os
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class ChartGenerator:
    """图表生成器基类"""
    
    def __init__(self, output_dir: str = "./data/charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_unique_filename(self, prefix: str = "chart", extension: str = "png") -> str:
        """生成唯一的文件名"""
        unique_id = uuid.uuid4().hex[:8]
        return f"{prefix}_{unique_id}.{extension}"
    
    def save_chart(self, fig, filename: str) -> str:
        """保存图表到文件"""
        file_path = self.output_dir / filename
        
        if hasattr(fig, 'write_html'):  # Plotly figure
            if filename.endswith('.png'):
                fig.write_image(str(file_path))
            else:
                fig.write_html(str(file_path))
        else:  # Matplotlib figure
            fig.savefig(str(file_path), dpi=300, bbox_inches='tight')
            plt.close(fig)
        
        logger.info(f"图表已保存: {file_path}")
        return str(file_path)

class DataVisualizer(ChartGenerator):
    """数据可视化器"""
    
    def __init__(self, output_dir: str = "./data/charts", use_plotly: bool = True):
        super().__init__(output_dir)
        self.use_plotly = use_plotly
    
    def create_chart(self, 
                    data: List[Dict[str, Any]], 
                    chart_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据配置创建图表
        
        Args:
            data: 数据列表
            chart_config: 图表配置
            
        Returns:
            Dict[str, Any]: 图表信息
        """
        try:
            if not data:
                return {"success": False, "error": "无数据可视化"}
            
            chart_type = chart_config.get("chart_type", "bar")
            title = chart_config.get("title", "数据图表")
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            if self.use_plotly:
                fig = self._create_plotly_chart(df, chart_config)
                filename = self.generate_unique_filename("chart", "html")
            else:
                fig = self._create_matplotlib_chart(df, chart_config)
                filename = self.generate_unique_filename("chart", "png")
            
            # 保存图表
            file_path = self.save_chart(fig, filename)
            
            return {
                "success": True,
                "chart_type": chart_type,
                "title": title,
                "file_path": file_path,
                "data_points": len(data)
            }
            
        except Exception as e:
            logger.error(f"图表创建失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_plotly_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """使用Plotly创建图表"""
        chart_type = config.get("chart_type", "bar")
        title = config.get("title", "数据图表")
        
        if chart_type == "bar":
            x_col = config.get("x_axis") or df.columns[0]
            y_col = config.get("y_axis") or df.columns[1]
            fig = px.bar(df, x=x_col, y=y_col, title=title)
            
        elif chart_type == "line":
            x_col = config.get("x_axis") or df.columns[0]
            y_col = config.get("y_axis") or df.columns[1]
            fig = px.line(df, x=x_col, y=y_col, title=title)
            
        elif chart_type == "pie":
            category_col = config.get("category") or df.columns[0]
            value_col = config.get("value") or df.columns[1]
            fig = px.pie(df, names=category_col, values=value_col, title=title)
            
        elif chart_type == "scatter":
            x_col = config.get("x_axis") or df.columns[0]
            y_col = config.get("y_axis") or df.columns[1]
            fig = px.scatter(df, x=x_col, y=y_col, title=title)
            
        elif chart_type == "histogram":
            x_col = config.get("x_axis") or df.columns[0]
            fig = px.histogram(df, x=x_col, title=title)
            
        else:
            # 默认为柱状图
            x_col = df.columns[0]
            y_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            fig = px.bar(df, x=x_col, y=y_col, title=title)
        
        # 设置布局
        fig.update_layout(
            font=dict(family="Arial, sans-serif", size=12),
            title_font_size=16,
            showlegend=True if chart_type == "pie" else False
        )
        
        return fig
    
    def _create_matplotlib_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> plt.Figure:
        """使用Matplotlib创建图表"""
        chart_type = config.get("chart_type", "bar")
        title = config.get("title", "数据图表")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == "bar":
            x_col = config.get("x_axis") or df.columns[0]
            y_col = config.get("y_axis") or df.columns[1]
            ax.bar(df[x_col], df[y_col])
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            
        elif chart_type == "line":
            x_col = config.get("x_axis") or df.columns[0]
            y_col = config.get("y_axis") or df.columns[1]
            ax.plot(df[x_col], df[y_col], marker='o')
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            
        elif chart_type == "pie":
            category_col = config.get("category") or df.columns[0]
            value_col = config.get("value") or df.columns[1]
            ax.pie(df[value_col], labels=df[category_col], autopct='%1.1f%%')
            
        elif chart_type == "scatter":
            x_col = config.get("x_axis") or df.columns[0]
            y_col = config.get("y_axis") or df.columns[1]
            ax.scatter(df[x_col], df[y_col])
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            
        elif chart_type == "histogram":
            x_col = config.get("x_axis") or df.columns[0]
            ax.hist(df[x_col], bins=20)
            ax.set_xlabel(x_col)
            ax.set_ylabel("频次")
            
        else:
            # 默认为柱状图
            x_col = df.columns[0]
            y_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            ax.bar(df[x_col], df[y_col])
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return fig
    
    def create_dashboard(self, 
                        charts_data: List[Dict[str, Any]], 
                        dashboard_title: str = "数据仪表板") -> Dict[str, Any]:
        """
        创建包含多个图表的仪表板
        
        Args:
            charts_data: 图表数据列表
            dashboard_title: 仪表板标题
            
        Returns:
            Dict[str, Any]: 仪表板信息
        """
        try:
            if self.use_plotly:
                return self._create_plotly_dashboard(charts_data, dashboard_title)
            else:
                return self._create_matplotlib_dashboard(charts_data, dashboard_title)
                
        except Exception as e:
            logger.error(f"仪表板创建失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_plotly_dashboard(self, charts_data: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
        """使用Plotly创建仪表板"""
        chart_count = len(charts_data)
        if chart_count == 0:
            return {"success": False, "error": "无图表数据"}
        
        # 计算子图布局
        cols = 2 if chart_count > 1 else 1
        rows = (chart_count + 1) // 2
        
        # 创建子图
        subplot_titles = [chart["title"] for chart in charts_data]
        fig = make_subplots(
            rows=rows, 
            cols=cols,
            subplot_titles=subplot_titles,
            specs=[[{"type": "xy"}] * cols for _ in range(rows)]
        )
        
        # 添加每个图表
        for i, chart_data in enumerate(charts_data):
            row = (i // cols) + 1
            col = (i % cols) + 1
            
            df = pd.DataFrame(chart_data["data"])
            config = chart_data["config"]
            
            # 根据类型添加图表
            if config.get("chart_type") == "bar":
                fig.add_trace(
                    go.Bar(x=df[config.get("x_axis", df.columns[0])], 
                          y=df[config.get("y_axis", df.columns[1])]),
                    row=row, col=col
                )
            elif config.get("chart_type") == "line":
                fig.add_trace(
                    go.Scatter(x=df[config.get("x_axis", df.columns[0])], 
                              y=df[config.get("y_axis", df.columns[1])], 
                              mode='lines+markers'),
                    row=row, col=col
                )
        
        fig.update_layout(
            title_text=title,
            showlegend=False,
            height=300 * rows
        )
        
        filename = self.generate_unique_filename("dashboard", "html")
        file_path = self.save_chart(fig, filename)
        
        return {
            "success": True,
            "title": title,
            "file_path": file_path,
            "chart_count": chart_count
        }
    
    def _create_matplotlib_dashboard(self, charts_data: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
        """使用Matplotlib创建仪表板"""
        chart_count = len(charts_data)
        if chart_count == 0:
            return {"success": False, "error": "无图表数据"}
        
        # 计算子图布局
        cols = 2 if chart_count > 1 else 1
        rows = (chart_count + 1) // 2
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 6 * rows))
        if chart_count == 1:
            axes = [axes]
        elif rows == 1:
            axes = [axes] if chart_count == 1 else axes
        else:
            axes = axes.flatten()
        
        # 创建每个子图
        for i, chart_data in enumerate(charts_data):
            ax = axes[i]
            df = pd.DataFrame(chart_data["data"])
            config = chart_data["config"]
            
            chart_type = config.get("chart_type", "bar")
            
            if chart_type == "bar":
                ax.bar(df[config.get("x_axis", df.columns[0])], 
                       df[config.get("y_axis", df.columns[1])])
            elif chart_type == "line":
                ax.plot(df[config.get("x_axis", df.columns[0])], 
                        df[config.get("y_axis", df.columns[1])], marker='o')
            
            ax.set_title(chart_data["title"])
            ax.tick_params(axis='x', rotation=45)
        
        # 隐藏多余的子图
        for i in range(chart_count, len(axes)):
            axes[i].set_visible(False)
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        filename = self.generate_unique_filename("dashboard", "png")
        file_path = self.save_chart(fig, filename)
        
        return {
            "success": True,
            "title": title,
            "file_path": file_path,
            "chart_count": chart_count
        }

# 全局可视化器实例
_visualizer: Optional[DataVisualizer] = None

def get_visualizer() -> DataVisualizer:
    """获取全局可视化器实例"""
    global _visualizer
    
    if _visualizer is None:
        _visualizer = DataVisualizer()
    
    return _visualizer

# 便捷函数
def create_chart(data: List[Dict[str, Any]], 
                chart_type: str = "bar", 
                title: str = "数据图表",
                **kwargs) -> Dict[str, Any]:
    """
    快速创建图表的便捷函数
    
    Args:
        data: 数据列表
        chart_type: 图表类型
        title: 图表标题
        **kwargs: 其他配置参数
        
    Returns:
        Dict[str, Any]: 图表信息
    """
    config = {
        "chart_type": chart_type,
        "title": title,
        **kwargs
    }
    
    visualizer = get_visualizer()
    return visualizer.create_chart(data, config) 