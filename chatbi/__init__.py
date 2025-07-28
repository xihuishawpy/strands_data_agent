"""
ChatBI - 企业级智能数据查询应用

基于 Strands Agents 框架构建的智能数据查询系统，支持：
- 自然语言到SQL的转换
- 安全的数据库查询执行
- 智能数据分析和解读
- 自动数据可视化
"""

from .orchestrator import ChatBIOrchestrator
from .config import Config

__version__ = "1.0.0"
__author__ = "ChatBI Team"

__all__ = [
    "ChatBIOrchestrator",
    "Config",
] 