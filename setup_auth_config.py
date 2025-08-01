#!/usr/bin/env python3
"""
ChatBI认证系统配置设置脚本
帮助用户快速配置认证系统
"""

import os
import secrets
from pathlib import Path

def generate_secure_key(length=32):
    """生成安全的密钥"""
    return secrets.token_urlsafe(length)

def create_auth_config():
    """创建认证配置文件"""
    print("🔧 ChatBI认证系统配置向导")
    print("=" * 50)
    
    # 生成密钥
    jwt_key = generate_secure_key(32)
    web_key = generate_secure_key(32)
    
    print(f"✅ 已生成JWT密钥: {jwt_key[:16]}...")
    print(f"✅ 已生成Web密钥: {web_key[:16]}...")
    
    # 获取用户输入
    print("\n📋 请配置以下参数（直接回车使用默认值）:")
    
    # 会话配置
    session_timeout = input("会话超时时间（秒，默认3600）: ").strip() or "3600"
    max_sessions = input("每用户最大会话数（默认5）: ").strip() or "5"
    
    # 密码配置
    password_min_length = input("密码最小长度（默认6）: ").strip() or "6"
    require_complexity = input("是否要求密码复杂度（y/n，默认n）: ").strip().lower()
    require_complexity = "true" if require_complexity in ['y', 'yes'] else "false"
    
    # 权限配置
    default_schemas = input("默认schema访问权限（逗号分隔，默认public）: ").strip() or "public"
    public_schemas = input("公共schema（逗号分隔，默认public）: ").strip() or "public"
    admin_schemas = input("管理员schema（逗号分隔，默认admin,system）: ").strip() or "admin,system"
    
    # API配置
    dashscope_key = input("DashScope API密钥（可选）: ").strip() or ""
    
    # 生成配置内容
    config_content = f"""# ChatBI认证系统配置文件
# 由setup_auth_config.py自动生成

# JWT配置（必需）
AUTH_JWT_SECRET_KEY={jwt_key}

# Web配置
SECRET_KEY={web_key}

# 会话配置
AUTH_SESSION_TIMEOUT={session_timeout}
AUTH_SESSION_CLEANUP_INTERVAL=300
AUTH_MAX_SESSIONS_PER_USER={max_sessions}

# 登录安全配置
AUTH_MAX_LOGIN_ATTEMPTS=5
AUTH_LOCKOUT_DURATION=900
AUTH_LOCKOUT_ENABLED=true

# 密码配置
AUTH_PASSWORD_MIN_LENGTH={password_min_length}
AUTH_PASSWORD_MAX_LENGTH=128
AUTH_REQUIRE_PASSWORD_COMPLEXITY={require_complexity}
AUTH_PASSWORD_HISTORY_COUNT=5

# 权限配置
PERM_DEFAULT_SCHEMA_ACCESS={default_schemas}
PERM_PUBLIC_SCHEMAS={public_schemas}
PERM_ADMIN_SCHEMAS={admin_schemas}
PERM_SCHEMA_ISOLATION_ENABLED=true
PERM_STRICT_PERMISSION_CHECK=true
PERM_INHERIT_ADMIN_PERMISSIONS=true

# 权限缓存配置
PERM_CACHE_ENABLED=true
PERM_CACHE_TTL=300
PERM_CACHE_SIZE=1000

# 审计配置
AUTH_ENABLE_AUDIT_LOGGING=true
AUTH_AUDIT_LOG_RETENTION_DAYS=90

# 安全配置
AUTH_ENABLE_CSRF_PROTECTION=true
AUTH_ENABLE_SESSION_FIXATION_PROTECTION=true
AUTH_SECURE_COOKIES=false

# API配置（可选）
DASHSCOPE_API_KEY={dashscope_key}
"""
    
    # 写入配置文件
    config_file = Path(".env.auth")
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print(f"\n✅ 配置文件已创建: {config_file}")
    print("\n🚀 现在您可以运行以下命令启动应用:")
    print("   python start_chatbi_with_auth.py")
    
    print("\n📖 配置说明:")
    print("- JWT密钥用于用户会话加密，请妥善保管")
    print("- Web密钥用于Web应用安全，请妥善保管")
    print("- 生产环境请修改默认配置以提高安全性")
    print("- 如需修改配置，请直接编辑 .env.auth 文件")

def main():
    """主函数"""
    try:
        create_auth_config()
    except KeyboardInterrupt:
        print("\n\n❌ 配置已取消")
    except Exception as e:
        print(f"\n❌ 配置失败: {str(e)}")

if __name__ == "__main__":
    main()