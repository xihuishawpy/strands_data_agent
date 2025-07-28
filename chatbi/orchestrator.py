"""
ChatBI主控智能体
统一调度各个组件，实现完整的智能数据查询工作流
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time

from .config import config
from .database import get_schema_manager, get_sql_executor
from .agents import get_sql_generator, get_data_analyst, get_sql_fixer
from .tools import get_visualizer

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    question: str
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    analysis: Optional[str] = None
    chart_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatBIOrchestrator:
    """ChatBI主控智能体"""
    
    def __init__(self):
        """初始化主控智能体"""
        # 初始化各个组件
        self.schema_manager = get_schema_manager()
        self.sql_executor = get_sql_executor()
        self.sql_generator = get_sql_generator()
        self.data_analyst = get_data_analyst()
        self.sql_fixer = get_sql_fixer()
        self.visualizer = get_visualizer()
        
        # 缓存Schema信息
        self._schema_summary = None
        self._last_schema_update = 0
        
        logger.info("ChatBI主控智能体初始化完成")
    
    def query(self, 
             question: str, 
             auto_visualize: bool = True,
             analysis_level: str = "standard") -> QueryResult:
        """
        处理用户查询
        
        Args:
            question: 用户问题
            auto_visualize: 是否自动生成可视化
            analysis_level: 分析级别 (basic, standard, detailed)
            
        Returns:
            QueryResult: 查询结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始处理查询: {question}")
            
            # 步骤1: 获取相关Schema信息
            schema_info = self._get_relevant_schema(question)
            if not schema_info:
                return QueryResult(
                    success=False,
                    question=question,
                    error="无法获取数据库Schema信息",
                    execution_time=time.time() - start_time
                )
            
            # 步骤2: 生成SQL查询
            logger.info("开始生成SQL查询")
            sql_query = self._generate_sql(question, schema_info)
            logger.info(f"生成的SQL: {sql_query}")
            
            if sql_query.startswith("ERROR"):
                return QueryResult(
                    success=False,
                    question=question,
                    error=f"SQL生成失败: {sql_query}",
                    execution_time=time.time() - start_time
                )
            
            # 步骤3: 执行SQL查询
            logger.info("开始执行SQL查询")
            sql_result = self._execute_sql(sql_query)
            logger.info(f"SQL执行结果: 成功={sql_result.success}, 行数={sql_result.row_count if hasattr(sql_result, 'row_count') else 0}")
            if not sql_result.success:
                # 尝试修复SQL并重新执行
                fixed_sql = self._try_fix_sql(sql_query, sql_result.error, schema_info, question)
                if fixed_sql and fixed_sql != sql_query:
                    logger.info("尝试使用修复的SQL重新执行")
                    sql_result = self._execute_sql(fixed_sql)
                    if sql_result.success:
                        sql_query = fixed_sql
                
                if not sql_result.success:
                    return QueryResult(
                        success=False,
                        question=question,
                        sql_query=sql_query,
                        error=f"SQL执行失败: {sql_result.error}",
                        execution_time=time.time() - start_time
                    )
            
            # 步骤4: 数据分析
            analysis = None
            if analysis_level != "none":
                analysis = self._analyze_data(question, sql_query, sql_result, analysis_level)
            
            # 步骤5: 可视化（可选）
            chart_info = None
            if auto_visualize and sql_result.data:
                chart_info = self._create_visualization(sql_result, question)
            
            execution_time = time.time() - start_time
            
            logger.info(f"查询处理完成，耗时: {execution_time:.2f}秒")
            
            return QueryResult(
                success=True,
                question=question,
                sql_query=sql_query,
                data=sql_result.data,
                analysis=analysis,
                chart_info=chart_info,
                execution_time=execution_time,
                metadata={
                    "row_count": sql_result.row_count,
                    "columns": sql_result.columns,
                    "schema_tables_used": self._extract_tables_from_sql(sql_query)
                }
            )
            
        except Exception as e:
            logger.error(f"查询处理失败: {str(e)}")
            return QueryResult(
                success=False,
                question=question,
                error=f"系统错误: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def explain_query(self, question: str) -> Dict[str, Any]:
        """
        解释查询过程（不执行）
        
        Args:
            question: 用户问题
            
        Returns:
            Dict[str, Any]: 解释信息
        """
        try:
            # 获取Schema信息
            schema_info = self._get_relevant_schema(question)
            
            # 生成SQL
            sql_query = self._generate_sql(question, schema_info)
            
            # 分析SQL
            explanation = {
                "question": question,
                "sql_query": sql_query,
                "sql_valid": not sql_query.startswith("ERROR"),
                "schema_used": schema_info[:200] + "..." if len(schema_info) > 200 else schema_info
            }
            
            if not sql_query.startswith("ERROR"):
                # 获取执行计划
                explain_result = self.sql_executor.explain_query(sql_query)
                explanation["execution_plan"] = explain_result
                
                # 分析涉及的表
                tables_used = self._extract_tables_from_sql(sql_query)
                explanation["tables_involved"] = tables_used
            
            return explanation
            
        except Exception as e:
            logger.error(f"查询解释失败: {str(e)}")
            return {"error": str(e)}
    
    def get_schema_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取Schema信息
        
        Args:
            table_name: 特定表名（可选）
            
        Returns:
            Dict[str, Any]: Schema信息
        """
        try:
            if table_name:
                return self.schema_manager.get_table_schema(table_name)
            else:
                return self.schema_manager.get_database_schema()
        except Exception as e:
            logger.error(f"获取Schema信息失败: {str(e)}")
            return {"error": str(e)}
    
    def refresh_schema(self) -> bool:
        """刷新Schema缓存"""
        try:
            self.schema_manager.refresh_cache()
            self._schema_summary = None
            self._last_schema_update = time.time()
            logger.info("Schema缓存刷新成功")
            return True
        except Exception as e:
            logger.error(f"Schema缓存刷新失败: {str(e)}")
            return False
    
    def _get_relevant_schema(self, question: str) -> str:
        """获取与问题相关的Schema信息"""
        try:
            # 检查是否需要更新Schema摘要
            current_time = time.time()
            if (not self._schema_summary or 
                current_time - self._last_schema_update > config.schema_cache_ttl):
                self._schema_summary = self.schema_manager.get_schema_summary()
                self._last_schema_update = current_time
            
            # 直接返回完整Schema摘要，不做关键词搜索
            return self._schema_summary
                
        except Exception as e:
            logger.error(f"获取相关Schema失败: {str(e)}")
            return self._schema_summary or "无法获取数据库Schema信息"
    

    
    def _generate_sql(self, question: str, schema_info: str) -> str:
        """生成SQL查询"""
        try:
            return self.sql_generator.generate_sql(
                question=question,
                schema_info=schema_info
            )
        except Exception as e:
            logger.error(f"SQL生成失败: {str(e)}")
            return f"ERROR_GENERATION_FAILED: {str(e)}"
    
    def _execute_sql(self, sql_query: str) -> Any:
        """执行SQL查询"""
        try:
            return self.sql_executor.execute(sql_query)
        except Exception as e:
            logger.error(f"SQL执行失败: {str(e)}")
            return type('SQLResult', (), {
                'success': False,
                'error': str(e),
                'data': [],
                'columns': [],
                'row_count': 0
            })()
    
    def _try_fix_sql(self, sql_query: str, error_msg: str, schema_info: str, original_question: str = "") -> Optional[str]:
        """尝试修复SQL错误"""
        try:
            logger.info(f"尝试修复SQL错误: {error_msg}")
            
            # 使用专门的SQL修复智能体
            fix_result = self.sql_fixer.analyze_and_fix_sql(
                original_sql=sql_query,
                error_message=error_msg,
                schema_info=schema_info,
                original_question=original_question
            )
            
            if fix_result.get("fixed_sql") and fix_result.get("is_valid", True):
                fixed_sql = fix_result["fixed_sql"]
                confidence = fix_result.get("confidence", 0.0)
                
                logger.info(f"SQL修复成功 (置信度: {confidence:.2f})")
                logger.info(f"修复分析: {fix_result.get('error_analysis', '')}")
                logger.info(f"修复后SQL: {fixed_sql}")
                
                # 只有在置信度足够高时才返回修复结果
                if confidence >= 0.6:
                    return fixed_sql
                else:
                    logger.warning(f"修复置信度过低 ({confidence:.2f})，不采用修复结果")
            else:
                logger.warning("SQL修复失败或修复结果无效")
                if fix_result.get("validation_errors"):
                    logger.warning(f"验证错误: {fix_result['validation_errors']}")
            
            return None
            
        except Exception as e:
            logger.error(f"SQL修复过程失败: {str(e)}")
            return None
    
    def _analyze_data(self, question: str, sql_query: str, sql_result: Any, analysis_level: str) -> str:
        """分析数据"""
        try:
            if not sql_result.data:
                return "查询结果为空，无法进行数据分析。"
            
            # 构建查询结果字典
            query_result = {
                "success": sql_result.success,
                "data": sql_result.data,
                "columns": sql_result.columns,
                "row_count": sql_result.row_count
            }
            
            # 根据分析级别调整分析要求
            analysis_requirements = {
                "basic": "请简要分析数据，提供基本统计信息",
                "standard": "请全面分析数据，提供关键洞察和建议", 
                "detailed": "请深入分析数据，包括趋势、异常、相关性等详细洞察"
            }.get(analysis_level, "请全面分析数据，提供关键洞察和建议")
            
            return self.data_analyst.analyze_data(
                query_result=query_result,
                original_question=question,
                sql_query=sql_query,
                analysis_requirements=analysis_requirements
            )
            
        except Exception as e:
            logger.error(f"数据分析失败: {str(e)}")
            return f"数据分析过程中出现错误: {str(e)}"
    
    def _create_visualization(self, sql_result: Any, question: str) -> Optional[Dict[str, Any]]:
        """创建数据可视化"""
        try:
            if not sql_result.data:
                return None
            
            # 构建查询结果字典
            query_result = {
                "data": sql_result.data
            }
            
            # 获取可视化建议
            chart_suggestion = self.data_analyst.suggest_visualization(query_result)
            
            if chart_suggestion.get("chart_type") == "none":
                return None
            
            # 创建图表
            chart_result = self.visualizer.create_chart(
                data=sql_result.data,
                chart_config=chart_suggestion
            )
            
            if chart_result.get("success"):
                return chart_result
            else:
                logger.warning(f"图表创建失败: {chart_result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"可视化创建失败: {str(e)}")
            return None
    
    def _extract_tables_from_sql(self, sql_query: str) -> List[str]:
        """从SQL中提取表名"""
        import re
        
        # 简单的表名提取，匹配FROM和JOIN后的表名
        pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(pattern, sql_query, re.IGNORECASE)
        
        return list(set(matches))  # 去重

# 全局主控智能体实例
_orchestrator: Optional[ChatBIOrchestrator] = None

def get_orchestrator() -> ChatBIOrchestrator:
    """获取全局主控智能体实例"""
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = ChatBIOrchestrator()
    
    return _orchestrator 