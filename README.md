# ChatBI - 企业级智能数据查询应用

基于 Strands Agents 框架构建的企业级 ChatBI 智能数据查询应用，支持通过自然语言查询 PostgreSQL、MySQL 等数据库，自动生成 SQL、执行查询、数据分析和可视化。

## 功能特性

- 🤖 **智能SQL生成**: 将自然语言转换为准确的SQL查询
- 🔒 **安全执行**: 使用只读权限确保数据安全
- 📊 **智能分析**: AI驱动的数据解读和洞察
- 📈 **数据可视化**: 自动生成图表和可视化
- 🏢 **企业级**: 支持多数据库、Schema管理、权限控制
- 🔄 **多智能体协作**: 基于"智能体即工具"模式的架构

## 架构设计

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   用户接口       │───▶│   主控智能体     │───▶│   数据库连接     │
│   (Web UI)      │    │ (Orchestrator)  │    │   (只读权限)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  数据可视化工具  │◀───│  SQL生成智能体   │───▶│   Schema知识库   │
│                │    │                │    │                │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │
        ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│  数据分析智能体  │    │   SQL执行工具    │
│                │    │                │
└─────────────────┘    └─────────────────┘
```

## 快速开始

### 1. 环境设置

```bash
# 克隆项目
git clone <repository-url>
cd strands_data_agent

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp config.env.example .env
# 编辑 .env 文件，配置您的数据库连接和API密钥
```

### 2. 数据库配置

确保您的数据库用户具有**只读权限**：

```sql
-- PostgreSQL 示例
CREATE USER chatbi_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE your_database TO chatbi_readonly;
GRANT USAGE ON SCHEMA public TO chatbi_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbi_readonly;
```

### 3. 启动应用

```bash
# 启动 Web API
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用命令行接口
python cli.py "上个月销售额最高的产品是什么？"
```

### 4. 使用示例

```python
from chatbi import ChatBIOrchestrator

# 创建ChatBI实例
chatbi = ChatBIOrchestrator()

# 查询示例
result = chatbi.query("显示过去6个月每月的销售趋势")
print(result)
```

## 项目结构

```
strands_data_agent/
├── app/                     # Web应用
│   ├── __init__.py
│   ├── main.py             # FastAPI主应用
│   ├── api/                # API路由
│   ├── models/             # 数据模型
│   └── templates/          # 前端模板
├── chatbi/                 # 核心ChatBI模块
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── database/           # 数据库连接和工具
│   ├── agents/             # 智能体定义
│   ├── tools/              # 工具函数
│   ├── knowledge/          # 知识库管理
│   └── orchestrator.py     # 主控智能体
├── data/                   # 数据目录
├── logs/                   # 日志目录
├── tests/                  # 测试文件
├── cli.py                  # 命令行接口
├── requirements.txt        # 依赖文件
└── README.md              # 项目文档
```

## 安全注意事项

1. **只读权限**: 确保数据库用户只有SELECT权限
2. **输入验证**: 所有用户输入都经过验证和清理
3. **SQL注入防护**: 使用参数化查询和安全检查
4. **访问控制**: 实现用户认证和授权机制

## 配置说明

详细的配置选项请参考 `config.env.example` 文件。

## 开发指南

### 添加新的数据库支持

1. 在 `chatbi/database/connectors.py` 中添加新的连接器
2. 更新 `chatbi/database/schema_manager.py` 中的Schema提取逻辑
3. 测试连接和查询功能

### 自定义智能体

```python
from strands import Agent
from chatbi.agents.base import BaseAgent

class CustomAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Custom_Analysis_Agent",
            system_prompt="您的自定义系统提示..."
        )
```

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交 Issues 和 Pull Requests！

## 联系方式

- 项目主页: [链接]
- 文档: [链接]
- 问题反馈: [链接] 