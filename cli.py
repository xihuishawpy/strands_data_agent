#!/usr/bin/env python3
"""
ChatBI 命令行接口
提供简单的命令行交互方式
"""

import sys
import argparse
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from chatbi import ChatBIOrchestrator
from chatbi.config import config

def print_banner():
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                         ChatBI                               ║
║                 企业级智能数据查询应用                        ║
║                   基于 Strands Agents                        ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_result(result):
    """格式化打印查询结果"""
    print("\n" + "="*60)
    print(f"📋 问题: {result.question}")
    print("="*60)
    
    if not result.success:
        print(f"❌ 错误: {result.error}")
        return
    
    print(f"✅ 执行时间: {result.execution_time:.2f}秒")
    
    if result.sql_query:
        print(f"\n🔧 生成的SQL:")
        print(f"```sql\n{result.sql_query}\n```")
    
    if result.data:
        print(f"\n📊 查询结果 (共{len(result.data)}行):")
        
        # 显示表格数据
        if result.metadata and "columns" in result.metadata:
            columns = result.metadata["columns"]
        else:
            columns = list(result.data[0].keys()) if result.data else []
        
        # 打印表头
        print("-" * 80)
        header = " | ".join(f"{col:<15}" for col in columns)
        print(header)
        print("-" * 80)
        
        # 打印数据行（最多显示10行）
        for i, row in enumerate(result.data[:10]):
            row_str = " | ".join(f"{str(row.get(col, '')):<15}" for col in columns)
            print(row_str)
        
        if len(result.data) > 10:
            print(f"... ({len(result.data) - 10} 行未显示)")
        print("-" * 80)
    
    if result.analysis:
        print(f"\n📈 数据分析:")
        print(result.analysis)
    
    if result.chart_info:
        print(f"\n📊 可视化:")
        print(f"图表类型: {result.chart_info.get('chart_type')}")
        print(f"文件路径: {result.chart_info.get('file_path')}")

def interactive_mode():
    """交互式模式"""
    print_banner()
    print("进入交互式模式。输入 'exit' 或 'quit' 退出，'help' 查看帮助。\n")
    
    orchestrator = ChatBIOrchestrator()
    
    while True:
        try:
            question = input("ChatBI> ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['exit', 'quit']:
                print("再见！")
                break
            
            if question.lower() == 'help':
                print_help()
                continue
            
            if question.lower() == 'schema':
                schema_info = orchestrator.get_schema_info()
                print("\n📋 数据库Schema信息:")
                print(json.dumps(schema_info, ensure_ascii=False, indent=2))
                continue
            
            if question.lower() == 'refresh':
                print("正在刷新Schema缓存...")
                success = orchestrator.refresh_schema()
                if success:
                    print("✅ Schema缓存刷新成功")
                else:
                    print("❌ Schema缓存刷新失败")
                continue
            
            # 处理查询
            print("🤔 正在思考...")
            result = orchestrator.query(question)
            print_result(result)
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 系统错误: {str(e)}")

def print_help():
    """打印帮助信息"""
    help_text = """
📚 ChatBI 命令行帮助

基本命令:
  help          - 显示此帮助信息
  schema        - 显示数据库Schema信息
  refresh       - 刷新Schema缓存
  exit/quit     - 退出程序

查询示例:
  "显示所有用户"
  "上个月销售额最高的产品是什么？"
  "统计每个月的订单数量"
  "查看用户年龄分布"

高级功能:
  - 自动SQL生成
  - 智能数据分析
  - 自动图表生成
  - 错误自动修复
    """
    print(help_text)

def single_query_mode(question: str, output_file: str = None):
    """单次查询模式"""
    orchestrator = ChatBIOrchestrator()
    
    print(f"🤔 正在处理查询: {question}")
    result = orchestrator.query(question)
    
    if output_file:
        # 保存结果到文件
        output_data = {
            "question": result.question,
            "success": result.success,
            "sql_query": result.sql_query,
            "data": result.data,
            "analysis": result.analysis,
            "chart_info": result.chart_info,
            "error": result.error,
            "execution_time": result.execution_time,
            "metadata": result.metadata
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"📄 结果已保存到: {output_file}")
    
    print_result(result)

def validate_config():
    """验证配置"""
    validation = config.validate()
    
    if not validation["valid"]:
        print("❌ 配置验证失败:")
        for error in validation["errors"]:
            print(f"  - {error}")
        return False
    
    if validation["warnings"]:
        print("⚠️  配置警告:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")
    
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ChatBI - 企业级智能数据查询应用",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py                                    # 交互式模式
  python cli.py "显示所有用户"                       # 单次查询
  python cli.py "统计订单数量" --output result.json  # 保存结果到文件
  python cli.py --validate                        # 验证配置
        """
    )
    
    parser.add_argument(
        "question", 
        nargs="?", 
        help="要查询的问题（如果不提供则进入交互式模式）"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（JSON格式）"
    )
    
    parser.add_argument(
        "--validate", 
        action="store_true",
        help="验证配置并退出"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="显示详细日志"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 验证配置
    if args.validate:
        print("🔍 验证配置...")
        if validate_config():
            print("✅ 配置验证通过")
        sys.exit(0)
    
    # 验证配置（静默）
    if not validate_config():
        print("\n请检查配置文件后重试。")
        sys.exit(1)
    
    try:
        if args.question:
            # 单次查询模式
            single_query_mode(args.question, args.output)
        else:
            # 交互式模式
            interactive_mode()
    
    except Exception as e:
        print(f"❌ 程序错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 