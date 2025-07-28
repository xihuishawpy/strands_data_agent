"""
数据分析智能体
专门负责分析和解释查询结果数据
"""

import logging
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..config import config

logger = logging.getLogger(__name__)

class DataAnalystAgent(BaseAgent):
    """数据分析智能体"""
    
    def __init__(self, model_name: Optional[str] = None):
        # 根据内存使用qwen-max作为默认QA模型
        model_name = model_name or config.llm.model_name
        
        system_prompt = """
你是一位经验丰富的数据分析师，擅长从数据中发现洞察并用通俗易懂的语言解释数据含义。

## 核心职责
1. **数据解读**: 分析查询结果，识别关键趋势、模式和异常
2. **洞察发现**: 从数据中挖掘有价值的商业洞察
3. **通俗解释**: 用中文和非技术语言解释数据含义
4. **建议提供**: 基于数据分析结果提供实用建议

## 分析原则
- **客观性**: 基于数据事实，避免主观臆断
- **准确性**: 确保数据理解和计算正确
- **完整性**: 全面分析数据的各个维度
- **可操作性**: 提供具体可行的建议

## 分析维度
1. **基础统计**: 总数、平均值、最大值、最小值等
2. **趋势分析**: 时间序列变化、增长趋势
3. **分布分析**: 数据分布特征、异常值识别
4. **对比分析**: 不同类别、时间段的对比
5. **关联分析**: 变量间的相关性

## 输出格式
使用以下结构化格式输出分析结果：

### 📊 数据概览
[简要描述数据集的基本情况]

### 🔍 关键发现
[列出3-5个最重要的发现]

### 📈 趋势洞察
[描述数据中的趋势和模式]

### ⚠️ 注意事项
[指出需要关注的异常或问题]

### 💡 建议行动
[基于分析结果的具体建议]

## 可视化建议
基于数据特征推荐最适合的图表类型：
- 时间趋势 → 折线图
- 分类对比 → 柱状图
- 占比关系 → 饼图
- 分布情况 → 直方图
- 相关关系 → 散点图

记住：让数据说话，让洞察有用。
        """
        
        super().__init__(
            name="Data_Analyst_Agent", 
            system_prompt=system_prompt,
            model_name=model_name
        )
    
    def _build_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """构建数据分析提示"""
        prompt_parts = []
        
        # 添加原始问题
        if context and "original_question" in context:
            prompt_parts.append(f"原始问题: {context['original_question']}")
            prompt_parts.append("")
        
        # 添加SQL查询（可选）
        if context and "sql_query" in context:
            prompt_parts.append(f"执行的SQL: {context['sql_query']}")
            prompt_parts.append("")
        
        # 添加数据结果
        if context and "query_result" in context:
            result = context["query_result"]
            prompt_parts.append("查询结果数据:")
            
            if isinstance(result, dict) and "data" in result:
                data = result["data"]
                if data:
                    # 显示数据结构
                    if isinstance(data, list) and len(data) > 0:
                        prompt_parts.append(f"数据行数: {len(data)}")
                        prompt_parts.append(f"字段: {list(data[0].keys())}")
                        prompt_parts.append("")
                        
                        # 显示前几行数据
                        prompt_parts.append("数据示例:")
                        for i, row in enumerate(data[:5]):  # 只显示前5行
                            prompt_parts.append(f"第{i+1}行: {row}")
                        
                        if len(data) > 5:
                            prompt_parts.append(f"... (共{len(data)}行数据)")
                    else:
                        prompt_parts.append("无数据返回")
                else:
                    prompt_parts.append("查询结果为空")
            else:
                prompt_parts.append(str(result))
            
            prompt_parts.append("")
        
        # 添加数据类型信息（如果有）
        if context and "data_types" in context:
            prompt_parts.append(f"数据类型信息: {context['data_types']}")
            prompt_parts.append("")
        
        # 添加分析要求
        prompt_parts.append("分析要求:")
        prompt_parts.append(query)
        prompt_parts.append("")
        prompt_parts.append("请对以上数据进行深入分析，并提供有价值的洞察和建议。")
        
        return "\n".join(prompt_parts)
    
    def analyze_data(self, 
                    query_result: Dict[str, Any],
                    original_question: str,
                    sql_query: Optional[str] = None,
                    analysis_requirements: Optional[str] = None) -> str:
        """
        分析查询结果数据
        
        Args:
            query_result: SQL查询结果
            original_question: 原始用户问题
            sql_query: 执行的SQL查询
            analysis_requirements: 特定分析要求
            
        Returns:
            str: 数据分析报告
        """
        try:
            # 构建上下文
            context = {
                "query_result": query_result,
                "original_question": original_question
            }
            
            if sql_query:
                context["sql_query"] = sql_query
            
            # 分析数据类型和结构
            data_info = self._analyze_data_structure(query_result)
            if data_info:
                context["data_types"] = data_info
            
            # 生成分析要求
            if not analysis_requirements:
                analysis_requirements = "请全面分析这些数据，提供关键洞察和实用建议"
            
            # 执行分析
            analysis_result = self.run(analysis_requirements, context)
            
            logger.info("数据分析完成")
            return analysis_result
            
        except Exception as e:
            logger.error(f"数据分析失败: {str(e)}")
            return f"数据分析过程中出现错误: {str(e)}"
    
    def suggest_visualization(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据数据特征建议可视化方案
        
        Args:
            query_result: 查询结果数据
            
        Returns:
            Dict[str, Any]: 可视化建议
        """
        try:
            if not query_result.get("data"):
                return {"chart_type": "none", "reason": "无数据可视化"}
            
            data = query_result["data"]
            if not data:
                return {"chart_type": "none", "reason": "数据为空"}
            
            # 分析数据结构
            columns = list(data[0].keys())
            row_count = len(data)
            
            # 分析字段类型
            numeric_cols = []
            text_cols = []
            date_cols = []
            
            for col in columns:
                sample_values = [row[col] for row in data[:10] if row[col] is not None]
                if not sample_values:
                    continue
                
                col_type = self._infer_column_type(sample_values)
                if col_type == "numeric":
                    numeric_cols.append(col)
                elif col_type == "date":
                    date_cols.append(col)
                else:
                    text_cols.append(col)
            
            # 推荐图表类型
            chart_recommendation = self._recommend_chart_type(
                numeric_cols, text_cols, date_cols, row_count
            )
            
            return chart_recommendation
            
        except Exception as e:
            logger.error(f"可视化建议生成失败: {str(e)}")
            return {"chart_type": "none", "reason": f"分析失败: {str(e)}"}
    
    def _analyze_data_structure(self, query_result: Dict[str, Any]) -> Optional[str]:
        """分析数据结构"""
        try:
            if not query_result.get("data"):
                return None
            
            data = query_result["data"]
            if not data:
                return "空数据集"
            
            columns = list(data[0].keys())
            analysis = []
            
            for col in columns:
                # 获取非空值样本
                sample_values = [row[col] for row in data[:20] if row[col] is not None]
                if not sample_values:
                    analysis.append(f"{col}: 全部为空值")
                    continue
                
                col_type = self._infer_column_type(sample_values)
                unique_count = len(set(str(v) for v in sample_values))
                analysis.append(f"{col}: {col_type}, 唯一值数: {unique_count}")
            
            return "; ".join(analysis)
            
        except Exception:
            return None
    
    def _infer_column_type(self, values: List[Any]) -> str:
        """推断列的数据类型"""
        if not values:
            return "unknown"
        
        # 检查是否为数值类型
        numeric_count = 0
        for value in values:
            try:
                float(value)
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        
        if numeric_count / len(values) > 0.8:
            return "numeric"
        
        # 检查是否为日期类型
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
        ]
        
        import re
        date_count = 0
        for value in values:
            value_str = str(value)
            for pattern in date_patterns:
                if re.match(pattern, value_str):
                    date_count += 1
                    break
        
        if date_count / len(values) > 0.8:
            return "date"
        
        return "text"
    
    def _recommend_chart_type(self, 
                             numeric_cols: List[str], 
                             text_cols: List[str], 
                             date_cols: List[str], 
                             row_count: int) -> Dict[str, Any]:
        """根据数据特征推荐图表类型"""
        
        # 时间序列数据
        if date_cols and numeric_cols:
            return {
                "chart_type": "line",
                "reason": "包含时间和数值字段，适合趋势分析",
                "x_axis": date_cols[0],
                "y_axis": numeric_cols[0],
                "title": f"{numeric_cols[0]}随时间的变化趋势"
            }
        
        # 分类数据 + 数值数据
        if text_cols and numeric_cols and row_count <= 20:
            return {
                "chart_type": "bar",
                "reason": "分类数据配合数值数据，适合对比分析",
                "x_axis": text_cols[0],
                "y_axis": numeric_cols[0],
                "title": f"不同{text_cols[0]}的{numeric_cols[0]}对比"
            }
        
        # 占比数据（只有一个文本字段和一个数值字段）
        if len(text_cols) == 1 and len(numeric_cols) == 1 and row_count <= 10:
            return {
                "chart_type": "pie",
                "reason": "适合展示占比关系",
                "category": text_cols[0],
                "value": numeric_cols[0],
                "title": f"{text_cols[0]}的{numeric_cols[0]}分布"
            }
        
        # 多数值字段
        if len(numeric_cols) >= 2:
            return {
                "chart_type": "scatter",
                "reason": "多个数值字段，适合相关性分析",
                "x_axis": numeric_cols[0],
                "y_axis": numeric_cols[1],
                "title": f"{numeric_cols[0]}与{numeric_cols[1]}的关系"
            }
        
        # 默认表格
        return {
            "chart_type": "table",
            "reason": "数据结构复杂或数据量大，适合表格展示",
            "title": "数据详情"
        }

# 全局数据分析师实例
_data_analyst: Optional[DataAnalystAgent] = None

def get_data_analyst() -> DataAnalystAgent:
    """获取全局数据分析师实例"""
    global _data_analyst
    
    if _data_analyst is None:
        _data_analyst = DataAnalystAgent()
    
    return _data_analyst 