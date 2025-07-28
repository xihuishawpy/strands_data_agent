"""
ChatBI Web API主应用
提供REST API接口和Web界面
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbi import ChatBIOrchestrator
from chatbi.config import config
from .api import query_router, schema_router, system_router
from .models import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("启动ChatBI Web应用")
    
    # 验证配置
    validation = config.validate()
    if not validation["valid"]:
        logger.error("配置验证失败:")
        for error in validation["errors"]:
            logger.error(f"  - {error}")
        raise RuntimeError("配置验证失败")
    
    if validation["warnings"]:
        logger.warning("配置警告:")
        for warning in validation["warnings"]:
            logger.warning(f"  - {warning}")
    
    # 初始化ChatBI
    try:
        orchestrator = ChatBIOrchestrator()
        app.state.orchestrator = orchestrator
        logger.info("ChatBI初始化成功")
    except Exception as e:
        logger.error(f"ChatBI初始化失败: {str(e)}")
        raise RuntimeError(f"ChatBI初始化失败: {str(e)}")
    
    yield
    
    # 关闭时
    logger.info("关闭ChatBI Web应用")

# 创建FastAPI应用
app = FastAPI(
    title="ChatBI - 智能数据查询应用",
    description="基于Strands Agents框架的企业级智能数据查询系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.web.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置模板
templates = Jinja2Templates(directory="app/templates")

# 配置静态文件
static_dir = Path("app/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 注册API路由
app.include_router(query_router, prefix="/api/v1")
app.include_router(schema_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")

def get_orchestrator(request: Request) -> ChatBIOrchestrator:
    """依赖注入：获取ChatBI主控智能体"""
    return request.app.state.orchestrator

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "ChatBI",
        "version": "1.0.0"
    }

@app.post("/api/v1/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """查询接口"""
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/explain/{question}")
async def explain_endpoint(
    question: str,
    orchestrator: ChatBIOrchestrator = Depends(get_orchestrator)
):
    """查询解释接口"""
    try:
        explanation = orchestrator.explain_query(question)
        return explanation
    except Exception as e:
        logger.error(f"查询解释失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.web.host,
        port=config.web.port,
        reload=config.web.debug,
        log_level="info"
    ) 