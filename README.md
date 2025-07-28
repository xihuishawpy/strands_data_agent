# ChatBI - 企业级智能数据查询应用

基于 Strands Agents 框架构建的企业级 ChatBI 智能数据查询应用，支持通过自然语言查询 PostgreSQL、MySQL 等数据库，自动生成 SQL、执行查询、数据分析和可视化。

## 功能特性

- 🤖 **智能SQL生成**: 将自然语言转换为准确的SQL查询
- 🔒 **安全执行**: 使用只读权限确保数据安全
- 📊 **智能分析**: AI驱动的数据解读和洞察
- 📈 **数据可视化**: 自动生成图表和可视化
- 💬 **对话式交互**: 人机对话式的数据查询体验
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

### 3. 测试系统

```bash
# 测试数据库连接
python debug_sql_execution.py

# 测试完整流程
python test_complete_flow.py
```

### 4. 启动应用

```bash
# 启动界面选择器 (推荐)
python start_gradio.py
# 选择 1: 对话式界面 (人机交互体验)
# 选择 2: 传统界面 (多标签页功能)

# 直接启动对话式界面
python start_chat_ui.py

# 直接启动传统界面
python gradio_app.py

# 使用命令行接口
python cli.py "统计每个表的记录数"
```

#### 界面选择指南

- **💬 对话式界面**: 适合日常查询，一次对话获得SQL、数据、分析、图表的完整回答
- **📋 传统界面**: 适合精细控制，提供SQL优化、详细配置等高级功能

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

### 6. 使用示例

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
├── chatbi/                 # 核心ChatBI模块
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── database/           # 数据库连接和工具
│   ├── agents/             # 智能体定义
│   ├── tools/              # 工具函数
│   └── orchestrator.py     # 主控智能体
├── data/                   # 数据目录
├── logs/                   # 日志目录
├── gradio_app.py           # 传统Web界面
├── gradio_app_chat.py      # 对话式Web界面
├── start_gradio.py         # 界面启动选择器
├── start_chat_ui.py        # 对话式界面启动脚本
├── cli.py                  # 命令行接口
├── test_*.py               # 测试脚本
├── requirements.txt        # 依赖文件
├── README.md               # 项目文档
├── CHAT_UI_README.md       # 对话式界面说明
├── UI_COMPARISON.md        # 界面对比说明
└── EMPTY_DATA_FIX.md       # 空数据处理修复说明
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

## 🚧 待开发功能

### 1. ChatUI 流式输出
- **功能描述**: 实现对话式界面的流式响应，提升用户体验
- **技术要点**:
  - 实时显示SQL生成过程
  - 流式展示数据分析结果
  - 渐进式图表加载
  - WebSocket或SSE实现
- **预期效果**: 用户可以实时看到AI的思考和处理过程，减少等待焦虑
- **优先级**: 高

### 2. SQL RAG 构建
- **功能描述**: 构建SQL知识库，提升SQL生成的准确性和一致性
- **技术要点**:
  - 收集和整理高质量SQL示例
  - 构建向量数据库存储SQL模式
  - 实现语义检索匹配
  - 集成到SQL生成流程
- **预期效果**: 
  - 提高复杂查询的生成准确率
  - 减少SQL语法错误
  - 支持企业特定的SQL模式和最佳实践
- **优先级**: 中

### 开发路线图

#### Phase 1: 用户体验优化 (Q1)
- ✅ 对话式界面基础版本
- 🚧 流式输出实现
- 📋 界面响应性优化
- 📋 移动端适配

#### Phase 2: 智能化增强 (Q2)
- 🚧 SQL RAG 知识库构建
- 📋 多轮对话上下文记忆
- 📋 查询意图理解优化
- 📋 个性化推荐系统

#### Phase 3: 企业级功能 (Q3)
- 📋 多租户支持
- 📋 权限管理系统
- 📋 审计日志
- 📋 API接口开放

#### Phase 4: 高级分析 (Q4)
- 📋 预测性分析
- 📋 异常检测
- 📋 自动报告生成
- 📋 数据血缘分析

### 贡献指南

如果您对以上功能感兴趣，欢迎参与开发：

1. **流式输出开发**:
   - 熟悉 Gradio 的流式API
   - 了解 WebSocket 或 SSE 技术
   - 前端实时更新经验

2. **SQL RAG 开发**:
   - 向量数据库经验 (如 Chroma, Pinecone)
   - 自然语言处理背景
   - SQL 专业知识

## 联系方式

- 项目主页: [链接]
- 文档: [链接]
- 问题反馈: [链接] 