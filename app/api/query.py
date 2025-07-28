"""
查询相关API路由
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Any

from chatbi import ChatBIOrchestrator
from ..models import QueryRequest, QueryResponse, ExplainResponse, ChartRequest, ChartResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])

def get_orchestrator(request: Request) -> ChatBIOrchestrator:
    """依赖注入：获取ChatBI主控智能体"""
    return request.app.state.orchestrator

@router.post("/query", response_model=QueryResponse)
async def query_data(
    request: QueryRequest,
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    执行数据查询
    
    - **question**: 自然语言问题
    - **auto_visualize**: 是否自动生成可视化图表
    - **analysis_level**: 分析级别 (basic/standard/detailed)
    """
    try:
        result = orchestrator.query(
            question=request.question,
            auto_visualize=request.auto_visualize,
            analysis_level=request.analysis_level
        )
        
        return QueryResponse(
            success=result.success,
            question=result.question,
            sql_query=result.sql_query,
            data=result.data,
            analysis=result.analysis,
            chart_info=result.chart_info,
            error=result.error,
            execution_time=result.execution_time,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"查询处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")

@router.get("/explain", response_model=ExplainResponse)
async def explain_query(
    question: str,
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    解释查询过程（不执行SQL）
    
    - **question**: 自然语言问题
    """
    try:
        explanation = orchestrator.explain_query(question)
        
        return ExplainResponse(
            question=explanation.get("question", question),
            sql_query=explanation.get("sql_query", ""),
            sql_valid=explanation.get("sql_valid", False),
            schema_used=explanation.get("schema_used", ""),
            execution_plan=explanation.get("execution_plan"),
            tables_involved=explanation.get("tables_involved", [])
        )
        
    except Exception as e:
        logger.error(f"查询解释失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询解释失败: {str(e)}")

@router.post("/chart", response_model=ChartResponse)
async def create_chart(
    request: ChartRequest,
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    创建数据图表
    
    - **data**: 数据列表
    - **chart_type**: 图表类型 (bar/line/pie/scatter/histogram)
    - **title**: 图表标题
    - **x_axis**: X轴字段名
    - **y_axis**: Y轴字段名
    """
    try:
        # 构建图表配置
        chart_config = {
            "chart_type": request.chart_type,
            "title": request.title
        }
        
        if request.x_axis:
            chart_config["x_axis"] = request.x_axis
        if request.y_axis:
            chart_config["y_axis"] = request.y_axis
        
        # 创建图表
        result = orchestrator.visualizer.create_chart(request.data, chart_config)
        
        if result.get("success"):
            return ChartResponse(
                success=True,
                chart_type=result["chart_type"],
                title=result["title"],
                file_path=result["file_path"],
                data_points=result["data_points"]
            )
        else:
            return ChartResponse(
                success=False,
                chart_type=request.chart_type,
                title=request.title,
                file_path="",
                data_points=0,
                error=result.get("error", "图表创建失败")
            )
            
    except Exception as e:
        logger.error(f"图表创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图表创建失败: {str(e)}")

@router.get("/history")
async def get_query_history():
    """
    获取查询历史（TODO: 实现查询历史存储）
    """
    # TODO: 实现查询历史功能
    return {
        "message": "查询历史功能待实现",
        "history": []
    }

@router.delete("/history")
async def clear_query_history():
    """
    清空查询历史（TODO: 实现查询历史存储）
    """
    # TODO: 实现查询历史功能
    return {
        "message": "查询历史已清空"
    } 