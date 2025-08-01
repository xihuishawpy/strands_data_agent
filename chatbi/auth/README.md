# ChatBI 认证模块

ChatBI认证模块提供完整的用户认证、权限管理和会话管理功能，支持基于工号的用户注册控制和数据库schema级别的访问权限管理。

## 功能特性

### 用户管理
- 基于工号的用户注册和登录
- 工号白名单控制注册权限
- 密码强度验证和安全存储
- 用户信息管理

### 权限管理
- Schema级别的访问权限控制
- 支持读取、写入、管理员三种权限级别
- 权限继承和缓存机制
- 灵活的权限配置

### 会话管理
- 安全的会话令牌生成和验证
- 会话超时和自动清理
- 多设备会话支持
- 会话活动跟踪

### 安全特性
- 密码加密存储（bcrypt）
- JWT令牌认证
- 登录失败锁定机制
- 完整的审计日志
- CSRF防护支持

## 快速开始

### 1. 安装依赖

```bash
pip install bcrypt pyjwt
```

### 2. 配置环境变量

复制 `config.env.example` 到 `.env` 并配置认证相关参数：

```bash
# 认证配置
AUTH_JWT_SECRET_KEY=your_jwt_secret_key_here
AUTH_SESSION_TIMEOUT=3600
AUTH_MAX_LOGIN_ATTEMPTS=5
AUTH_PASSWORD_MIN_LENGTH=8

# 权限配置
PERM_SCHEMA_ISOLATION_ENABLED=true
PERM_DEFAULT_SCHEMA_ACCESS=public,common
```

### 3. 初始化数据库

```bash
python init_auth.py init-db
```

### 4. 创建管理员用户

```bash
python init_auth.py create-admin
```

### 5. 添加允许注册的工号

```bash
python init_auth.py add-employee
```

## 数据库结构

认证模块使用以下数据表：

- `users` - 用户信息表
- `allowed_employees` - 允许注册工号表
- `user_permissions` - 用户权限表
- `user_sessions` - 用户会话表
- `audit_logs` - 审计日志表
- `login_attempts` - 登录尝试记录表

## API 使用示例

### 用户管理

```python
from chatbi.auth import UserManager
from chatbi.config import config

# 创建用户管理器
user_manager = UserManager(config.database)

# 用户注册
result = user_manager.register_user("EMP001", "password123", "user@example.com")

# 用户登录
auth_result = user_manager.authenticate_user("EMP001", "password123")
```

### 权限管理

```python
from chatbi.auth import PermissionManager

# 创建权限管理器
perm_manager = PermissionManager(config.database)

# 分配权限
perm_manager.assign_schema_permission("user_id", "schema_name", "read")

# 检查权限
has_access = perm_manager.check_schema_access("user_id", "schema_name")
```

### 会话管理

```python
from chatbi.auth import SessionManager

# 创建会话管理器
session_manager = SessionManager(config.database)

# 创建会话
session_token = session_manager.create_session("user_id", "192.168.1.1")

# 验证会话
session_result = session_manager.validate_session(session_token)
```

## 配置选项

### 认证配置 (AuthConfig)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `session_timeout` | 3600 | 会话超时时间（秒） |
| `max_login_attempts` | 5 | 最大登录尝试次数 |
| `lockout_duration` | 900 | 账户锁定时间（秒） |
| `password_min_length` | 8 | 密码最小长度 |
| `jwt_secret_key` | "" | JWT密钥 |
| `enable_audit_logging` | true | 启用审计日志 |

### 权限配置 (PermissionConfig)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `schema_isolation_enabled` | true | 启用schema隔离 |
| `strict_permission_check` | true | 严格权限检查 |
| `permission_cache_ttl` | 300 | 权限缓存TTL（秒） |
| `default_schema_access` | [] | 默认schema访问权限 |

## 命令行工具

认证模块提供了命令行工具用于管理：

```bash
# 初始化数据库
python init_auth.py init-db

# 创建管理员用户
python init_auth.py create-admin

# 添加允许注册的工号
python init_auth.py add-employee

# 查看数据库状态
python init_auth.py status

# 列出允许注册的工号
python init_auth.py list-employees
```

## 安全最佳实践

1. **密钥管理**
   - 使用强随机密钥作为JWT密钥
   - 定期轮换密钥
   - 不要在代码中硬编码密钥

2. **密码策略**
   - 启用密码复杂度要求
   - 设置合适的密码长度限制
   - 考虑密码过期策略

3. **会话安全**
   - 设置合理的会话超时时间
   - 启用会话固定攻击防护
   - 定期清理过期会话

4. **权限控制**
   - 遵循最小权限原则
   - 定期审查用户权限
   - 启用审计日志记录

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置是否正确
   - 确认数据库服务是否运行
   - 验证网络连接

2. **迁移失败**
   - 检查数据库权限
   - 查看迁移日志
   - 确认数据库版本兼容性

3. **认证失败**
   - 检查JWT密钥配置
   - 验证用户状态
   - 查看审计日志

### 日志查看

认证模块的日志记录在配置的日志文件中，可以通过以下方式查看：

```bash
# 查看最新日志
tail -f logs/chatbi.log

# 搜索认证相关日志
grep "auth" logs/chatbi.log
```

## 开发指南

### 扩展认证模块

1. **添加新的认证方式**
   - 继承 `AuthenticationMiddleware` 类
   - 实现自定义认证逻辑
   - 注册到认证管道

2. **自定义权限检查**
   - 继承 `PermissionManager` 类
   - 实现自定义权限逻辑
   - 更新权限配置

3. **添加新的数据模型**
   - 在 `models.py` 中定义数据模型
   - 创建对应的数据库迁移
   - 更新数据库操作类

### 测试

```bash
# 运行认证模块测试
python -m pytest tests/test_auth.py -v

# 运行特定测试
python -m pytest tests/test_auth.py::test_user_registration -v
```

## 许可证

本模块遵循项目的整体许可证。