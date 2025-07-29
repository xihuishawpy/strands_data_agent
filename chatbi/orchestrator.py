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
    
    def query_stream(self, 
                    question: str, 
                    auto_visualize: bool = True,
                    analysis_level: str = "standard"):
        """
        流式智能查询流程 - 实时返回处理进度
        
        Yields:
            Dict: 包含step_info或final_result的字典
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 开始流式智能查询流程: {question}")
            
            # ===== 步骤1: 获取数据库Schema信息 =====
            yield {"step_info": "✅ **步骤1完成**: Schema信息获取成功"}
            
            schema_info = self._get_relevant_schema(question)
            if not schema_info:
                yield {"final_result": self._create_error_result(
                    question, "无法获取数据库Schema信息", start_time
                )}
                return
            
            # ===== 步骤2: 生成SQL查询 =====
            yield {"step_info": "🔧 **步骤2**: 正在生成SQL查询..."}
            
            sql_query = self._generate_sql(question, schema_info)
            
            if sql_query.startswith("ERROR"):
                yield {"final_result": self._create_error_result(
                    question, f"SQL生成失败: {sql_query}", start_time
                )}
                return
            
            yield {"step_info": f"✅ **步骤2完成**: SQL查询生成成功\n```sql\n{sql_query[:200]}{'...' if len(sql_query) > 200 else ''}\n```"}
            
            # ===== 步骤3: 执行SQL查询 =====
            yield {"step_info": "⚡ **步骤3**: 正在执行SQL查询..."}
            
            sql_result, final_sql = self._execute_sql_with_retry(sql_query, schema_info, question)
            
            if not sql_result.success:
                yield {"final_result": self._create_error_result(
                    question, f"SQL执行失败: {sql_result.error}", start_time, final_sql or sql_query
                )}
                return
            
            sql_query = final_sql or sql_query
            yield {"step_info": f"✅ **步骤3完成**: 查询执行成功，获得 **{sql_result.row_count}** 行数据"}
            
            # ===== 步骤4: 数据分析 =====
            analysis = None
            visualization_suggestion = None
            
            if analysis_level != "none" and sql_result.data:
                yield {"step_info": "🔍 **步骤4**: 正在进行智能数据分析..."}
                
                analysis = self._analyze_data(question, sql_query, sql_result, analysis_level)
                yield {"step_info": "✅ **步骤4完成**: 数据分析完成"}
                
                # 获取可视化建议
                if auto_visualize:
                    yield {"step_info": "🎨 **步骤5**: 正在生成可视化建议..."}
                    visualization_suggestion = self._get_visualization_suggestion(sql_result, question)
                    chart_type = visualization_suggestion.get('chart_type', 'none')
                    yield {"step_info": f"✅ **步骤5完成**: 建议使用 **{chart_type}** 图表"}
            
            # ===== 步骤6: 创建可视化 =====
            chart_info = None
            if auto_visualize and sql_result.data and visualization_suggestion:
                yield {"step_info": "🎯 **步骤6**: 正在创建数据可视化..."}
                
                chart_info = self._create_chart_from_suggestion(sql_result, visualization_suggestion)
                
                if chart_info and chart_info.get("success"):
                    yield {"step_info": "✅ **步骤6完成**: 可视化图表创建成功"}
                else:
                    yield {"step_info": "⚠️ **步骤6**: 可视化创建失败或跳过"}
            
            execution_time = time.time() - start_time
            yield {"step_info": f"🎉 **查询完成**: 总耗时 {execution_time:.2f}秒"}
            
            # 返回最终结果
            result = QueryResult(
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
                    "schema_tables_used": self._extract_tables_from_sql(sql_query),
                    "visualization_suggestion": visualization_suggestion
                }
            )
            
            yield {"final_result": result}
            
        except Exception as e:
            logger.error(f"❌ 流式查询流程失败: {str(e)}")
            yield {"final_result": self._create_error_result(
                question, f"系统错误: {str(e)}", start_time
            )}

    def query(self, 
             question: str, 
             auto_visualize: bool = True,
             analysis_level: str = "standard") -> QueryResult:
        """
        完整的智能查询流程
        
        流程: Schema获取 -> SQL生成 -> SQL执行 -> 数据分析 -> 可视化建议 -> 图表创建
        
        Args:
            question: 用户问题
            auto_visualize: 是否自动生成可视化
            analysis_level: 分析级别 (basic, standard, detailed)
            
        Returns:
            QueryResult: 查询结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 开始智能查询流程: {question}")
            
            # ===== 步骤1: 获取数据库Schema信息 =====
            logger.info("📋 步骤1: 获取数据库Schema信息")
            schema_info = self._get_relevant_schema(question)
            if not schema_info:
                return self._create_error_result(
                    question, "无法获取数据库Schema信息", start_time
                )
            logger.info("✅ Schema信息获取成功")
            
            # ===== 步骤2: 生成SQL查询 =====
            logger.info("🔧 步骤2: 生成SQL查询")
            sql_query = self._generate_sql(question, schema_info)
            logger.info(f"生成的SQL: {sql_query}")
            
            if sql_query.startswith("ERROR"):
                return self._create_error_result(
                    question, f"SQL生成失败: {sql_query}", start_time
                )
            logger.info("✅ SQL生成成功")
            
            # ===== 步骤3: 执行SQL查询 =====
            logger.info("⚡ 步骤3: 执行SQL查询")
            sql_result, final_sql = self._execute_sql_with_retry(sql_query, schema_info, question)
            
            if not sql_result.success:
                return self._create_error_result(
                    question, f"SQL执行失败: {sql_result.error}", start_time, final_sql or sql_query
                )
            
            # 更新SQL查询为最终使用的版本（可能是修复后的）
            sql_query = final_sql or sql_query
            logger.info(f"✅ SQL执行成功: 获得 {sql_result.row_count} 行数据")
            
            # ===== 步骤4: 数据分析 =====
            logger.info("🔍 步骤4: 执行数据分析")
            analysis = None
            visualization_suggestion = None
            
            if analysis_level != "none" and sql_result.data:
                analysis = self._analyze_data(question, sql_query, sql_result, analysis_level)
                logger.info("✅ 数据分析完成")
                
                # 获取可视化建议（作为分析的一部分）
                if auto_visualize:
                    logger.info("🎨 获取可视化建议")
                    visualization_suggestion = self._get_visualization_suggestion(sql_result, question)
                    logger.info(f"可视化建议: {visualization_suggestion.get('chart_type', 'none')}")
            
            # ===== 步骤5: 创建可视化 =====
            chart_info = None
            if auto_visualize and sql_result.data and visualization_suggestion:
                logger.info("🎯 步骤5: 创建数据可视化")
                chart_info = self._create_chart_from_suggestion(sql_result, visualization_suggestion)
                
                if chart_info and chart_info.get("success"):
                    logger.info("✅ 可视化创建成功")
                else:
                    logger.warning("⚠️ 可视化创建失败或跳过")
            
            execution_time = time.time() - start_time
            logger.info(f"🎉 查询流程完成，总耗时: {execution_time:.2f}秒")
            
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
                    "schema_tables_used": self._extract_tables_from_sql(sql_query),
                    "visualization_suggestion": visualization_suggestion
                }
            )
            
        except Exception as e:
            logger.error(f"❌ 查询流程失败: {str(e)}")
            return self._create_error_result(
                question, f"系统错误: {str(e)}", start_time
            )
    

    
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
    
    def _create_error_result(self, question: str, error: str, start_time: float, sql_query: str = None) -> QueryResult:
        """创建错误结果"""
        return QueryResult(
            success=False,
            question=question,
            sql_query=sql_query,
            error=error,
            execution_time=time.time() - start_time
        )
    
    def _execute_sql_with_retry(self, sql_query: str, schema_info: str, question: str) -> tuple[Any, str]:
        """执行SQL查询，包含重试机制
        
        Returns:
            tuple: (sql_result, final_sql_query)
        """
        # 第一次尝试执行
        sql_result = self._execute_sql(sql_query)
        
        if sql_result.success:
            return sql_result, sql_query
        
        # 如果失败，尝试修复SQL并重新执行
        logger.warning(f"SQL执行失败，尝试修复: {sql_result.error}")
        fixed_sql = self._try_fix_sql(sql_query, sql_result.error, schema_info, question)
        
        if fixed_sql and fixed_sql != sql_query:
            logger.info("🔧 使用修复后的SQL重新执行")
            logger.info(f"修复后的SQL: {fixed_sql}")
            
            # 执行修复后的SQL
            fixed_result = self._execute_sql(fixed_sql)
            if fixed_result.success:
                return fixed_result, fixed_sql
            else:
                # 如果修复后的SQL也失败，返回原始错误
                logger.error(f"修复后的SQL也执行失败: {fixed_result.error}")
                return sql_result, sql_query
        
        # 没有修复或修复失败，返回原始结果
        return sql_result, sql_query
    
    def _get_visualization_suggestion(self, sql_result: Any, question: str) -> Dict[str, Any]:
        """获取可视化建议"""
        try:
            if not sql_result.data:
                return {"chart_type": "none", "reason": "无数据"}
            
            # 构建查询结果字典
            query_result = {
                "data": sql_result.data,
                "columns": sql_result.columns,
                "row_count": sql_result.row_count
            }
            
            # 获取可视化建议
            chart_suggestion = self.data_analyst.suggest_visualization(query_result)
            
            # 添加原始问题作为上下文
            chart_suggestion["original_question"] = question
            
            return chart_suggestion
            
        except Exception as e:
            logger.error(f"获取可视化建议失败: {str(e)}")
            return {"chart_type": "none", "reason": f"建议生成失败: {str(e)}"}
    
    def _create_chart_from_suggestion(self, sql_result: Any, visualization_suggestion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """根据可视化建议创建图表"""
        try:
            chart_type = visualization_suggestion.get("chart_type")
            
            if chart_type == "none":
                logger.info("跳过可视化：建议类型为none")
                return None
            
            # 创建图表
            chart_result = self.visualizer.create_chart(
                data=sql_result.data,
                chart_config=visualization_suggestion
            )
            
            if chart_result and chart_result.get("success"):
                # 添加可视化建议信息到结果中
                chart_result["suggestion"] = visualization_suggestion
                return chart_result
            else:
                error_msg = chart_result.get('error', '未知错误') if chart_result else '图表创建返回None'
                logger.warning(f"图表创建失败: {error_msg}")
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