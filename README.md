# ChatBI - 企业级智能数据查询应用

基于 Strands Agents 框架构建的企业级 ChatBI 智能数据查询应用，支持通过自然语言查询 PostgreSQL、MySQL 等数据库，自动生成 SQL、执行查询、数据分析和可视化。

## 🌟 核心特性

- 🔐 **登录门禁系统**: 完整的用户认证和权限管理
- 🤖 **智能SQL生成**: 将自然语言转换为准确的SQL查询
- 🧠 **RAG知识库**: 基于用户反馈的SQL知识库，提升查询准确性
- 🔒 **安全执行**: 使用只读权限确保数据安全
- 📊 **智能分析**: AI驱动的数据解读和洞察
- 📈 **数据可视化**: 自动生成图表和可视化
- 💬 **对话式交互**: 人机对话式的数据查询体验
- 👍 **用户反馈**: 支持点赞机制，持续改进AI性能
- 🏢 **企业级**: 支持多数据库、Schema管理、权限控制
- 🔄 **多智能体协作**: 基于"智能体即工具"模式的架构

## 🏗️ 系统架构

### 整体架构图
系统采用分层架构设计，包含用户界面层、应用层、认证系统、智能体层、知识库系统、数据库层和工具层。

### 数据处理流程
1. **用户认证** → 登录门禁验证用户身份
2. **查询输入** → 用户输入自然语言问题
3. **RAG检索** → 智能搜索历史查询知识库
4. **SQL生成** → AI生成或使用缓存的SQL查询
5. **权限过滤** → 基于用户权限过滤数据访问
6. **数据分析** → AI分析查询结果
7. **可视化** → 自动生成图表和可视化
8. **用户反馈** → 收集反馈优化知识库

## 🚀 快速开始

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
# 🔥 启动主应用（推荐）- 登录门禁版
python start_login_gate.py
# 访问 http://127.0.0.1:7861

# 或者启动界面选择器
python start_gradio.py
# 选择不同的界面模式

# 或者直接启动对话式界面
python start_chat_ui.py

# 使用命令行接口
python cli.py "统计每个表的记录数"
```

### 4. 应用特色

- **🔐 登录门禁**: 用户必须先登录才能访问应用功能
- **🎨 美观界面**: 全屏登录界面，现代化UI设计
- **💬 智能对话**: 自然语言查询，AI自动生成SQL
- **📊 自动可视化**: 智能选择图表类型，生成可视化
- **🧠 知识库学习**: RAG技术，基于用户反馈持续改进
- **🔒 权限控制**: 基于用户角色的数据访问控制

### 5. 完整查询流程

ChatBI 采用**智能化五步流程**：

```
🚀 用户问题 
    ↓
📋 Schema获取 → 分析数据库结构，找到相关表和字段
    ↓  
🔧 SQL生成 → AI智能生成准确的SQL查询语句
    ↓
⚡ SQL执行 → 安全执行SQL，支持自动错误修复
    ↓
🔍 数据分析 → AI分析结果，提供洞察和建议
    ↓
🎨 可视化 → 自动选择图表类型，生成可视化
```

### 6. SQL知识库功能

ChatBI集成了先进的RAG（检索增强生成）技术，通过用户反馈持续改进SQL生成质量：

#### 🧠 智能检索匹配
- **语义搜索**: 基于向量相似度匹配历史查询
- **Q-Q相似度**: 计算问题间的语义相似度
- **智能缓存**: 高相似度查询直接使用历史SQL

#### 👍 用户反馈机制
- **点赞收集**: 用户对满意结果进行点赞
- **知识积累**: 点赞的Q-SQL对存储到向量数据库
- **质量提升**: 基于反馈数据持续优化生成效果

#### 🔄 RAG工作流程
```
用户提问 → 向量检索 → 相似度判断
    ↓
高相似度 → 直接返回缓存SQL
    ↓
中相似度 → 使用相似示例辅助生成
    ↓
低相似度 → 常规SQL生成流程
```

### 7. 使用示例

```python
from chatbi import ChatBIOrchestrator

# 创建ChatBI实例
chatbi = ChatBIOrchestrator()

# 查询示例
result = chatbi.query("显示过去6个月每月的销售趋势")
print(result)

# 添加正面反馈
if result.success:
    chatbi.add_positive_feedback(
        question="显示过去6个月每月的销售趋势",
        sql=result.sql_query,
        description="月度销售趋势分析"
    )

# 查看知识库统计
stats = chatbi.get_knowledge_stats()
print(f"知识库条目数: {stats['total_items']}")
```

## 📁 项目结构

```
strands_data_agent/
├── 🔥 gradio_app_login_gate.py    # 主程序入口（登录门禁版）
├── 🚀 start_login_gate.py         # 主程序启动脚本
├── 📋 gradio_app_chat.py          # ChatBI应用核心类
├── 🎛️ start_gradio.py             # 界面选择器
├── 💬 start_chat_ui.py            # 对话式界面启动
├── 🖥️ cli.py                      # 命令行接口
├── 📦 requirements.txt            # 依赖管理
├── ⚙️ config.env.example          # 配置模板
├── 📚 README.md                   # 项目文档
├── 📖 文档目录/
│   ├── CHATBI_AUTH_GUIDE.md       # 认证功能指南
│   ├── RAG_INTEGRATION_GUIDE.md   # RAG集成指南
│   ├── SQL_KNOWLEDGE_BASE_GUIDE.md # SQL知识库指南
│   └── COMPLETE_LOGIN_GATE_SUMMARY.md # 登录门禁总结
├── 🧠 chatbi/                     # 核心ChatBI模块
│   ├── __init__.py
│   ├── config.py                  # 配置管理
│   ├── orchestrator.py            # 主控智能体
│   ├── 🔐 auth/                   # 认证系统
│   │   ├── user_manager.py        # 用户管理
│   │   ├── session_manager.py     # 会话管理
│   │   ├── permission_manager.py  # 权限管理
│   │   └── chatbi_integration.py  # ChatBI集成
│   ├── 🤖 agents/                 # 智能体层
│   │   ├── sql_generator.py       # SQL生成智能体
│   │   ├── data_analyst.py        # 数据分析智能体
│   │   ├── chart_agent.py         # 图表生成智能体
│   │   └── sql_fixer.py           # SQL修复智能体
│   ├── 🧠 knowledge_base/         # 知识库系统
│   │   ├── sql_knowledge_manager.py # SQL知识库管理
│   │   ├── rag_strategy.py        # RAG策略
│   │   ├── vector_store.py        # 向量存储
│   │   └── embedding_service.py   # 嵌入服务
│   ├── 🗄️ database/               # 数据库层
│   │   ├── connectors.py          # 数据库连接器
│   │   ├── schema_manager.py      # Schema管理
│   │   ├── sql_executor.py        # SQL执行器
│   │   └── table_metadata_manager.py # 表元数据管理
│   └── 🛠️ tools/                  # 工具层
│       ├── data_processor.py      # 数据处理
│       └── visualization.py       # 可视化工具
├── 📊 data/                       # 数据目录
│   ├── charts/                    # 图表存储
│   └── knowledge_base/            # 知识库数据
└── 🧪 tests/                      # 测试目录
    ├── test_chatbi_integration.py
    ├── test_rag_strategy.py
    └── ...
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

## ✨ 已完成功能

### 🔐 用户认证系统 ✅
- **登录门禁**: 全屏登录界面，用户必须认证后才能访问
- **用户管理**: 支持用户注册、登录、会话管理
- **权限控制**: 基于用户角色的数据访问权限控制
- **安全审计**: 完整的用户操作日志和安全审计

### 🧠 RAG知识库系统 ✅
- **智能检索**: 基于向量相似度的历史查询匹配
- **知识积累**: 用户点赞后自动存储Q-SQL对到向量数据库
- **策略选择**: 根据相似度智能选择SQL生成策略
- **持续学习**: 基于用户反馈不断优化查询准确性

### 🤖 多智能体协作 ✅
- **SQL生成智能体**: 自然语言转SQL查询
- **数据分析智能体**: AI驱动的数据洞察分析
- **图表生成智能体**: 智能选择图表类型和可视化
- **SQL修复智能体**: 自动检测和修复SQL错误

### 📊 企业级功能 ✅
- **多数据库支持**: PostgreSQL、MySQL等主流数据库
- **Schema管理**: 动态获取和缓存数据库结构信息
- **表元数据管理**: 支持业务字段描述和元数据维护
- **数据安全**: 只读权限，SQL注入防护

## 🚀 未来规划

### 短期目标
- 🔄 **流式输出**: 实现对话式界面的实时响应
- 📱 **移动端适配**: 响应式设计，支持移动设备
- 🎨 **UI优化**: 进一步美化界面，提升用户体验

### 中期目标
- 🧠 **上下文记忆**: 多轮对话上下文理解
- 🎯 **个性化推荐**: 基于用户历史的智能推荐
- 📈 **高级分析**: 预测性分析和异常检测

### 长期目标
- 🏢 **多租户支持**: 企业级多租户架构
- 🔌 **API开放**: RESTful API接口
- 🌐 **云原生**: 容器化部署和微服务架构

## 联系方式

- 项目主页: [链接]
- 文档: [链接]
- 问题反馈: [链接] 