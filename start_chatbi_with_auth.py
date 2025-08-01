#!/usr/bin/env python3
"""
启动带认证功能的ChatBI应用
确保认证系统正确初始化
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载认证配置文件
auth_env_file = Path(__file__).parent / ".env.auth"
if auth_env_file.exists():
    load_dotenv(auth_env_file)
    print(f"✅ 已加载认证配置文件: {auth_env_file}")
else:
    print(f"⚠️ 认证配置文件不存在: {auth_env_file}")
    print("将使用默认配置，某些功能可能无法正常工作")

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def check_and_fix_config():
    """检查并修复配置问题"""
    print("🔧 检查认证配置...")
    
    # 检查JWT密钥
    jwt_key = os.getenv("AUTH_JWT_SECRET_KEY", "")
    if not jwt_key or jwt_key == "your-super-secret-jwt-key-change-this-in-production-12345678901234567890":
        print("⚠️ JWT密钥未设置或使用默认值")
        # 生成一个临时的JWT密钥
        import secrets
        temp_jwt_key = secrets.token_urlsafe(32)
        os.environ["AUTH_JWT_SECRET_KEY"] = temp_jwt_key
        print(f"✅ 已生成临时JWT密钥（生产环境请设置固定密钥）")
    
    # 检查Web密钥
    web_key = os.getenv("SECRET_KEY", "")
    if not web_key or web_key == "your-web-secret-key-change-this-in-production-abcdefghijklmnopqrstuvwxyz":
        print("⚠️ Web密钥未设置或使用默认值")
        # 生成一个临时的Web密钥
        import secrets
        temp_web_key = secrets.token_urlsafe(32)
        os.environ["SECRET_KEY"] = temp_web_key
        print(f"✅ 已生成临时Web密钥（生产环境请设置固定密钥）")
    
    # 设置默认schema权限
    if not os.getenv("PERM_DEFAULT_SCHEMA_ACCESS"):
        os.environ["PERM_DEFAULT_SCHEMA_ACCESS"] = "public"
        print("✅ 已设置默认schema访问权限: public")
    
    print("✅ 配置检查完成")

def initialize_auth_system():
    """初始化认证系统"""
    try:
        # 先检查和修复配置
        check_and_fix_config()
        
        from chatbi.config import config
        from chatbi.auth.config import get_auth_config, validate_all_configs
        from chatbi.auth.database import AuthDatabase
        from chatbi.auth.migrations.migration_manager import MigrationManager
        
        # 验证配置
        validation_result = validate_all_configs()
        if validation_result["warnings"]:
            print("⚠️ 配置警告:")
            for warning in validation_result["warnings"]:
                print(f"- {warning}")
        
        if not validation_result["valid"]:
            print("❌ 配置验证失败:")
            for error in validation_result["errors"]:
                print(f"- {error}")
            print("\n💡 提示: 请检查 .env.auth 文件中的配置")
            return False
        
        # 获取数据库配置（使用主配置中的数据库配置）
        database_config = config.database
        
        # 初始化认证数据库
        auth_db = AuthDatabase(database_config)
        
        # 运行数据库迁移
        migration_manager = MigrationManager(database_config)
        migration_manager.run_migrations()
        
        print("✅ 认证系统初始化成功")
        return True
        
    except Exception as e:
        print(f"❌ 认证系统初始化失败: {str(e)}")
        print("请检查认证配置和数据库连接")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    setup_logging()
    
    print("🚀 启动ChatBI带认证功能的应用...")
    
    # 初始化认证系统
    if not initialize_auth_system():
        print("❌ 认证系统初始化失败，退出")
        sys.exit(1)
    
    try:
        from gradio_app_chat import create_authenticated_chatbi_app
        from chatbi.config import config
        
        # 创建应用
        app = create_authenticated_chatbi_app()
        
        print(f"📊 数据库类型: {config.database.type}")
        print(f"🤖 AI模型: {config.llm.model_name}")
        print("🔐 认证功能: 已启用")
        print("📋 功能说明:")
        print("  - 用户认证和权限管理")
        print("  - 智能数据查询和分析")
        print("  - 自动可视化生成")
        print("  - 查询反馈和优化")
        print()
        print("🌐 访问地址: http://localhost:7860")
        print("📖 使用说明:")
        print("  1. 在'用户认证'标签页中登录或注册")
        print("  2. 登录后在'智能查询'标签页进行查询")
        print("  3. 系统会根据权限过滤数据访问")
        
        # 启动应用
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            debug=False,
            show_error=True
        )
        
    except Exception as e:
        print(f"❌ 应用启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()