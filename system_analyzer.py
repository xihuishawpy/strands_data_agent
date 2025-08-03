#!/usr/bin/env python3
"""
ChatBI系统分析器
实时分析系统状态、性能和配置
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

class ChatBISystemAnalyzer:
    """ChatBI系统分析器"""
    
    def __init__(self):
        self.analysis_results = {}
        self.start_time = datetime.now()
    
    def analyze_configuration(self) -> Dict[str, Any]:
        """分析系统配置"""
        print("🔍 分析系统配置...")
        
        config_analysis = {
            "status": "success",
            "issues": [],
            "recommendations": [],
            "details": {}
        }
        
        try:
            from chatbi.config import config
            
            # 数据库配置分析
            db_config = {
                "type": config.database.type,
                "host": config.database.host,
                "port": config.database.port,
                "database": config.database.database,
                "connection_string_length": len(config.database.connection_string)
            }
            config_analysis["details"]["database"] = db_config
            
            # LLM配置分析
            llm_config = {
                "model_name": config.llm.model_name,
                "coder_model": config.llm.coder_model,
                "has_api_key": bool(config.llm.api_key),
                "api_key_length": len(config.llm.api_key) if config.llm.api_key else 0,
                "base_url": config.llm.base_url
            }
            config_analysis["details"]["llm"] = llm_config
            
            # RAG配置分析
            rag_config = {
                "enabled": config.rag.enabled,
                "similarity_threshold": config.rag.similarity_threshold,
                "confidence_threshold": config.rag.confidence_threshold,
                "max_examples": config.rag.max_examples,
                "vector_dimension": config.rag.vector_dimension
            }
            config_analysis["details"]["rag"] = rag_config
            
            # 重试配置分析
            retry_config = {
                "max_retries": config.retry.max_retries,
                "base_delay": config.retry.base_delay,
                "exponential_backoff": config.retry.exponential_backoff,
                "timeout": config.retry.timeout
            }
            config_analysis["details"]["retry"] = retry_config
            
            # 检查配置问题
            if not config.llm.api_key:
                config_analysis["issues"].append("LLM API密钥未设置")
                config_analysis["recommendations"].append("设置DASHSCOPE_API_KEY环境变量")
            
            if config.rag.similarity_threshold >= config.rag.confidence_threshold:
                config_analysis["issues"].append("RAG相似度阈值配置不合理")
                config_analysis["recommendations"].append("确保similarity_threshold < confidence_threshold")
            
            if config.retry.max_retries > 5:
                config_analysis["recommendations"].append("重试次数过多可能影响性能")
            
        except Exception as e:
            config_analysis["status"] = "error"
            config_analysis["error"] = str(e)
        
        return config_analysis
    
    def analyze_database_connectivity(self) -> Dict[str, Any]:
        """分析数据库连接状态"""
        print("🔍 分析数据库连接...")
        
        db_analysis = {
            "status": "success",
            "connection_status": False,
            "table_count": 0,
            "tables": [],
            "performance": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            from chatbi.database import get_database_connector
            
            connector = get_database_connector()
            
            # 测试连接
            start_time = time.time()
            if connector.is_connected or connector.connect():
                db_analysis["connection_status"] = True
                connection_time = time.time() - start_time
                db_analysis["performance"]["connection_time"] = connection_time
                
                # 获取表列表
                start_time = time.time()
                tables = connector.get_tables()
                query_time = time.time() - start_time
                
                db_analysis["table_count"] = len(tables)
                db_analysis["tables"] = tables[:10]  # 只显示前10个
                db_analysis["performance"]["table_query_time"] = query_time
                
                # 性能分析
                if connection_time > 2.0:
                    db_analysis["issues"].append("数据库连接时间过长")
                    db_analysis["recommendations"].append("检查网络连接或数据库性能")
                
                if query_time > 1.0:
                    db_analysis["issues"].append("表查询时间过长")
                    db_analysis["recommendations"].append("检查数据库索引或网络延迟")
                
                if len(tables) == 0:
                    db_analysis["issues"].append("数据库中没有表")
                    db_analysis["recommendations"].append("检查数据库权限或数据")
                
            else:
                db_analysis["connection_status"] = False
                db_analysis["issues"].append("无法连接到数据库")
                db_analysis["recommendations"].append("检查数据库配置和网络连接")
        
        except Exception as e:
            db_analysis["status"] = "error"
            db_analysis["error"] = str(e)
        
        return db_analysis
    
    def analyze_schema_manager(self) -> Dict[str, Any]:
        """分析Schema管理器状态"""
        print("🔍 分析Schema管理器...")
        
        schema_analysis = {
            "status": "success",
            "cache_status": {},
            "performance": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            from chatbi.database import get_schema_manager
            
            schema_manager = get_schema_manager()
            
            # 测试获取表列表
            start_time = time.time()
            tables = schema_manager.get_all_tables()
            table_query_time = time.time() - start_time
            
            schema_analysis["performance"]["table_query_time"] = table_query_time
            schema_analysis["table_count"] = len(tables)
            
            # 测试获取Schema
            start_time = time.time()
            schema = schema_manager.get_database_schema()
            schema_query_time = time.time() - start_time
            
            schema_analysis["performance"]["schema_query_time"] = schema_query_time
            schema_analysis["schema_table_count"] = len(schema.get("tables", {}))
            
            # 缓存分析
            cache_file = Path("data/knowledge_base/schema_cache.json")
            if cache_file.exists():
                cache_size = cache_file.stat().st_size
                cache_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                
                schema_analysis["cache_status"] = {
                    "exists": True,
                    "size_bytes": cache_size,
                    "size_mb": cache_size / 1024 / 1024,
                    "last_modified": cache_mtime.isoformat(),
                    "age_hours": (datetime.now() - cache_mtime).total_seconds() / 3600
                }
                
                # 缓存问题检查
                if cache_size > 10 * 1024 * 1024:  # 10MB
                    schema_analysis["issues"].append("Schema缓存文件过大")
                    schema_analysis["recommendations"].append("考虑清理Schema缓存")
                
                if schema_analysis["cache_status"]["age_hours"] > 24:
                    schema_analysis["recommendations"].append("Schema缓存较旧，建议刷新")
            else:
                schema_analysis["cache_status"]["exists"] = False
                schema_analysis["recommendations"].append("Schema缓存不存在，首次运行正常")
            
            # 性能问题检查
            if table_query_time > 2.0:
                schema_analysis["issues"].append("表查询时间过长")
                schema_analysis["recommendations"].append("检查数据库连接或清理缓存")
            
            if schema_query_time > 5.0:
                schema_analysis["issues"].append("Schema查询时间过长")
                schema_analysis["recommendations"].append("考虑优化Schema缓存策略")
        
        except Exception as e:
            schema_analysis["status"] = "error"
            schema_analysis["error"] = str(e)
        
        return schema_analysis
    
    def analyze_knowledge_base(self) -> Dict[str, Any]:
        """分析知识库状态"""
        print("🔍 分析知识库系统...")
        
        kb_analysis = {
            "status": "success",
            "enabled": False,
            "stats": {},
            "performance": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            from chatbi.knowledge_base import get_knowledge_manager
            
            kb_manager = get_knowledge_manager()
            kb_analysis["enabled"] = kb_manager.enabled
            
            if kb_manager.enabled:
                # 获取统计信息
                start_time = time.time()
                stats = kb_manager.get_stats()
                stats_query_time = time.time() - start_time
                
                kb_analysis["stats"] = stats
                kb_analysis["performance"]["stats_query_time"] = stats_query_time
                
                # 测试搜索性能
                start_time = time.time()
                search_result = kb_manager.search_knowledge("测试查询")
                search_time = time.time() - start_time
                
                kb_analysis["performance"]["search_time"] = search_time
                kb_analysis["search_result_count"] = len(search_result.similar_examples) if search_result else 0
                
                # 检查知识库目录
                kb_dir = Path("data/knowledge_base")
                if kb_dir.exists():
                    total_size = sum(f.stat().st_size for f in kb_dir.rglob('*') if f.is_file())
                    kb_analysis["storage"] = {
                        "directory_exists": True,
                        "total_size_bytes": total_size,
                        "total_size_mb": total_size / 1024 / 1024
                    }
                    
                    if total_size > 100 * 1024 * 1024:  # 100MB
                        kb_analysis["recommendations"].append("知识库存储较大，考虑定期清理")
                else:
                    kb_analysis["storage"]["directory_exists"] = False
                    kb_analysis["issues"].append("知识库目录不存在")
                
                # 性能问题检查
                if search_time > 2.0:
                    kb_analysis["issues"].append("知识库搜索时间过长")
                    kb_analysis["recommendations"].append("检查向量数据库性能或重建索引")
                
                if stats.get("total_items", 0) == 0:
                    kb_analysis["recommendations"].append("知识库为空，建议添加一些示例查询")
            else:
                kb_analysis["issues"].append("知识库未启用")
                kb_analysis["recommendations"].append("检查RAG依赖安装和API密钥配置")
        
        except Exception as e:
            kb_analysis["status"] = "error"
            kb_analysis["error"] = str(e)
        
        return kb_analysis
    
    def analyze_agents(self) -> Dict[str, Any]:
        """分析智能体状态"""
        print("🔍 分析智能体系统...")
        
        agents_analysis = {
            "status": "success",
            "agents": {},
            "performance": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            # 测试SQL生成智能体
            from chatbi.agents import get_sql_generator
            
            start_time = time.time()
            sql_generator = get_sql_generator()
            init_time = time.time() - start_time
            
            agents_analysis["agents"]["sql_generator"] = {
                "initialized": True,
                "init_time": init_time,
                "model_name": sql_generator.model_name
            }
            
            # 测试简单的SQL生成（不实际调用LLM）
            test_schema = "表: test_table\n字段: id (int), name (varchar)"
            
            # 检查其他智能体
            try:
                from chatbi.agents import get_sql_fixer
                sql_fixer = get_sql_fixer()
                agents_analysis["agents"]["sql_fixer"] = {
                    "initialized": True,
                    "model_name": sql_fixer.model_name
                }
            except Exception as e:
                agents_analysis["agents"]["sql_fixer"] = {
                    "initialized": False,
                    "error": str(e)
                }
            
            # 性能检查
            if init_time > 5.0:
                agents_analysis["issues"].append("智能体初始化时间过长")
                agents_analysis["recommendations"].append("检查模型加载或网络连接")
        
        except Exception as e:
            agents_analysis["status"] = "error"
            agents_analysis["error"] = str(e)
        
        return agents_analysis
    
    def analyze_system_resources(self) -> Dict[str, Any]:
        """分析系统资源使用"""
        print("🔍 分析系统资源...")
        
        resource_analysis = {
            "status": "success",
            "disk_usage": {},
            "memory_info": {},
            "file_counts": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            # 磁盘使用分析
            data_dir = Path("data")
            logs_dir = Path("logs")
            
            if data_dir.exists():
                data_size = sum(f.stat().st_size for f in data_dir.rglob('*') if f.is_file())
                resource_analysis["disk_usage"]["data_directory"] = {
                    "size_bytes": data_size,
                    "size_mb": data_size / 1024 / 1024
                }
            
            if logs_dir.exists():
                logs_size = sum(f.stat().st_size for f in logs_dir.rglob('*') if f.is_file())
                resource_analysis["disk_usage"]["logs_directory"] = {
                    "size_bytes": logs_size,
                    "size_mb": logs_size / 1024 / 1024
                }
                
                if logs_size > 50 * 1024 * 1024:  # 50MB
                    resource_analysis["issues"].append("日志文件过大")
                    resource_analysis["recommendations"].append("考虑清理或轮转日志文件")
            
            # 文件数量统计
            py_files = len(list(Path(".").rglob("*.py")))
            json_files = len(list(Path(".").rglob("*.json")))
            
            resource_analysis["file_counts"] = {
                "python_files": py_files,
                "json_files": json_files
            }
            
            # 检查临时文件
            temp_files = list(Path(".").rglob("*.tmp")) + list(Path(".").rglob("*~"))
            if temp_files:
                resource_analysis["issues"].append(f"发现 {len(temp_files)} 个临时文件")
                resource_analysis["recommendations"].append("清理临时文件")
        
        except Exception as e:
            resource_analysis["status"] = "error"
            resource_analysis["error"] = str(e)
        
        return resource_analysis
    
    def generate_report(self) -> str:
        """生成完整的分析报告"""
        print("\n📊 生成系统分析报告...")
        
        # 执行所有分析
        self.analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "configuration": self.analyze_configuration(),
            "database": self.analyze_database_connectivity(),
            "schema_manager": self.analyze_schema_manager(),
            "knowledge_base": self.analyze_knowledge_base(),
            "agents": self.analyze_agents(),
            "system_resources": self.analyze_system_resources()
        }
        
        # 生成报告
        report_lines = []
        report_lines.append("# ChatBI 系统分析报告")
        report_lines.append(f"生成时间: {self.analysis_results['timestamp']}")
        report_lines.append("")
        
        # 总体状态
        total_issues = 0
        total_recommendations = 0
        
        for category, analysis in self.analysis_results.items():
            if category == "timestamp":
                continue
            
            if isinstance(analysis, dict):
                total_issues += len(analysis.get("issues", []))
                total_recommendations += len(analysis.get("recommendations", []))
        
        report_lines.append("## 📋 总体状态")
        report_lines.append(f"- 发现问题: {total_issues} 个")
        report_lines.append(f"- 优化建议: {total_recommendations} 个")
        report_lines.append("")
        
        # 各模块详细分析
        for category, analysis in self.analysis_results.items():
            if category == "timestamp":
                continue
            
            category_name = {
                "configuration": "配置分析",
                "database": "数据库连接",
                "schema_manager": "Schema管理器",
                "knowledge_base": "知识库系统",
                "agents": "智能体系统",
                "system_resources": "系统资源"
            }.get(category, category)
            
            report_lines.append(f"## 🔍 {category_name}")
            
            if analysis.get("status") == "error":
                report_lines.append(f"❌ **状态**: 错误")
                report_lines.append(f"**错误信息**: {analysis.get('error', '未知错误')}")
            else:
                report_lines.append(f"✅ **状态**: 正常")
            
            # 关键指标
            if category == "database" and analysis.get("connection_status"):
                report_lines.append(f"- 表数量: {analysis.get('table_count', 0)}")
                perf = analysis.get("performance", {})
                if perf:
                    report_lines.append(f"- 连接时间: {perf.get('connection_time', 0):.3f}秒")
                    report_lines.append(f"- 查询时间: {perf.get('table_query_time', 0):.3f}秒")
            
            elif category == "knowledge_base" and analysis.get("enabled"):
                stats = analysis.get("stats", {})
                report_lines.append(f"- 知识库条目: {stats.get('total_items', 0)}")
                report_lines.append(f"- 平均评分: {stats.get('avg_rating', 0):.2f}")
                perf = analysis.get("performance", {})
                if perf.get("search_time"):
                    report_lines.append(f"- 搜索时间: {perf['search_time']:.3f}秒")
            
            elif category == "system_resources":
                disk = analysis.get("disk_usage", {})
                if disk.get("data_directory"):
                    report_lines.append(f"- 数据目录大小: {disk['data_directory']['size_mb']:.2f}MB")
                if disk.get("logs_directory"):
                    report_lines.append(f"- 日志目录大小: {disk['logs_directory']['size_mb']:.2f}MB")
            
            # 问题和建议
            issues = analysis.get("issues", [])
            if issues:
                report_lines.append("**⚠️ 发现的问题:**")
                for issue in issues:
                    report_lines.append(f"  - {issue}")
            
            recommendations = analysis.get("recommendations", [])
            if recommendations:
                report_lines.append("**💡 优化建议:**")
                for rec in recommendations:
                    report_lines.append(f"  - {rec}")
            
            report_lines.append("")
        
        # 总结和建议
        report_lines.append("## 🎯 总结和建议")
        
        if total_issues == 0:
            report_lines.append("✅ 系统运行状态良好，未发现严重问题。")
        else:
            report_lines.append(f"⚠️ 发现 {total_issues} 个问题需要关注。")
        
        if total_recommendations > 0:
            report_lines.append(f"💡 有 {total_recommendations} 个优化建议可以提升系统性能。")
        
        report_lines.append("")
        report_lines.append("## 📞 支持信息")
        report_lines.append("如需技术支持，请提供此报告和相关日志文件。")
        
        return "\n".join(report_lines)
    
    def save_report(self, report: str, filename: str = None):
        """保存报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_analysis_report_{timestamp}.md"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"📄 报告已保存到: {filename}")
        return filename

def main():
    """主函数"""
    print("🚀 ChatBI 系统分析器")
    print("=" * 50)
    
    analyzer = ChatBISystemAnalyzer()
    
    try:
        # 生成报告
        report = analyzer.generate_report()
        
        # 保存报告
        filename = analyzer.save_report(report)
        
        # 显示摘要
        print("\n" + "=" * 50)
        print("📊 分析完成！")
        
        # 统计问题和建议
        total_issues = 0
        total_recommendations = 0
        
        for category, analysis in analyzer.analysis_results.items():
            if category == "timestamp":
                continue
            if isinstance(analysis, dict):
                total_issues += len(analysis.get("issues", []))
                total_recommendations += len(analysis.get("recommendations", []))
        
        print(f"🔍 发现问题: {total_issues} 个")
        print(f"💡 优化建议: {total_recommendations} 个")
        print(f"📄 详细报告: {filename}")
        
        # 显示关键问题
        if total_issues > 0:
            print("\n⚠️ 关键问题:")
            for category, analysis in analyzer.analysis_results.items():
                if category == "timestamp":
                    continue
                issues = analysis.get("issues", [])
                for issue in issues[:3]:  # 只显示前3个
                    print(f"  - {issue}")
        
    except Exception as e:
        print(f"❌ 分析过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()