"""
系统管理相关API路由
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Any

from chatbi import ChatBIOrchestrator
from chatbi.config import config
from ..models import SystemStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

def get_orchestrator(request: Request) -> ChatBIOrchestrator:
    """依赖注入：获取ChatBI主控智能体"""
    return request.app.state.orchestrator

@router.get("/system/status", response_model=SystemStatus)
async def get_system_status(
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    获取系统状态信息
    """
    try:
        # 检查数据库连接
        db_connected = False
        try:
            # 尝试获取表列表来测试连接
            tables = orchestrator.schema_manager.get_all_tables()
            db_connected = len(tables) >= 0  # 即使没有表也说明连接正常
        except Exception:
            db_connected = False
        
        # 检查配置
        validation = config.validate()
        
        # 检查Schema缓存状态
        schema_cache_status = "unknown"
        try:
            schema_info = orchestrator.schema_manager.get_database_schema()
            if schema_info and "tables" in schema_info:
                schema_cache_status = "active"
            else:
                schema_cache_status = "empty"
        except Exception:
            schema_cache_status = "error"
        
        # 确定整体状态
        if db_connected and validation["valid"]:
            status = "healthy"
        elif db_connected:
            status = "warning"
        else:
            status = "error"
        
        return SystemStatus(
            status=status,
            database_connected=db_connected,
            schema_cache_status=schema_cache_status,
            config_valid=validation["valid"],
            warnings=validation.get("warnings", []) + validation.get("errors", [])
        )
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

@router.get("/system/config")
async def get_system_config():
    """
    获取系统配置信息（脱敏）
    """
    try:
        # 返回脱敏的配置信息
        config_info = {
            "database": {
                "type": config.database.type,
                "host": config.database.host if config.database.host != "localhost" else "localhost",
                "port": config.database.port,
                "database": config.database.database[:3] + "***" if len(config.database.database) > 3 else "***"
            },
            "llm": {
                "model_name": config.llm.model_name,
                "coder_model": config.llm.coder_model,
                "embedding_model": config.llm.embedding_model,
                "rerank_model": config.llm.rerank_model,
                "base_url": config.llm.base_url
            },
            "web": {
                "host": config.web.host,
                "port": config.web.port,
                "debug": config.web.debug
            },
            "cache": {
                "knowledge_base_path": config.knowledge_base_path,
                "schema_cache_ttl": config.schema_cache_ttl
            }
        }
        
        return config_info
        
    except Exception as e:
        logger.error(f"获取配置信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置信息失败: {str(e)}")

@router.post("/system/validate")
async def validate_system_config():
    """
    验证系统配置
    """
    try:
        validation = config.validate()
        return {
            "valid": validation["valid"],
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", [])
        }
        
    except Exception as e:
        logger.error(f"配置验证失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"配置验证失败: {str(e)}")

@router.get("/system/logs")
async def get_system_logs(lines: int = 100):
    """
    获取系统日志（最新的N行）
    
    - **lines**: 返回的日志行数，默认100行
    """
    try:
        import os
        from pathlib import Path
        
        log_file = Path(config.log_file)
        
        if not log_file.exists():
            return {"logs": [], "message": "日志文件不存在"}
        
        # 读取最后N行
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "logs": [line.strip() for line in recent_lines],
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines)
        }
        
    except Exception as e:
        logger.error(f"获取系统日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统日志失败: {str(e)}")

@router.get("/system/stats")
async def get_system_stats(
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """
    获取系统统计信息
    """
    try:
        # 获取数据库统计
        db_stats = {}
        try:
            tables = orchestrator.schema_manager.get_all_tables()
            db_stats["table_count"] = len(tables)
            
            # 获取Schema信息
            schema_info = orchestrator.schema_manager.get_database_schema()
            if schema_info and "tables" in schema_info:
                total_columns = sum(
                    len(table_info.get("columns", [])) 
                    for table_info in schema_info["tables"].values()
                )
                db_stats["total_columns"] = total_columns
                db_stats["total_relationships"] = len(schema_info.get("relationships", []))
            
        except Exception as e:
            logger.warning(f"获取数据库统计失败: {str(e)}")
            db_stats = {"error": str(e)}
        
        # 缓存统计
        cache_stats = {
            "schema_cache_ttl": config.schema_cache_ttl,
            "knowledge_base_path": config.knowledge_base_path
        }
        
        return {
            "database_stats": db_stats,
            "cache_stats": cache_stats,
            "system_info": {
                "version": "1.0.0",
                "framework": "Strands Agents",
                "api_framework": "FastAPI"
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统统计失败: {str(e)}") 