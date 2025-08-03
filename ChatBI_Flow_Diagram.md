
```mermaid
graph TB
    %% 用户界面层
    subgraph "前端界面层"
        UI[Gradio Web界面]
        AUTH[用户认证界面]
        CHAT[对话查询界面]
        MGMT[表信息维护界面]
        KB[知识库管理界面]
    end
    
    %% 应用层
    subgraph "应用层 (ChatBIApp)"
        APP[ChatBIApp主应用]
        LOGIN[用户登录逻辑]
        QUERY[查询处理逻辑]
        META[元数据管理逻辑]
        FEEDBACK[反馈处理逻辑]
    end
    
    %% 认证系统
    subgraph "认证系统"
        USER_MGR[UserManager<br/>用户管理器]
        SESSION_MGR[SessionManager<br/>会话管理器]
        AUTH_DB[AuthDatabase<br/>认证数据库]
        PERM_FILTER[PermissionFilter<br/>权限过滤器]
        INTEGRATION[IntegrationAdapter<br/>集成适配器]
    end
    
    %% 核心业务层
    subgraph "核心业务层"
        ORCH[Orchestrator<br/>编排器]
        SQL_GEN[SQLGeneratorAgent<br/>SQL生成智能体]
        SQL_FIX[SQLFixerAgent<br/>SQL修复智能体]
        ANALYZER[AnalyzerAgent<br/>分析智能体]
        CHART[ChartAgent<br/>图表智能体]
    end
    
    %% 数据库层
    subgraph "数据库层"
        SCHEMA_MGR[SchemaManager<br/>Schema管理器]
        CONNECTOR[DatabaseConnector<br/>数据库连接器]
        SQL_EXEC[SQLExecutor<br/>SQL执行器]
        META_MGR[TableMetadataManager<br/>表元数据管理器]
    end
    
    %% 知识库系统
    subgraph "知识库系统 (RAG)"
        KB_MGR[SQLKnowledgeManager<br/>SQL知识库管理器]
        VECTOR_DB[ChromaDB<br/>向量数据库]
        EMBEDDING[EmbeddingService<br/>嵌入服务]
        RERANK[RerankService<br/>重排序服务]
    end
    
    %% 外部服务
    subgraph "外部服务"
        LLM[DashScope LLM<br/>大语言模型]
        DB[(MySQL/PostgreSQL<br/>业务数据库)]
        CACHE[(本地缓存<br/>Schema/知识库)]
    end
    
    %% 主要调用流程
    UI --> APP
    AUTH --> LOGIN
    CHAT --> QUERY
    MGMT --> META
    KB --> FEEDBACK
    
    APP --> USER_MGR
    APP --> SESSION_MGR
    APP --> ORCH
    
    LOGIN --> AUTH_DB
    USER_MGR --> AUTH_DB
    SESSION_MGR --> AUTH_DB
    
    QUERY --> INTEGRATION
    INTEGRATION --> PERM_FILTER
    INTEGRATION --> ORCH
    
    ORCH --> SQL_GEN
    ORCH --> SQL_FIX
    ORCH --> ANALYZER
    ORCH --> CHART
    ORCH --> SQL_EXEC
    
    SQL_GEN --> KB_MGR
    SQL_GEN --> LLM
    KB_MGR --> VECTOR_DB
    KB_MGR --> EMBEDDING
    KB_MGR --> RERANK
    
    SQL_EXEC --> CONNECTOR
    CONNECTOR --> DB
    
    META --> SCHEMA_MGR
    META --> META_MGR
    SCHEMA_MGR --> CONNECTOR
    
    FEEDBACK --> KB_MGR
    
    %% 缓存关系
    SCHEMA_MGR -.-> CACHE
    KB_MGR -.-> CACHE
    META_MGR -.-> CACHE
    
    %% 样式定义
    classDef frontend fill:#e1f5fe
    classDef app fill:#f3e5f5
    classDef auth fill:#fff3e0
    classDef core fill:#e8f5e8
    classDef database fill:#fce4ec
    classDef knowledge fill:#f1f8e9
    classDef external fill:#f5f5f5
    
    class UI,AUTH,CHAT,MGMT,KB frontend
    class APP,LOGIN,QUERY,META,FEEDBACK app
    class USER_MGR,SESSION_MGR,AUTH_DB,PERM_FILTER,INTEGRATION auth
    class ORCH,SQL_GEN,SQL_FIX,ANALYZER,CHART core
    class SCHEMA_MGR,CONNECTOR,SQL_EXEC,META_MGR database
    class KB_MGR,VECTOR_DB,EMBEDDING,RERANK knowledge
    class LLM,DB,CACHE external
```

## ChatBI 应用架构说明

### 1. 前端界面层
- **Gradio Web界面**: 提供用户交互界面
- **用户认证界面**: 处理用户登录/注册
- **对话查询界面**: 自然语言查询入口
- **表信息维护界面**: 管理表和字段元数据
- **知识库管理界面**: 管理SQL知识库

### 2. 应用层 (ChatBIApp)
- **主应用**: 协调各个组件，管理应用状态
- **用户登录逻辑**: 处理用户认证流程
- **查询处理逻辑**: 处理用户查询请求
- **元数据管理逻辑**: 管理表和字段信息
- **反馈处理逻辑**: 处理用户反馈到知识库

### 3. 认证系统
- **UserManager**: 用户管理，处理注册/登录
- **SessionManager**: 会话管理，维护用户状态
- **AuthDatabase**: 认证数据存储
- **PermissionFilter**: 权限过滤，控制数据访问
- **IntegrationAdapter**: 集成适配器，包装业务组件

### 4. 核心业务层
- **Orchestrator**: 编排器，协调各个智能体
- **SQLGeneratorAgent**: SQL生成智能体，支持RAG
- **SQLFixerAgent**: SQL修复智能体
- **AnalyzerAgent**: 数据分析智能体
- **ChartAgent**: 图表生成智能体

### 5. 数据库层
- **SchemaManager**: Schema管理，支持权限过滤
- **DatabaseConnector**: 数据库连接，支持多种数据库
- **SQLExecutor**: SQL执行器，支持权限控制
- **TableMetadataManager**: 表元数据管理

### 6. 知识库系统 (RAG)
- **SQLKnowledgeManager**: SQL知识库管理
- **ChromaDB**: 向量数据库存储
- **EmbeddingService**: 文本嵌入服务
- **RerankService**: 结果重排序服务

### 7. 外部服务
- **DashScope LLM**: 阿里云大语言模型
- **MySQL/PostgreSQL**: 业务数据库
- **本地缓存**: Schema和知识库缓存

## 主要调用流程

### 用户查询流程
1. 用户在Gradio界面输入查询
2. ChatBIApp验证用户认证状态
3. IntegrationAdapter应用权限过滤
4. Orchestrator协调各个智能体
5. SQLGeneratorAgent生成SQL（使用RAG）
6. SQLExecutor执行SQL（权限控制）
7. 返回结果并可选生成图表/分析

### 表信息维护流程
1. 用户在维护界面选择表
2. SchemaManager获取表结构（权限过滤）
3. TableMetadataManager管理业务元数据
4. 更新数据库字段备注
5. 缓存更新的元数据信息

### 知识库反馈流程
1. 用户对查询结果点赞
2. SQLKnowledgeManager存储到向量数据库
3. 更新嵌入向量和索引
4. 用于后续RAG检索
