"""
SQL生成智能体
专门负责将自然语言转换为SQL查询
集成RAG知识库功能
"""

import logging
import re
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..config import config
from ..knowledge_base.sql_knowledge_manager import get_knowledge_manager

logger = logging.getLogger(__name__)

class SQLGeneratorAgent(BaseAgent):
    """SQL生成智能体"""
    
    def __init__(self, model_name: Optional[str] = None):
        # 根据内存使用qwen-coder-plus处理代码相关任务
        model_name = model_name or config.llm.coder_model
        
        # 初始化知识库管理器
        self.knowledge_manager = get_knowledge_manager()
        
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
    
    def generate_sql_with_rag(self, 
                             question: str, 
                             schema_info: str,
                             rag_result: Optional[Any] = None,
                             table_names: Optional[List[str]] = None) -> str:
        """
        使用RAG增强的SQL生成
        
        Args:
            question: 自然语言问题
            schema_info: 数据库Schema信息
            rag_result: RAG检索结果
            table_names: 相关表名列表
            
        Returns:
            str: 生成的SQL查询或错误信息
        """
        # 验证输入
        is_valid, error_msg = self.validate_input(question)
        if not is_valid:
            return f"ERROR_INVALID_INPUT: {error_msg}"
        
        # 如果没有提供RAG结果，进行搜索
        if rag_result is None and self.knowledge_manager.enabled:
            rag_result = self.knowledge_manager.search_knowledge(question)
        
        # RAG策略处理
        if rag_result and rag_result.found_match:
            if rag_result.should_use_cached:
                # 策略1：高相似度 - 直接使用缓存的SQL
                cached_sql = rag_result.best_match["sql"]
                logger.info(f"🎯 RAG策略1-高相似度: 直接使用缓存SQL (相似度: {rag_result.confidence:.3f})")
                
                # 验证缓存SQL的质量
                is_valid_sql, validation_error = self.validate_sql_quality(cached_sql)
                if not is_valid_sql:
                    logger.warning(f"缓存SQL质量验证失败: {validation_error}，转为辅助生成模式")
                    # 降级为辅助生成模式
                    rag_result.should_use_cached = False
                else:
                    # 更新使用统计
                    if hasattr(self.knowledge_manager, 'update_usage_feedback'):
                        self.knowledge_manager.update_usage_feedback(question, cached_sql, 0.1)
                    return cached_sql
        
        # 构建RAG增强的提示词
        rag_prompt = self.build_rag_prompt(question, schema_info, rag_result, table_names)
        
        try:
            # 使用增强提示词生成SQL
            sql_response = self.run(rag_prompt)
            
            # 清理响应
            sql_response = sql_response.strip()
            
            # 检查是否为错误响应
            if sql_response.startswith("ERROR"):
                return sql_response
            
            # 提取SQL语句
            sql_query = self._extract_sql(sql_response)
            
            if not sql_query:
                return "ERROR_NO_SQL_GENERATED"
            
            # 验证生成SQL的质量
            is_valid_sql, validation_error = self.validate_sql_quality(sql_query)
            if not is_valid_sql:
                logger.warning(f"生成SQL质量验证失败: {validation_error}")
                return f"ERROR_SQL_VALIDATION_FAILED: {validation_error}"
            
            logger.info(f"RAG增强SQL生成成功: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"RAG增强SQL生成失败: {str(e)}")
            return f"ERROR_GENERATION_FAILED: {str(e)}"
    
    def build_rag_prompt(self, 
                        question: str, 
                        schema_info: str,
                        rag_result: Optional[Any] = None,
                        table_names: Optional[List[str]] = None,
                        max_prompt_length: int = 8000) -> str:
        """
        构建RAG增强的提示词，将相似示例整合到生成提示词中
        
        Args:
            question: 用户问题
            schema_info: 数据库Schema信息
            rag_result: RAG检索结果
            table_names: 相关表名列表
            max_prompt_length: 最大提示词长度限制
            
        Returns:
            str: 构建的提示词
        """
        prompt_parts = []
        
        # 添加数据库Schema信息
        prompt_parts.append("数据库Schema信息:")
        prompt_parts.append(schema_info)
        prompt_parts.append("")
        
        # 添加相关表名（如果有）
        if table_names:
            prompt_parts.append("相关表名:")
            prompt_parts.append(", ".join(table_names))
            prompt_parts.append("")
        
        # 智能选择和添加RAG检索到的相似示例
        if rag_result and rag_result.found_match and rag_result.similar_examples:
            # 使用智能示例选择算法
            selected_examples = self._select_optimal_examples(
                question, rag_result.similar_examples, max_examples=3
            )
            
            if selected_examples:
                prompt_parts.append("参考相似查询示例:")
                
                for i, example in enumerate(selected_examples):
                    example_parts = []
                    example_parts.append(f"示例 {i+1}:")
                    example_parts.append(f"问题: {example['question']}")
                    example_parts.append(f"SQL: {example['sql']}")
                    
                    # 添加相似度信息
                    if 'similarity' in example:
                        example_parts.append(f"相似度: {example['similarity']:.3f}")
                    
                    # 添加描述信息（如果有且不太长）
                    if example.get('description') and len(example['description']) < 200:
                        example_parts.append(f"说明: {example['description']}")
                    
                    example_parts.append("")
                    
                    # 检查添加这个示例后是否会超出长度限制
                    example_text = "\n".join(example_parts)
                    current_prompt = "\n".join(prompt_parts)
                    
                    if len(current_prompt + example_text) > max_prompt_length * 0.8:  # 预留20%空间
                        logger.info(f"达到提示词长度限制，停止添加示例（已添加{i}个）")
                        break
                    
                    prompt_parts.extend(example_parts)
                
                # 添加策略说明
                strategy = rag_result.strategy if hasattr(rag_result, 'strategy') else "unknown"
                if strategy == "medium_similarity_assisted":
                    prompt_parts.append("💡 提示: 以上示例与当前问题有一定相似性，请参考其查询思路和SQL结构。")
                elif strategy == "low_similarity_normal":
                    prompt_parts.append("💡 提示: 以上示例仅供参考，请根据具体问题独立构建查询。")
                
                prompt_parts.append("")
        
        # 添加用户问题
        prompt_parts.append(f"用户问题: {question}")
        prompt_parts.append("")
        
        # 添加生成指导
        prompt_parts.append("请基于以上信息生成准确的SQL查询语句。")
        prompt_parts.append("要求:")
        prompt_parts.append("1. 只输出SQL语句，不要包含解释")
        prompt_parts.append("2. 确保语法正确且符合安全要求")
        prompt_parts.append("3. 优先使用提供的Schema信息")
        if rag_result and rag_result.similar_examples:
            prompt_parts.append("4. 可以参考相似示例的查询思路，但要根据具体问题调整")
        
        # 构建最终提示词并检查长度
        final_prompt = "\n".join(prompt_parts)
        
        # 如果超出长度限制，进行智能截断
        if len(final_prompt) > max_prompt_length:
            final_prompt = self._truncate_prompt_intelligently(final_prompt, max_prompt_length)
            logger.warning(f"提示词超出长度限制，已智能截断至 {len(final_prompt)} 字符")
        
        return final_prompt
    
    def _select_optimal_examples(self, 
                               question: str, 
                               examples: List[Dict[str, Any]], 
                               max_examples: int = 3) -> List[Dict[str, Any]]:
        """
        实现智能示例选择算法，选择最相关的历史查询作为示例
        
        优化策略:
        1. 多维度评分：相似度、历史评分、使用频率、复杂度匹配、时效性
        2. 多样性过滤：避免选择过于相似的示例
        3. 长度控制：优先选择适中长度的示例
        4. 质量保证：过滤掉低质量示例
        
        Args:
            question: 用户问题
            examples: 候选示例列表
            max_examples: 最大示例数量
            
        Returns:
            List[Dict]: 选择的最优示例
        """
        if not examples:
            return []
        
        # 预过滤：移除明显低质量的示例
        filtered_examples = self._pre_filter_examples(examples)
        
        if not filtered_examples:
            logger.warning("所有示例都被预过滤器移除")
            return []
        
        # 为每个示例计算综合评分
        scored_examples = []
        
        for example in filtered_examples:
            score = self._calculate_example_score(question, example)
            scored_examples.append({
                **example,
                'selection_score': score
            })
        
        # 按评分排序
        scored_examples.sort(key=lambda x: x['selection_score'], reverse=True)
        
        # 应用多样性过滤，避免选择过于相似的示例
        selected_examples = self._apply_diversity_filter(
            scored_examples, max_examples
        )
        
        # 最终质量检查和排序优化
        final_examples = self._finalize_example_selection(selected_examples, question)
        
        logger.info(f"从 {len(examples)} 个候选示例中选择了 {len(final_examples)} 个最优示例")
        
        return final_examples
    
    def _pre_filter_examples(self, examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        预过滤示例，移除明显低质量的示例
        
        Args:
            examples: 原始示例列表
            
        Returns:
            List[Dict]: 过滤后的示例列表
        """
        filtered = []
        
        for example in examples:
            # 检查必要字段
            if not example.get('question') or not example.get('sql'):
                continue
            
            # 检查SQL基本质量
            sql = example.get('sql', '').strip()
            if len(sql) < 10 or not sql.upper().startswith('SELECT'):
                continue
            
            # 检查问题长度合理性
            question = example.get('question', '').strip()
            if len(question) < 3 or len(question) > 500:
                continue
            
            # 检查相似度阈值
            similarity = example.get('similarity', 0.0)
            if similarity < 0.3:  # 过低的相似度示例没有参考价值
                continue
            
            # 检查评分（如果有）
            rating = example.get('rating', 0.0)
            if rating < -1.0:  # 过低评分的示例可能有问题
                continue
            
            filtered.append(example)
        
        logger.debug(f"预过滤：从 {len(examples)} 个示例中保留了 {len(filtered)} 个")
        return filtered
    
    def _finalize_example_selection(self, 
                                  examples: List[Dict[str, Any]], 
                                  question: str) -> List[Dict[str, Any]]:
        """
        最终优化示例选择，确保最佳的示例组合
        
        Args:
            examples: 已选择的示例列表
            question: 用户问题
            
        Returns:
            List[Dict]: 最终优化的示例列表
        """
        if not examples:
            return []
        
        # 按复杂度和相关性重新排序
        def sort_key(example):
            # 优先考虑高相似度
            similarity = example.get('similarity', 0.0)
            # 其次考虑综合评分
            score = example.get('selection_score', 0.0)
            # 最后考虑SQL长度适中性
            sql_length = len(example.get('sql', ''))
            length_penalty = abs(sql_length - 100) / 1000.0  # 偏好100字符左右的SQL
            
            return similarity * 0.5 + score * 0.4 - length_penalty * 0.1
        
        examples.sort(key=sort_key, reverse=True)
        
        # 确保示例质量
        quality_examples = []
        for example in examples:
            # 最终SQL质量检查
            sql = example.get('sql', '')
            is_valid, _ = self.validate_sql_quality(sql)
            if is_valid:
                quality_examples.append(example)
        
        return quality_examples
    
    def _calculate_example_score(self, question: str, example: Dict[str, Any]) -> float:
        """
        计算示例的综合评分
        
        Args:
            question: 用户问题
            example: 示例数据
            
        Returns:
            float: 综合评分 (0-1)
        """
        # 基础相似度分数 (权重: 40%)
        similarity_score = example.get('similarity', 0.0) * 0.4
        
        # 历史评分 (权重: 20%)
        rating = example.get('rating', 0.0)
        rating_score = min(1.0, max(0.0, (rating + 1) / 2)) * 0.2  # 归一化到0-1
        
        # 使用频率 (权重: 15%)
        usage_count = example.get('usage_count', 0)
        usage_score = min(1.0, usage_count / 10.0) * 0.15  # 使用次数越多分数越高
        
        # SQL复杂度匹配 (权重: 15%)
        complexity_score = self._calculate_sql_complexity_match(
            question, example.get('sql', '')
        ) * 0.15
        
        # 时效性 (权重: 10%)
        recency_score = self._calculate_recency_score(example) * 0.1
        
        total_score = (
            similarity_score + rating_score + usage_score + 
            complexity_score + recency_score
        )
        
        return min(1.0, total_score)
    
    def _calculate_sql_complexity_match(self, question: str, sql: str) -> float:
        """
        计算SQL复杂度匹配度
        
        Args:
            question: 用户问题
            sql: SQL语句
            
        Returns:
            float: 复杂度匹配分数 (0-1)
        """
        # 从问题推断期望的查询复杂度
        question_lower = question.lower()
        
        # 简单查询指标
        simple_indicators = ['查询', '显示', '列出', '获取', '查看', '找到']
        # 中等复杂度指标
        medium_indicators = ['统计', '计算', '分组', '排序', '前', '最', '平均', '总计']
        # 复杂查询指标
        complex_indicators = ['关联', '连接', '子查询', '嵌套', '复杂', '多表', '联合']
        
        question_complexity = 1  # 默认简单
        if any(indicator in question_lower for indicator in complex_indicators):
            question_complexity = 3
        elif any(indicator in question_lower for indicator in medium_indicators):
            question_complexity = 2
        
        # 分析SQL复杂度
        sql_upper = sql.upper()
        sql_complexity = 1  # 默认简单
        
        # 复杂SQL特征
        if any(keyword in sql_upper for keyword in ['JOIN', 'UNION', 'SUBQUERY', 'EXISTS', 'WITH']):
            sql_complexity = 3
        elif any(keyword in sql_upper for keyword in ['GROUP BY', 'ORDER BY', 'HAVING', 'DISTINCT']):
            sql_complexity = 2
        
        # 计算匹配度
        complexity_diff = abs(question_complexity - sql_complexity)
        if complexity_diff == 0:
            return 1.0  # 完全匹配
        elif complexity_diff == 1:
            return 0.7  # 接近匹配
        else:
            return 0.3  # 差异较大
    
    def _calculate_recency_score(self, example: Dict[str, Any]) -> float:
        """
        计算时效性分数
        
        Args:
            example: 示例数据
            
        Returns:
            float: 时效性分数 (0-1)
        """
        try:
            from datetime import datetime, timedelta
            
            # 获取创建时间
            created_at = example.get('created_at')
            if not created_at:
                return 0.5  # 没有时间信息，给中等分数
            
            # 解析时间
            if isinstance(created_at, str):
                try:
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    return 0.5
            elif isinstance(created_at, datetime):
                created_time = created_at
            else:
                return 0.5
            
            # 计算时间差
            now = datetime.now()
            time_diff = now - created_time
            
            # 时效性评分：越新分数越高
            if time_diff.days <= 7:
                return 1.0  # 一周内
            elif time_diff.days <= 30:
                return 0.8  # 一月内
            elif time_diff.days <= 90:
                return 0.6  # 三月内
            elif time_diff.days <= 365:
                return 0.4  # 一年内
            else:
                return 0.2  # 超过一年
                
        except Exception as e:
            logger.warning(f"计算时效性分数失败: {str(e)}")
            return 0.5
    
    def _apply_diversity_filter(self, 
                              scored_examples: List[Dict[str, Any]], 
                              max_examples: int) -> List[Dict[str, Any]]:
        """
        应用多样性过滤，避免选择过于相似的示例
        
        Args:
            scored_examples: 已评分的示例列表（按分数降序）
            max_examples: 最大示例数量
            
        Returns:
            List[Dict]: 过滤后的示例列表
        """
        if len(scored_examples) <= max_examples:
            return scored_examples
        
        selected = []
        
        # 总是选择第一个（分数最高的）
        if scored_examples:
            selected.append(scored_examples[0])
        
        # 为剩余位置选择多样化的示例
        for candidate in scored_examples[1:]:
            if len(selected) >= max_examples:
                break
            
            # 检查与已选择示例的相似度
            is_diverse = True
            for selected_example in selected:
                similarity = self._calculate_example_similarity(candidate, selected_example)
                if similarity > 0.7:  # 降低相似度阈值，使过滤更严格
                    is_diverse = False
                    break
            
            if is_diverse:
                selected.append(candidate)
        
        # 如果多样性过滤后示例不足，补充高分示例
        if len(selected) < max_examples:
            for candidate in scored_examples:
                if len(selected) >= max_examples:
                    break
                if candidate not in selected:
                    selected.append(candidate)
        
        return selected[:max_examples]
    
    def _calculate_example_similarity(self, 
                                    example1: Dict[str, Any], 
                                    example2: Dict[str, Any]) -> float:
        """
        计算两个示例之间的相似度
        
        Args:
            example1: 示例1
            example2: 示例2
            
        Returns:
            float: 相似度分数 (0-1)
        """
        # 问题相似度
        question1 = example1.get('question', '')
        question2 = example2.get('question', '')
        question_similarity = self._calculate_text_similarity(question1, question2)
        
        # SQL相似度
        sql1 = example1.get('sql', '')
        sql2 = example2.get('sql', '')
        sql_similarity = self._calculate_text_similarity(sql1, sql2)
        
        # 综合相似度
        return (question_similarity * 0.6 + sql_similarity * 0.4)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（简单实现）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            float: 相似度分数 (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        # 简单的字符级相似度计算
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # 计算最长公共子序列长度
        def lcs_length(s1, s2):
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        lcs_len = lcs_length(text1_lower, text2_lower)
        max_len = max(len(text1_lower), len(text2_lower))
        
        return lcs_len / max_len if max_len > 0 else 0.0
    
    def _truncate_prompt_intelligently(self, prompt: str, max_length: int) -> str:
        """
        智能截断提示词，保留最重要的部分
        
        优化策略:
        1. 优先级保护：确保核心信息不被截断
        2. 示例智能选择：保留最有价值的示例
        3. 渐进式截断：逐步减少非关键内容
        4. 结构完整性：保持提示词的逻辑结构
        
        Args:
            prompt: 原始提示词
            max_length: 最大长度
            
        Returns:
            str: 截断后的提示词
        """
        if len(prompt) <= max_length:
            return prompt
        
        lines = prompt.split('\n')
        
        # 定义重要性优先级（数字越小越重要）
        section_priorities = {
            "用户问题:": 1,
            "数据库Schema信息:": 2,
            "请基于以上信息生成准确的SQL查询语句": 3,
            "要求:": 4,
            "相关表名:": 5,
            "参考相似查询示例:": 6,
            "💡 提示:": 7
        }
        
        # 分类和标记行
        categorized_lines = []
        current_section = ""
        current_priority = 999
        
        for line in lines:
            line_stripped = line.strip()
            
            # 识别新的部分
            for section, priority in section_priorities.items():
                if section in line:
                    current_section = section
                    current_priority = priority
                    break
            
            categorized_lines.append({
                'content': line,
                'section': current_section,
                'priority': current_priority,
                'is_example': '示例' in line and ':' in line,
                'length': len(line)
            })
        
        # 按优先级排序并逐步构建结果
        result_lines = []
        current_length = 0
        
        # 第一轮：添加最高优先级内容（1-4级）
        for line_info in categorized_lines:
            if line_info['priority'] <= 4:
                if current_length + line_info['length'] + 1 <= max_length:
                    result_lines.append(line_info['content'])
                    current_length += line_info['length'] + 1
        
        # 第二轮：添加中等优先级内容（5-6级）
        for line_info in categorized_lines:
            if 5 <= line_info['priority'] <= 6:
                if current_length + line_info['length'] + 1 <= max_length:
                    result_lines.append(line_info['content'])
                    current_length += line_info['length'] + 1
        
        # 第三轮：智能添加示例内容
        example_lines = [line_info for line_info in categorized_lines 
                        if line_info['is_example'] or '相似度:' in line_info['content'] 
                        or 'SQL:' in line_info['content']]
        
        # 按示例分组
        current_example = []
        example_groups = []
        
        for line_info in example_lines:
            if line_info['is_example'] and current_example:
                example_groups.append(current_example)
                current_example = [line_info]
            else:
                current_example.append(line_info)
        
        if current_example:
            example_groups.append(current_example)
        
        # 按示例质量排序（基于相似度）
        def get_example_quality(example_group):
            for line_info in example_group:
                if '相似度:' in line_info['content']:
                    try:
                        similarity_str = line_info['content'].split('相似度:')[1].strip()
                        return float(similarity_str)
                    except:
                        pass
            return 0.0
        
        example_groups.sort(key=get_example_quality, reverse=True)
        
        # 添加示例，直到达到长度限制
        added_examples = 0
        for example_group in example_groups:
            if added_examples >= 3:  # 最多3个示例
                break
                
            group_length = sum(line_info['length'] + 1 for line_info in example_group)
            if current_length + group_length <= max_length:
                for line_info in example_group:
                    result_lines.append(line_info['content'])
                current_length += group_length
                added_examples += 1
            else:
                # 尝试添加截断的示例
                truncated_group = []
                temp_length = current_length
                
                for line_info in example_group:
                    if temp_length + line_info['length'] + 1 <= max_length:
                        truncated_group.append(line_info['content'])
                        temp_length += line_info['length'] + 1
                    else:
                        break
                
                if truncated_group:
                    result_lines.extend(truncated_group)
                    result_lines.append("... (示例已截断)")
                    current_length = temp_length + 20  # "... (示例已截断)" 的长度
                break
        
        # 第四轮：添加剩余低优先级内容
        for line_info in categorized_lines:
            if line_info['priority'] > 6 and not line_info['is_example']:
                if current_length + line_info['length'] + 1 <= max_length:
                    result_lines.append(line_info['content'])
                    current_length += line_info['length'] + 1
        
        final_prompt = '\n'.join(result_lines)
        
        # 确保结构完整性
        if "要求:" in final_prompt and not final_prompt.rstrip().endswith(("调整", "要求", "语句")):
            final_prompt += "\n\n请生成对应的SQL查询语句。"
        
        return final_prompt
    
    def validate_sql_quality(self, sql: str) -> tuple[bool, str]:
        """
        创建SQL质量验证机制，确保生成的SQL语法正确且安全
        
        Args:
            sql: 待验证的SQL语句
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            # 基础安全性验证
            is_safe, safety_error = self.validate_sql_safety(sql)
            if not is_safe:
                return False, f"安全验证失败: {safety_error}"
            
            # 语法结构验证
            sql_clean = sql.strip()
            if not sql_clean:
                return False, "SQL语句为空"
            
            # 检查SQL基本结构
            sql_upper = sql_clean.upper()
            
            # 验证SELECT语句结构
            if not sql_upper.startswith('SELECT'):
                return False, "必须是SELECT查询语句"
            
            # 检查基本SQL关键词的合理性
            required_keywords = ['SELECT']
            for keyword in required_keywords:
                if keyword not in sql_upper:
                    return False, f"缺少必要关键词: {keyword}"
            
            # 检查括号匹配
            if sql_clean.count('(') != sql_clean.count(')'):
                return False, "括号不匹配"
            
            # 检查引号匹配
            single_quotes = sql_clean.count("'") - sql_clean.count("\\'")
            double_quotes = sql_clean.count('"') - sql_clean.count('\\"')
            if single_quotes % 2 != 0:
                return False, "单引号不匹配"
            if double_quotes % 2 != 0:
                return False, "双引号不匹配"
            
            # 检查SQL长度合理性
            if len(sql_clean) > 10000:
                return False, "SQL语句过长，可能存在问题"
            
            # 检查是否包含明显的语法错误模式
            error_patterns = [
                r'SELECT\s*$',  # SELECT后面没有内容
                r'FROM\s*$',    # FROM后面没有内容
                r'WHERE\s*$',   # WHERE后面没有内容
                r'GROUP\s+BY\s*$',  # GROUP BY后面没有内容
                r'ORDER\s+BY\s*$',  # ORDER BY后面没有内容
            ]
            
            import re
            for pattern in error_patterns:
                if re.search(pattern, sql_upper):
                    return False, f"SQL语法不完整，匹配错误模式: {pattern}"
            
            # 检查常见的SQL注入模式
            injection_patterns = [
                r';\s*(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE)',
                r'UNION\s+SELECT.*--',
                r'OR\s+1\s*=\s*1',
                r'AND\s+1\s*=\s*1',
                r'/\*.*\*/',  # SQL注释
                r'--.*$',     # 行注释
            ]
            
            for pattern in injection_patterns:
                if re.search(pattern, sql_upper, re.MULTILINE):
                    return False, f"检测到潜在的SQL注入模式: {pattern}"
            
            # 验证字段和表名的合理性（基础检查）
            # 检查是否有明显不合理的标识符
            identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
            identifiers = re.findall(identifier_pattern, sql_clean)
            
            # 过滤掉SQL关键词
            sql_keywords = {
                'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING',
                'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON', 'AS',
                'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE',
                'IS', 'NULL', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN',
                'LIMIT', 'OFFSET', 'UNION', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'
            }
            
            table_field_identifiers = [
                id for id in identifiers 
                if id.upper() not in sql_keywords and len(id) > 1
            ]
            
            # 检查标识符是否合理（不能全是数字或特殊字符）
            for identifier in table_field_identifiers:
                if identifier.isdigit():
                    return False, f"不合理的标识符: {identifier}"
                if len(identifier) > 64:  # MySQL标识符长度限制
                    return False, f"标识符过长: {identifier}"
            
            logger.info(f"SQL质量验证通过: {sql_clean[:100]}...")
            return True, ""
            
        except Exception as e:
            logger.error(f"SQL质量验证异常: {str(e)}")
            return False, f"验证过程异常: {str(e)}"
    
    def generate_sql(self, 
                    question: str, 
                    schema_info: str, 
                    examples: Optional[List[Dict[str, str]]] = None,
                    table_names: Optional[List[str]] = None,
                    use_rag: bool = True) -> str:
        """
        生成SQL查询（集成RAG功能）
        
        Args:
            question: 自然语言问题
            schema_info: 数据库Schema信息
            examples: SQL示例
            table_names: 相关表名列表
            use_rag: 是否使用RAG知识库
            
        Returns:
            str: 生成的SQL查询或错误信息
        """
        # 如果启用RAG，使用RAG增强生成
        if use_rag and self.knowledge_manager.enabled:
            return self.generate_sql_with_rag(question, schema_info, None, table_names)
        
        # 传统生成方式（向后兼容）
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
            
            # 验证SQL质量
            is_valid_sql, validation_error = self.validate_sql_quality(sql_query)
            if not is_valid_sql:
                logger.warning(f"生成SQL质量验证失败: {validation_error}")
                return f"ERROR_SQL_VALIDATION_FAILED: {validation_error}"
            
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
    
    def add_positive_feedback(self, question: str, sql: str, description: str = None) -> bool:
        """
        添加正面反馈到知识库
        
        Args:
            question: 用户问题
            sql: SQL查询
            description: 描述信息
            
        Returns:
            bool: 是否成功添加
        """
        if not self.knowledge_manager.enabled:
            logger.warning("知识库未启用，无法添加反馈")
            return False
        
        return self.knowledge_manager.add_positive_feedback(
            question=question,
            sql=sql,
            description=description
        )
    
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