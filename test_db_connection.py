#!/usr/bin/env python3
"""
数据库连接测试脚本
用于验证数据库配置和连接是否正常
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_database_connection():
    """测试数据库连接"""
    print("🔍 开始测试数据库连接...")
    
    try:
        # 导入配置
        from chatbi.config import config
        print(f"✅ 配置加载成功")
        
        # 验证配置
        validation = config.validate()
        print(f"📋 配置验证结果:")
        print(f"   - 有效: {validation['valid']}")
        
        if validation['errors']:
            print(f"   - 错误: {validation['errors']}")
            return False
            
        if validation['warnings']:
            print(f"   - 警告: {validation['warnings']}")
        
        # 显示数据库配置信息
        print(f"\n📊 数据库配置信息:")
        print(f"   - 类型: {config.database.type}")
        print(f"   - 主机: {config.database.host}")
        print(f"   - 端口: {config.database.port}")
        print(f"   - 数据库: {config.database.database}")
        print(f"   - 用户: {config.database.username}")
        print(f"   - 连接字符串: {config.database.connection_string}")
        
        # 测试数据库连接
        print(f"\n🔌 测试数据库连接...")
        from chatbi.database.connectors import get_database_connector
        
        connector = get_database_connector()
        print(f"✅ 数据库连接器创建成功: {type(connector).__name__}")
        
        # 尝试连接
        connected = connector.connect()
        
        if connected:
            print(f"✅ 数据库连接成功！")
            
            # 测试基本查询
            print(f"\n🧪 执行基本测试查询...")
            test_result = connector.execute_query("SELECT 1 as test_column")
            
            if test_result.get("success"):
                print(f"✅ 测试查询执行成功")
                print(f"   - 结果: {test_result.get('data', [])}")
            else:
                print(f"❌ 测试查询失败: {test_result.get('error')}")
                return False
            
            # 获取表列表
            print(f"\n📋 获取数据库表列表...")
            tables = connector.get_tables()
            
            if tables:
                print(f"✅ 找到 {len(tables)} 个表:")
                for i, table in enumerate(tables[:10]):  # 只显示前10个
                    print(f"   {i+1}. {table}")
                if len(tables) > 10:
                    print(f"   ... 还有 {len(tables) - 10} 个表")
            else:
                print(f"⚠️  数据库中没有找到表，可能是：")
                print(f"   - 数据库为空")
                print(f"   - 用户权限不足")
                print(f"   - Schema配置问题")
            
            # 断开连接
            connector.disconnect()
            print(f"✅ 数据库连接已断开")
            
            return True
            
        else:
            print(f"❌ 数据库连接失败")
            return False
            
    except ImportError as e:
        print(f"❌ 导入模块失败: {str(e)}")
        print(f"   请确保已安装所有依赖: pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        print(f"   错误类型: {type(e).__name__}")
        return False

def test_chatbi_initialization():
    """测试ChatBI系统初始化"""
    print(f"\n🚀 测试ChatBI系统初始化...")
    
    try:
        from chatbi import ChatBIOrchestrator
        
        print(f"✅ 正在初始化ChatBI主控智能体...")
        orchestrator = ChatBIOrchestrator()
        
        print(f"✅ ChatBI主控智能体初始化成功")
        
        # 测试Schema管理器
        print(f"\n📋 测试Schema管理器...")
        schema_summary = orchestrator.schema_manager.get_schema_summary()
        
        if schema_summary and schema_summary != "无法获取数据库Schema信息":
            print(f"✅ Schema信息获取成功")
            print(f"   前200字符: {schema_summary[:200]}...")
        else:
            print(f"⚠️  Schema信息获取失败或为空")
        
        return True
        
    except Exception as e:
        print(f"❌ ChatBI初始化失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 ChatBI 数据库连接测试")
    print("=" * 60)
    
    # 检查环境变量文件
    env_files = [".env", "config.env.example"]
    env_found = False
    
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"📁 找到环境配置文件: {env_file}")
            env_found = True
            break
    
    if not env_found:
        print(f"⚠️  未找到环境配置文件，将使用默认配置")
        print(f"   建议创建 .env 文件并配置数据库连接信息")
    
    # 测试数据库连接
    db_success = test_database_connection()
    
    if db_success:
        # 测试ChatBI系统
        chatbi_success = test_chatbi_initialization()
        
        if chatbi_success:
            print(f"\n🎉 所有测试通过！ChatBI系统可以正常使用")
            print(f"\n📖 接下来您可以:")
            print(f"   1. 使用命令行: python cli.py")
            print(f"   2. 启动Web服务: python app/main.py")
            print(f"   3. 访问API文档: http://localhost:8000/docs")
        else:
            print(f"\n❌ ChatBI系统初始化失败，请检查配置")
            sys.exit(1)
    else:
        print(f"\n❌ 数据库连接测试失败")
        print(f"\n🔧 排查建议:")
        print(f"   1. 检查 .env 文件中的数据库配置")
        print(f"   2. 确保数据库服务正在运行")
        print(f"   3. 验证用户名和密码")
        print(f"   4. 检查网络连接和防火墙设置")
        print(f"   5. 确保已安装相应的数据库驱动")
        sys.exit(1)

if __name__ == "__main__":
    main() 