"""
API路由模块
"""

from .query import router as query_router
from .schema import router as schema_router  
from .system import router as system_router

__all__ = [
    "query_router",
    "schema_router", 
    "system_router",
] 