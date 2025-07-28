"""
SQL修复智能体
专门分析SQL错误并提供修复建议
"""

import logging
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..config import config

logger = logging.getLogger(__name__)

class SQLFixerAgent(BaseAgent):
    """SQL修复智能体"""
    
    def __init__(self):
        system_prompt = """你是一个专业的SQL错误诊断和修复专家。你的任务是：

1. **错误分析**：
   - 分析SQL语法错误
   - 识别数据库兼容性问题
   - 检测字段名、表名错误
   - 分析逻辑错误

2. **修复策略**：
   - 提供具体的修复方案
   - 解释错误原因
   - 给出替代方案
   - 确保修复后的SQL语法正确

3. **输出格式**：
   返回JSON格式的结果：
   ```json
   {
     "error_type": "语法错误|字段错误|表名错误|逻辑错误|兼容性错误",
     "error_analysis": "详细的错误分析",
     "fixed_sql": "修复后的SQL语句",
     "explanation": "修复说明",
     "confidence": 0.9
   }
   ```

4. **修复规则**：
   - 保持原始查询意图
   - 优先使用标准SQL语法
   - 避免危险操作（DROP, DELETE, UPDATE等）
   - 确保只生成SELECT查询
   - 正确处理字段名和表名的引用

5. **常见错误处理**：
   - 字段名拼写错误：根据相似度匹配正确字段名
   - 表名错误：使用提供的Schema中的正确表名
   - 语法错误：修正SQL语法问题
   - 聚合函数错误：正确使用GROUP BY
   - JOIN错误：修正表连接语法

请始终返回有效的、可执行的SQL语句。"""

        super().__init__(
            name="SQL_Fixer_Agent",
            system_prompt=system_prompt,
            model_name=config.llm.coder_model  # 使用代码专用模型
        )
    
    def analyze_and_fix_sql(self, 
                          original_sql: str,
                          error_message: str,
                          schema_info: str,
                          original_question: str = "") -> Dict[str, Any]:
        """
        分析并修复SQL错误
        
        Args:
            original_sql: 原始SQL语句
            error_message: 错误信息
            schema_info: 数据库Schema信息
            original_question: 原始问题（可选）
            
        Returns:
            Dict[str, Any]: 修复结果
        """
        try:
            context = {
                "original_sql": original_sql,
                "error_message": error_message,
                "schema_info": schema_info,
                "original_question": original_question
            }
            
            # 构建修复请求
            fix_request = f"""
请分析并修复以下SQL错误：

**原始问题**：{original_question}

**错误的SQL**：
```sql
{original_sql}
```

**错误信息**：
{error_message}

**数据库Schema**：
{schema_info}

请根据错误信息和Schema信息，提供修复建议。确保修复后的SQL：
1. 语法正确
2. 字段名和表名存在于Schema中
3. 保持原始查询意图
4. 只生成SELECT语句

请返回JSON格式的修复结果。
            """
            
            response = self.run(fix_request, context)
            
            # 解析响应
            fixed_result = self._parse_fix_response(response)
            
            # 验证修复结果
            if fixed_result.get("fixed_sql"):
                validated_result = self._validate_fixed_sql(
                    fixed_result["fixed_sql"], 
                    schema_info
                )
                fixed_result.update(validated_result)
            
            return fixed_result
            
        except Exception as e:
            logger.error(f"SQL修复失败: {str(e)}")
            return {
                "error_type": "修复失败",
                "error_analysis": f"修复过程中出现错误: {str(e)}",
                "fixed_sql": None,
                "explanation": "无法完成SQL修复",
                "confidence": 0.0
            }
    
    def _parse_fix_response(self, response: str) -> Dict[str, Any]:
        """解析修复响应"""
        try:
            import json
            import re
            
            # 尝试从响应中提取JSON
            json_match = re.search(r'\{[^{}]*"error_type"[^{}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    result = json.loads(json_str)
                    return result
                except json.JSONDecodeError:
                    pass
            
            # 如果无法解析JSON，尝试从文本中提取信息
            result = {
                "error_type": "未知",
                "error_analysis": "",
                "fixed_sql": "",
                "explanation": "",
                "confidence": 0.5
            }
            
            # 提取修复后的SQL
            sql_match = re.search(r'```sql\n(.*?)\n```', response, re.DOTALL | re.IGNORECASE)
            if not sql_match:
                sql_match = re.search(r'```\n(.*?)\n```', response, re.DOTALL)
            
            if sql_match:
                result["fixed_sql"] = sql_match.group(1).strip()
            
            # 提取错误分析
            if "错误分析" in response or "error_analysis" in response:
                lines = response.split('\n')
                for i, line in enumerate(lines):
                    if "错误分析" in line or "error_analysis" in line:
                        if i + 1 < len(lines):
                            result["error_analysis"] = lines[i + 1].strip()
                        break
            
            result["explanation"] = response
            return result
            
        except Exception as e:
            logger.error(f"解析修复响应失败: {str(e)}")
            return {
                "error_type": "解析失败",
                "error_analysis": f"响应解析失败: {str(e)}",
                "fixed_sql": None,
                "explanation": response,
                "confidence": 0.0
            }
    
    def _validate_fixed_sql(self, fixed_sql: str, schema_info: str) -> Dict[str, Any]:
        """验证修复后的SQL"""
        validation = {
            "is_valid": True,
            "validation_errors": [],
            "warnings": []
        }
        
        try:
            # 基本语法检查
            if not fixed_sql.strip():
                validation["is_valid"] = False
                validation["validation_errors"].append("修复后的SQL为空")
                return validation
            
            # 检查是否为SELECT语句
            if not fixed_sql.strip().upper().startswith('SELECT'):
                validation["warnings"].append("建议只使用SELECT语句")
            
            # 检查危险关键词
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
            sql_upper = fixed_sql.upper()
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    validation["is_valid"] = False
                    validation["validation_errors"].append(f"包含危险关键词: {keyword}")
            
            # 简单的语法检查
            if sql_upper.count('(') != sql_upper.count(')'):
                validation["warnings"].append("括号不匹配")
            
            return validation
            
        except Exception as e:
            validation["is_valid"] = False
            validation["validation_errors"].append(f"验证过程出错: {str(e)}")
            return validation
    
    def suggest_query_improvements(self, sql: str, schema_info: str) -> Dict[str, Any]:
        """建议查询优化"""
        try:
            context = {
                "sql": sql,
                "schema_info": schema_info
            }
            
            optimization_request = f"""
请分析以下SQL查询并提供优化建议：

**SQL查询**：
```sql
{sql}
```

**数据库Schema**：
{schema_info}

请分析：
1. 性能优化机会
2. 索引使用建议
3. 查询重写建议
4. 潜在问题

返回JSON格式：
```json
{{
  "performance_score": 0.8,
  "optimizations": [
    {{"type": "索引建议", "description": "...", "impact": "高"}},
    {{"type": "查询重写", "description": "...", "impact": "中"}}
  ],
  "optimized_sql": "优化后的SQL",
  "explanation": "优化说明"
}}
```
            """
            
            response = self.run(optimization_request, context)
            return self._parse_optimization_response(response)
            
        except Exception as e:
            logger.error(f"查询优化建议失败: {str(e)}")
            return {
                "performance_score": 0.5,
                "optimizations": [],
                "optimized_sql": sql,
                "explanation": f"优化分析失败: {str(e)}"
            }
    
    def _parse_optimization_response(self, response: str) -> Dict[str, Any]:
        """解析优化建议响应"""
        try:
            import json
            import re
            
            # 尝试从响应中提取JSON
            json_match = re.search(r'\{[^{}]*"performance_score"[^{}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    result = json.loads(json_str)
                    return result
                except json.JSONDecodeError:
                    pass
            
            # 默认结果
            return {
                "performance_score": 0.5,
                "optimizations": [],
                "optimized_sql": "",
                "explanation": response
            }
            
        except Exception as e:
            logger.error(f"解析优化响应失败: {str(e)}")
            return {
                "performance_score": 0.5,
                "optimizations": [],
                "optimized_sql": "",
                "explanation": f"解析失败: {str(e)}"
            }
    
    def _build_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """构建提示"""
        return query

# 全局SQL修复智能体实例
_sql_fixer: Optional[SQLFixerAgent] = None

def get_sql_fixer() -> SQLFixerAgent:
    """获取全局SQL修复智能体实例"""
    global _sql_fixer
    
    if _sql_fixer is None:
        _sql_fixer = SQLFixerAgent()
    
    return _sql_fixer 