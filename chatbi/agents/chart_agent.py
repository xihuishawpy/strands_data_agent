"""
图表智能体
专门负责数据可视化的智能分析和图表生成
独立分析数据特征，智能推荐最适合的可视化方案
"""

import logging
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from .base import BaseAgent
from ..config import config

logger = logging.getLogger(__name__)

class ChartAgent(BaseAgent):
    """图表智能体"""
    
    def __init__(self, model_name: Optional[str] = None):
        # 使用标准模型进行图表分析
        model_name = model_name or config.llm.model_name
        
        system_prompt = """
你是一个专业的数据可视化专家，擅长根据数据特征智能推荐最适合的图表类型。

## 核心职责
1. **分析数据结构**：理解数据的字段类型、数量、分布特征
2. **智能推荐图表**：基于数据特征推荐最适合的可视化方案
3. **提供配置参数**：为图表生成提供详细的配置信息
4. **解释推荐理由**：说明为什么选择特定的图表类型

## 图表类型选择规则

### 柱状图 (bar)
- 适用场景：分类数据对比、排名展示
- 数据特征：1个分类字段 + 1个数值字段
- 数据量：适合20个以内的分类

### 折线图 (line)
- 适用场景：时间趋势分析、连续数据变化
- 数据特征：1个时间/序列字段 + 1个数值字段
- 数据量：适合展示趋势变化

### 饼图 (pie)
- 适用场景：部分与整体关系、占比分析
- 数据特征：1个分类字段 + 1个数值字段（代表占比）
- 数据量：适合10个以内的分类，且有明显的占比关系

### 散点图 (scatter)
- 适用场景：两个数值变量的相关性分析
- 数据特征：2个数值字段
- 数据量：适合中等到大量数据点

### 直方图 (histogram)
- 适用场景：数值分布分析、频率统计
- 数据特征：1个数值字段
- 数据量：适合大量数据的分布分析

### 热力图 (heatmap)
- 适用场景：矩阵数据、相关性分析
- 数据特征：多个数值字段或二维分类数据
- 数据量：适合矩阵形式的数据

## 输出格式
请以JSON格式返回推荐结果：
```json
{
    "chart_type": "图表类型",
    "title": "建议的图表标题",
    "x_axis": "X轴字段名",
    "y_axis": "Y轴字段名", 
    "category": "分类字段名（如适用）",
    "value": "数值字段名（如适用）",
    "reason": "选择此图表类型的理由",
    "confidence": 0.85
}
```

## 特殊情况处理
- 如果数据不适合可视化，返回 `{"chart_type": "none", "reason": "具体原因"}`
- 如果有多种合适的图表类型，选择最能突出数据特征的一种
- 考虑数据量大小，避免推荐不适合的图表类型

记住：你的目标是让数据的故事通过最合适的可视化方式清晰地传达给用户。
        """
        
        super().__init__(
            name="Chart_Agent",
            system_prompt=system_prompt,
            model_name=model_name
        )
    
    def analyze_and_recommend_chart(self, 
                                   data: List[Dict[str, Any]], 
                                   question: str = "",
                                   columns: List[str] = None) -> Dict[str, Any]:
        """
        分析数据并推荐图表类型
        
        Args:
            data: 查询结果数据
            question: 原始用户问题（可选，用于上下文）
            columns: 字段列表（可选）
            
        Returns:
            Dict[str, Any]: 图表推荐结果
        """
        try:
            if not data:
                return {"chart_type": "none", "reason": "无数据可视化"}
            
            # 数据预处理和分析
            df = pd.DataFrame(data)
            data_analysis = self._analyze_data_characteristics(df)
            
            # 构建分析提示
            analysis_prompt = self._build_analysis_prompt(data_analysis, question)
            
            # 调用LLM进行智能分析
            recommendation = self.run(analysis_prompt)
            
            # 解析LLM返回的JSON结果
            chart_config = self._parse_recommendation(recommendation, data_analysis)
            
            # 验证和优化推荐结果
            validated_config = self._validate_and_optimize_config(chart_config, data_analysis)
            
            logger.info(f"图表推荐完成: {validated_config.get('chart_type', 'none')}")
            return validated_config
            
        except Exception as e:
            logger.error(f"图表分析推荐失败: {str(e)}")
            return {"chart_type": "none", "reason": f"分析失败: {str(e)}"}
    
    def _analyze_data_characteristics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数据特征"""
        analysis = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "column_types": {},
            "numeric_columns": [],
            "categorical_columns": [],
            "datetime_columns": [],
            "data_sample": df.head(3).to_dict('records') if len(df) > 0 else []
        }
        
        # 分析每个字段的类型和特征
        for col in df.columns:
            col_analysis = self._analyze_column(df[col])
            analysis["column_types"][col] = col_analysis
            
            if col_analysis["type"] == "numeric":
                analysis["numeric_columns"].append(col)
            elif col_analysis["type"] == "datetime":
                analysis["datetime_columns"].append(col)
            else:
                analysis["categorical_columns"].append(col)
        
        # 数据分布特征
        analysis["has_time_series"] = len(analysis["datetime_columns"]) > 0
        analysis["has_categories"] = len(analysis["categorical_columns"]) > 0
        analysis["has_numeric"] = len(analysis["numeric_columns"]) > 0
        analysis["category_count"] = len(set(str(val) for val in df.iloc[:, 0])) if len(df) > 0 else 0
        
        return analysis
    
    def _analyze_column(self, series: pd.Series) -> Dict[str, Any]:
        """分析单个字段的特征"""
        col_info = {
            "type": "categorical",  # 默认为分类型
            "unique_count": series.nunique(),
            "null_count": series.isnull().sum(),
            "sample_values": series.dropna().head(5).tolist()
        }
        
        # 尝试判断数值类型
        try:
            numeric_series = pd.to_numeric(series, errors='coerce')
            if not numeric_series.isnull().all():
                non_null_ratio = (len(numeric_series) - numeric_series.isnull().sum()) / len(numeric_series)
                if non_null_ratio > 0.8:  # 80%以上可以转换为数值
                    col_info["type"] = "numeric"
                    col_info["min_value"] = float(numeric_series.min())
                    col_info["max_value"] = float(numeric_series.max())
                    col_info["mean_value"] = float(numeric_series.mean())
        except:
            pass
        
        # 尝试判断日期时间类型
        if col_info["type"] == "categorical":
            try:
                datetime_series = pd.to_datetime(series, errors='coerce')
                if not datetime_series.isnull().all():
                    non_null_ratio = (len(datetime_series) - datetime_series.isnull().sum()) / len(datetime_series)
                    if non_null_ratio > 0.8:  # 80%以上可以转换为日期
                        col_info["type"] = "datetime"
                        col_info["date_range"] = {
                            "start": str(datetime_series.min()),
                            "end": str(datetime_series.max())
                        }
            except:
                pass
        
        return col_info
    
    def _build_analysis_prompt(self, data_analysis: Dict[str, Any], question: str = "") -> str:
        """构建数据分析提示"""
        prompt_parts = []
        
        # 数据基本信息
        prompt_parts.append("## 数据基本信息")
        prompt_parts.append(f"- 数据行数: {data_analysis['row_count']}")
        prompt_parts.append(f"- 字段数量: {data_analysis['column_count']}")
        prompt_parts.append(f"- 字段列表: {', '.join(data_analysis['columns'])}")
        prompt_parts.append("")
        
        # 字段类型分析
        prompt_parts.append("## 字段类型分析")
        for col, col_info in data_analysis["column_types"].items():
            prompt_parts.append(f"**{col}**:")
            prompt_parts.append(f"  - 类型: {col_info['type']}")
            prompt_parts.append(f"  - 唯一值数量: {col_info['unique_count']}")
            
            if col_info["type"] == "numeric":
                prompt_parts.append(f"  - 数值范围: {col_info.get('min_value', 'N/A')} ~ {col_info.get('max_value', 'N/A')}")
                prompt_parts.append(f"  - 平均值: {col_info.get('mean_value', 'N/A')}")
            elif col_info["type"] == "datetime":
                date_range = col_info.get('date_range', {})
                prompt_parts.append(f"  - 时间范围: {date_range.get('start', 'N/A')} ~ {date_range.get('end', 'N/A')}")
            
            prompt_parts.append(f"  - 示例值: {col_info['sample_values'][:3]}")
            prompt_parts.append("")
        
        # 数据特征总结
        prompt_parts.append("## 数据特征总结")
        prompt_parts.append(f"- 数值字段: {data_analysis['numeric_columns']}")
        prompt_parts.append(f"- 分类字段: {data_analysis['categorical_columns']}")
        prompt_parts.append(f"- 时间字段: {data_analysis['datetime_columns']}")
        prompt_parts.append(f"- 是否有时间序列: {'是' if data_analysis['has_time_series'] else '否'}")
        prompt_parts.append(f"- 主要分类数量: {data_analysis['category_count']}")
        prompt_parts.append("")
        
        # 数据样例
        if data_analysis["data_sample"]:
            prompt_parts.append("## 数据样例")
            for i, sample in enumerate(data_analysis["data_sample"][:3]):
                prompt_parts.append(f"样例 {i+1}: {sample}")
            prompt_parts.append("")
        
        # 用户问题上下文
        if question:
            prompt_parts.append("## 用户问题上下文")
            prompt_parts.append(f"原始问题: {question}")
            prompt_parts.append("")
        
        # 分析要求
        prompt_parts.append("## 分析要求")
        prompt_parts.append("请基于以上数据特征，智能推荐最适合的图表类型。")
        prompt_parts.append("考虑因素：")
        prompt_parts.append("1. 数据的字段类型和数量")
        prompt_parts.append("2. 数据的分布特征")
        prompt_parts.append("3. 用户问题的意图（如果有）")
        prompt_parts.append("4. 图表的可读性和表达效果")
        prompt_parts.append("")
        prompt_parts.append("请返回JSON格式的推荐结果。")
        
        return "\n".join(prompt_parts)
    
    def _parse_recommendation(self, recommendation: str, data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """解析LLM推荐结果"""
        try:
            import json
            import re
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', recommendation, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 确保必要字段存在
                if "chart_type" not in result:
                    result["chart_type"] = "none"
                if "reason" not in result:
                    result["reason"] = "LLM推荐结果"
                
                return result
            else:
                # 如果没有找到JSON，尝试解析文本
                return self._parse_text_recommendation(recommendation, data_analysis)
                
        except Exception as e:
            logger.warning(f"解析LLM推荐结果失败: {str(e)}")
            # 回退到基于规则的推荐
            return self._rule_based_recommendation(data_analysis)
    
    def _parse_text_recommendation(self, text: str, data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """解析文本形式的推荐结果"""
        text_lower = text.lower()
        
        # 简单的关键词匹配
        if "柱状图" in text or "bar" in text_lower:
            chart_type = "bar"
        elif "折线图" in text or "line" in text_lower:
            chart_type = "line"
        elif "饼图" in text or "pie" in text_lower:
            chart_type = "pie"
        elif "散点图" in text or "scatter" in text_lower:
            chart_type = "scatter"
        elif "直方图" in text or "histogram" in text_lower:
            chart_type = "histogram"
        else:
            chart_type = "none"
        
        return {
            "chart_type": chart_type,
            "reason": "基于文本解析的推荐",
            "confidence": 0.6
        }
    
    def _rule_based_recommendation(self, data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """基于规则的图表推荐（回退方案）"""
        numeric_cols = data_analysis["numeric_columns"]
        categorical_cols = data_analysis["categorical_columns"]
        datetime_cols = data_analysis["datetime_columns"]
        row_count = data_analysis["row_count"]
        category_count = data_analysis["category_count"]
        
        # 规则1: 时间序列数据 -> 折线图
        if datetime_cols and numeric_cols:
            return {
                "chart_type": "line",
                "x_axis": datetime_cols[0],
                "y_axis": numeric_cols[0],
                "title": f"{numeric_cols[0]}随时间变化趋势",
                "reason": "检测到时间序列数据，适合用折线图展示趋势",
                "confidence": 0.9
            }
        
        # 规则2: 一个分类字段 + 一个数值字段，且分类数量适中 -> 柱状图
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1 and category_count <= 20:
            return {
                "chart_type": "bar",
                "x_axis": categorical_cols[0],
                "y_axis": numeric_cols[0],
                "title": f"{categorical_cols[0]}的{numeric_cols[0]}对比",
                "reason": "分类数据对比，适合用柱状图展示",
                "confidence": 0.8
            }
        
        # 规则3: 两个数值字段 -> 散点图
        if len(numeric_cols) >= 2:
            return {
                "chart_type": "scatter",
                "x_axis": numeric_cols[0],
                "y_axis": numeric_cols[1],
                "title": f"{numeric_cols[0]}与{numeric_cols[1]}的关系",
                "reason": "两个数值变量，适合用散点图分析相关性",
                "confidence": 0.7
            }
        
        # 规则4: 一个分类字段 + 一个数值字段，且分类数量较少，数值代表占比 -> 饼图
        if (len(categorical_cols) >= 1 and len(numeric_cols) >= 1 and 
            category_count <= 8 and row_count <= 10):
            return {
                "chart_type": "pie",
                "category": categorical_cols[0],
                "value": numeric_cols[0],
                "title": f"{categorical_cols[0]}的{numeric_cols[0]}分布",
                "reason": "少量分类的占比分析，适合用饼图展示",
                "confidence": 0.7
            }
        
        # 规则5: 单个数值字段，数据量较大 -> 直方图
        if len(numeric_cols) == 1 and row_count > 20:
            return {
                "chart_type": "histogram",
                "x_axis": numeric_cols[0],
                "title": f"{numeric_cols[0]}的分布情况",
                "reason": "单个数值变量的分布分析，适合用直方图",
                "confidence": 0.6
            }
        
        # 默认情况
        return {
            "chart_type": "none",
            "reason": "数据特征不明显，无法确定合适的图表类型",
            "confidence": 0.0
        }
    
    def _validate_and_optimize_config(self, config: Dict[str, Any], data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """验证和优化图表配置"""
        chart_type = config.get("chart_type", "none")
        
        if chart_type == "none":
            return config
        
        # 确保字段名有效
        available_columns = data_analysis["columns"]
        numeric_columns = data_analysis["numeric_columns"]
        categorical_columns = data_analysis["categorical_columns"]
        datetime_columns = data_analysis["datetime_columns"]
        
        # 根据图表类型验证和修正字段配置
        if chart_type == "bar":
            if not config.get("x_axis") or config["x_axis"] not in available_columns:
                config["x_axis"] = categorical_columns[0] if categorical_columns else available_columns[0]
            if not config.get("y_axis") or config["y_axis"] not in available_columns:
                config["y_axis"] = numeric_columns[0] if numeric_columns else available_columns[-1]
        
        elif chart_type == "line":
            if not config.get("x_axis") or config["x_axis"] not in available_columns:
                config["x_axis"] = datetime_columns[0] if datetime_columns else available_columns[0]
            if not config.get("y_axis") or config["y_axis"] not in available_columns:
                config["y_axis"] = numeric_columns[0] if numeric_columns else available_columns[-1]
        
        elif chart_type == "pie":
            if not config.get("category") or config["category"] not in available_columns:
                config["category"] = categorical_columns[0] if categorical_columns else available_columns[0]
            if not config.get("value") or config["value"] not in available_columns:
                config["value"] = numeric_columns[0] if numeric_columns else available_columns[-1]
        
        elif chart_type == "scatter":
            if not config.get("x_axis") or config["x_axis"] not in available_columns:
                config["x_axis"] = numeric_columns[0] if numeric_columns else available_columns[0]
            if not config.get("y_axis") or config["y_axis"] not in available_columns:
                config["y_axis"] = numeric_columns[1] if len(numeric_columns) > 1 else available_columns[-1]
        
        elif chart_type == "histogram":
            if not config.get("x_axis") or config["x_axis"] not in available_columns:
                config["x_axis"] = numeric_columns[0] if numeric_columns else available_columns[0]
        
        # 确保有标题
        if not config.get("title"):
            config["title"] = f"数据{chart_type}图表"
        
        # 确保有置信度
        if "confidence" not in config:
            config["confidence"] = 0.7
        
        return config
    
    def _build_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        构建图表分析提示（实现基类抽象方法）
        
        Args:
            query: 分析提示内容
            context: 上下文信息（可选）
            
        Returns:
            str: 完整的提示
        """
        # 对于图表智能体，query就是完整的分析提示
        return query

# 全局图表智能体实例
_chart_agent: Optional[ChartAgent] = None

def get_chart_agent() -> ChartAgent:
    """获取全局图表智能体实例"""
    global _chart_agent
    
    if _chart_agent is None:
        _chart_agent = ChartAgent()
    
    return _chart_agent