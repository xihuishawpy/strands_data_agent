"""
SQL生成智能体
专门负责将自然语言转换为SQL查询
"""

import logging
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..config import config

logger = logging.getLogger(__name__)

class SQLGeneratorAgent(BaseAgent):
    """SQL生成智能体"""
    
    def __init__(self, model_name: Optional[str] = None):
        # 根据内存使用qwen-coder-plus处理代码相关任务
        model_name = model_name or config.llm.coder_model
        
        system_prompt = """
你是一个世界级的数据库专家和SQL查询生成专家。你的职责是将用户的自然语言问题转换成准确、高效的SQL查询语句。

## 核心规则
1. **只输出SQL查询语句**，不要包含任何解释、注释或其他文字
2. **只允许SELECT查询**，绝对不能包含INSERT、UPDATE、DELETE、DROP等危险操作
3. **基于提供的数据库Schema**来构建查询，确保表名和字段名准确
4. **使用标准SQL语法**，兼容PostgreSQL、MySQL
5. 如果无法根据Schema生成合适的查询，输出: `ERROR_CANNOT_GENERATE`

## SQL最佳实践
- 使用适当的JOIN来连接相关表
- 添加WHERE条件进行数据过滤
- 使用GROUP BY进行数据聚合
- 添加ORDER BY进行排序
- 使用LIMIT限制结果数量（如果需要）
- 使用别名提高可读性
- 优先使用EXISTS而不是IN进行子查询

## 时间处理
- 对于"今天"、"昨天"，使用CURRENT_DATE
- 对于"本月"，使用DATE_TRUNC('month', CURRENT_DATE)  
- 对于"上个月"，使用DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
- 对于"今年"，使用DATE_TRUNC('year', CURRENT_DATE)

## 聚合查询
- 计数：COUNT(*)或COUNT(column_name)
- 求和：SUM(column_name)
- 平均值：AVG(column_name)
- 最大值：MAX(column_name)
- 最小值：MIN(column_name)

## 错误处理
如果遇到以下情况，返回 `ERROR_CANNOT_GENERATE`：
- Schema信息不足
- 用户问题与现有表结构不匹配
- 问题过于模糊无法准确理解
- 需要执行非SELECT操作

记住：安全第一，准确第二，效率第三。
        """
        
        super().__init__(
            name="SQL_Generator_Agent",
            system_prompt=system_prompt,
            model_name=model_name
        )
    
    def _build_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """构建SQL生成提示"""
        prompt_parts = []
        
        # 添加数据库Schema信息
        if context and "schema" in context:
            prompt_parts.append("数据库Schema信息:")
            prompt_parts.append(context["schema"])
            prompt_parts.append("")
        
        # 添加示例SQL（如果有）
        if context and "examples" in context:
            prompt_parts.append("参考SQL示例:")
            for example in context["examples"]:
                prompt_parts.append(f"问题: {example['question']}")
                prompt_parts.append(f"SQL: {example['sql']}")
                prompt_parts.append("")
        
        # 添加用户问题
        prompt_parts.append(f"用户问题: {query}")
        prompt_parts.append("")
        prompt_parts.append("请生成对应的SQL查询语句:")
        
        return "\n".join(prompt_parts)
    
    def generate_sql(self, 
                    question: str, 
                    schema_info: str, 
                    examples: Optional[List[Dict[str, str]]] = None,
                    table_names: Optional[List[str]] = None) -> str:
        """
        生成SQL查询
        
        Args:
            question: 自然语言问题
            schema_info: 数据库Schema信息
            examples: SQL示例
            table_names: 相关表名列表
            
        Returns:
            str: 生成的SQL查询或错误信息
        """
        # 验证输入
        is_valid, error_msg = self.validate_input(question)
        if not is_valid:
            return f"ERROR_INVALID_INPUT: {error_msg}"
        
        # 构建上下文
        context = {
            "schema": schema_info
        }
        
        if examples:
            context["examples"] = examples
        
        if table_names:
            context["relevant_tables"] = table_names
        
        try:
            # 生成SQL
            sql_response = self.run(question, context)
            
            # 清理响应（移除可能的解释文字）
            sql_response = sql_response.strip()
            
            # 检查是否为错误响应
            if sql_response.startswith("ERROR"):
                return sql_response
            
            # 提取SQL语句
            sql_query = self._extract_sql(sql_response)
            
            if not sql_query:
                return "ERROR_NO_SQL_GENERATED"
            
            logger.info(f"生成SQL成功: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"SQL生成失败: {str(e)}")
            return f"ERROR_GENERATION_FAILED: {str(e)}"
    
    def _extract_sql(self, response: str) -> str:
        """从响应中提取SQL语句"""
        response = response.strip()
        
        # 如果整个响应就是SQL语句
        if response.upper().startswith('SELECT'):
            return response
        
        # 尝试从代码块中提取
        import re
        
        # 查找```sql代码块
        sql_block_pattern = r'```sql\s*(.*?)\s*```'
        sql_match = re.search(sql_block_pattern, response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        # 查找```代码块
        code_block_pattern = r'```\s*(.*?)\s*```'
        code_match = re.search(code_block_pattern, response, re.DOTALL)
        if code_match:
            code_content = code_match.group(1).strip()
            if code_content.upper().startswith('SELECT'):
                return code_content
        
        # 查找以SELECT开头的行
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.upper().startswith('SELECT'):
                # 可能是多行SQL，尝试收集完整语句
                sql_lines = [line]
                start_idx = lines.index(line) + 1
                
                for next_line in lines[start_idx:]:
                    next_line = next_line.strip()
                    if not next_line:
                        break
                    if next_line.startswith('#') or next_line.startswith('--'):
                        break
                    sql_lines.append(next_line)
                
                return ' '.join(sql_lines)
        
        return ""
    
    def validate_sql_safety(self, sql: str) -> tuple[bool, str]:
        """验证SQL安全性"""
        sql_upper = sql.upper().strip()
        
        # 检查危险关键词
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'TRUNCATE', 'ALTER',
            'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"包含危险关键词: {keyword}"
        
        # 检查是否以SELECT开头
        if not sql_upper.startswith('SELECT'):
            return False, "必须是SELECT查询"
        
        return True, ""

# 全局SQL生成器实例
_sql_generator: Optional[SQLGeneratorAgent] = None

def get_sql_generator() -> SQLGeneratorAgent:
    """获取全局SQL生成器实例"""
    global _sql_generator
    
    if _sql_generator is None:
        _sql_generator = SQLGeneratorAgent()
    
    return _sql_generator 