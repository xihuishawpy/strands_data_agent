"""
API数据模型
定义请求和响应的数据结构
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    """查询请求模型"""
    question: str = Field(..., description="用户问题", min_length=1, max_length=1000)
    auto_visualize: bool = Field(True, description="是否自动生成可视化")
    analysis_level: str = Field("standard", description="分析级别: basic, standard, detailed")

class QueryResponse(BaseModel):
    """查询响应模型"""
    success: bool = Field(..., description="是否成功")
    question: str = Field(..., description="原始问题")
    sql_query: Optional[str] = Field(None, description="生成的SQL查询")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="查询结果数据")
    analysis: Optional[str] = Field(None, description="数据分析结果")
    chart_info: Optional[Dict[str, Any]] = Field(None, description="图表信息")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据信息")

class SchemaResponse(BaseModel):
    """Schema响应模型"""
    database_type: str = Field(..., description="数据库类型")
    tables: Dict[str, Any] = Field(..., description="表信息")
    relationships: List[Dict[str, Any]] = Field(..., description="表关系")

class TableSchemaResponse(BaseModel):
    """表Schema响应模型"""
    table_name: str = Field(..., description="表名")
    columns: List[Dict[str, Any]] = Field(..., description="字段信息")
    primary_keys: List[str] = Field(..., description="主键")
    foreign_keys: List[Dict[str, Any]] = Field(..., description="外键")
    indexes: List[Dict[str, Any]] = Field(..., description="索引")

class SystemStatus(BaseModel):
    """系统状态模型"""
    status: str = Field(..., description="系统状态")
    database_connected: bool = Field(..., description="数据库连接状态")
    schema_cache_status: str = Field(..., description="Schema缓存状态")
    config_valid: bool = Field(..., description="配置是否有效")
    warnings: List[str] = Field(default_factory=list, description="系统警告")

class ExplainResponse(BaseModel):
    """查询解释响应模型"""
    question: str = Field(..., description="原始问题")
    sql_query: str = Field(..., description="生成的SQL")
    sql_valid: bool = Field(..., description="SQL是否有效")
    schema_used: str = Field(..., description="使用的Schema信息")
    execution_plan: Optional[Dict[str, Any]] = Field(None, description="执行计划")
    tables_involved: List[str] = Field(default_factory=list, description="涉及的表")

class ChartRequest(BaseModel):
    """图表请求模型"""
    data: List[Dict[str, Any]] = Field(..., description="数据")
    chart_type: str = Field(..., description="图表类型")
    title: str = Field("数据图表", description="图表标题")
    x_axis: Optional[str] = Field(None, description="X轴字段")
    y_axis: Optional[str] = Field(None, description="Y轴字段")

class ChartResponse(BaseModel):
    """图表响应模型"""
    success: bool = Field(..., description="是否成功")
    chart_type: str = Field(..., description="图表类型")
    title: str = Field(..., description="图表标题")
    file_path: str = Field(..., description="图表文件路径")
    data_points: int = Field(..., description="数据点数量")
    error: Optional[str] = Field(None, description="错误信息") 