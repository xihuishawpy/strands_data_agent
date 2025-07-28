"""
Schema相关API路由
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Any

from chatbi import ChatBIOrchestrator
from ..models import SchemaResponse, TableSchemaResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["schema"])

def get_orchestrator(request: Request) -> ChatBIOrchestrator:
    """依赖注入：获取ChatBI主控智能体"""
    return request.app.state.orchestrator

@router.get("/schema", response_model=SchemaResponse)
async def get_database_schema(
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    获取完整数据库Schema信息
    """
    try:
        schema_info = orchestrator.get_schema_info()
        
        if "error" in schema_info:
            raise HTTPException(status_code=500, detail=schema_info["error"])
        
        return SchemaResponse(
            database_type=schema_info.get("database_type", "unknown"),
            tables=schema_info.get("tables", {}),
            relationships=schema_info.get("relationships", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Schema失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取Schema失败: {str(e)}")

@router.get("/schema/tables")
async def get_table_list(
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    获取所有表名列表
    """
    try:
        tables = orchestrator.schema_manager.get_all_tables()
        return {"tables": tables}
        
    except Exception as e:
        logger.error(f"获取表列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取表列表失败: {str(e)}")

@router.get("/schema/tables/{table_name}", response_model=TableSchemaResponse)
async def get_table_schema(
    table_name: str,
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    获取特定表的Schema信息
    
    - **table_name**: 表名
    """
    try:
        table_info = orchestrator.get_schema_info(table_name)
        
        if "error" in table_info:
            raise HTTPException(status_code=404, detail=f"表 {table_name} 不存在或获取失败")
        
        if not table_info:
            raise HTTPException(status_code=404, detail=f"表 {table_name} 不存在")
        
        return TableSchemaResponse(
            table_name=table_info.get("table_name", table_name),
            columns=table_info.get("columns", []),
            primary_keys=table_info.get("primary_keys", []),
            foreign_keys=table_info.get("foreign_keys", []),
            indexes=table_info.get("indexes", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表Schema失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取表Schema失败: {str(e)}")

@router.get("/schema/summary")
async def get_schema_summary(
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    获取数据库Schema文本摘要
    """
    try:
        summary = orchestrator.schema_manager.get_schema_summary()
        return {"summary": summary}
        
    except Exception as e:
        logger.error(f"获取Schema摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取Schema摘要失败: {str(e)}")

@router.post("/schema/refresh")
async def refresh_schema_cache(
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    刷新Schema缓存
    """
    try:
        success = orchestrator.refresh_schema()
        
        if success:
            return {"message": "Schema缓存刷新成功"}
        else:
            raise HTTPException(status_code=500, detail="Schema缓存刷新失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新Schema缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刷新Schema缓存失败: {str(e)}")

@router.get("/schema/search")
async def search_relevant_tables(
    keywords: str,
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    根据关键词搜索相关表
    
    - **keywords**: 搜索关键词（用逗号分隔）
    """
    try:
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        
        if not keyword_list:
            raise HTTPException(status_code=400, detail="请提供搜索关键词")
        
        relevant_tables = orchestrator.schema_manager.search_relevant_tables(keyword_list)
        
        return {
            "keywords": keyword_list,
            "relevant_tables": relevant_tables
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索相关表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索相关表失败: {str(e)}") 