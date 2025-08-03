# ChatBI 快速启动指南

## 🚀 一键启动

### 1. 环境准备
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp config.env.example .env
# 编辑 .env 文件，配置数据库连接和API密钥
```

### 2. 启动应用
```bash
# 启动主应用（推荐）
python start_login_gate.py

# 访问地址
http://127.0.0.1:7861
```

## 🔐 首次使用

### 1. 用户注册
- 访问应用后会看到登录界面
- 点击"注册"标签页
- 填写工号、密码、邮箱等信息
- 点击"注册"按钮

### 2. 用户登录
- 在"登录"标签页输入工号和密码
- 点击"登录"按钮
- 登录成功后进入主应用界面

## 💬 智能查询

### 1. 基本查询
在"智能查询"标签页中：
- 输入自然语言问题，如："显示用户总数"
- 点击"发送"按钮
- 系统会自动生成SQL、执行查询、分析数据、生成图表

### 2. 查询选项
- **自动生成可视化**: 自动创建图表
- **启用数据分析**: AI分析查询结果
- **分析级别**: basic/standard/detailed

### 3. 用户反馈
- 对满意的查询结果点击"👍 添加到知识库"
- 可选择添加反馈描述
- 系统会学习并改进后续查询

## 🧠 知识库管理

### 1. 查看知识库
在"SQL知识库"标签页中：
- 查看已保存的查询历史
- 浏览问题-SQL对应关系
- 查看知识库统计信息

### 2. 管理条目
- **添加新条目**: 手动添加问题和SQL
- **编辑条目**: 修改现有的知识库条目
- **删除条目**: 删除不需要的条目

### 3. 数据导入导出
- **导出知识库**: 备份知识库数据
- **导入知识库**: 恢复或迁移知识库

## 📝 表信息维护

### 1. 表信息管理
在"表信息维护"标签页中：
- 选择要管理的数据库表
- 编辑表的业务名称和描述
- 设置表的业务分类

### 2. 字段信息管理
- 加载表的字段列表
- 编辑字段的业务名称和描述
- 查看字段的数据示例
- 系统会自动保存修改

## ℹ️ 系统信息

### 1. 系统状态
- 测试数据库连接
- 刷新Schema缓存
- 获取详细的Schema信息

### 2. 知识库统计
- 查看知识库条目数量
- 了解系统使用情况

## 🔧 配置说明

### 数据库配置
在 `.env` 文件中配置：
```env
# PostgreSQL
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=your_database
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password

# MySQL
DATABASE_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=your_database
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
```

### AI模型配置
```env
# DashScope API
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 模型设置
LLM_MODEL_NAME=qwen-max
LLM_CODER_MODEL=qwen-coder-plus
EMBEDDING_MODEL=text-embedding-v3
```

### 认证配置
```env
# 会话设置
AUTH_SESSION_TIMEOUT=3600
AUTH_MAX_SESSIONS_PER_USER=5

# 密码策略
AUTH_PASSWORD_MIN_LENGTH=8
AUTH_REQUIRE_PASSWORD_COMPLEXITY=true

# 安全设置
AUTH_ENABLE_CSRF_PROTECTION=true
AUTH_ENABLE_AUDIT_LOGGING=true
```

## 🛠️ 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务是否启动
   - 验证连接参数是否正确
   - 确认用户权限是否足够

2. **AI模型调用失败**
   - 检查API密钥是否正确
   - 验证网络连接是否正常
   - 确认模型名称是否正确

3. **登录失败**
   - 检查用户名和密码是否正确
   - 确认用户是否已注册
   - 查看是否有账户锁定

4. **查询结果为空**
   - 检查SQL语句是否正确
   - 验证数据库中是否有数据
   - 确认用户权限是否足够

### 日志查看
系统会在控制台输出详细的运行日志，包括：
- 用户操作记录
- SQL执行过程
- 错误信息详情
- 性能统计信息

### 获取帮助
如遇到问题，可以：
1. 查看控制台日志信息
2. 检查配置文件设置
3. 参考项目文档
4. 提交Issue反馈

## 🎯 最佳实践

### 1. 查询优化
- 使用具体明确的问题描述
- 避免过于复杂的查询逻辑
- 合理使用查询选项

### 2. 知识库维护
- 及时对满意的查询结果点赞
- 定期清理无用的知识库条目
- 添加详细的描述信息

### 3. 权限管理
- 使用强密码策略
- 定期更换密码
- 及时登出系统

### 4. 系统维护
- 定期备份知识库数据
- 监控系统运行状态
- 及时更新配置信息
