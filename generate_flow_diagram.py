#!/usr/bin/env python3
"""
生成ChatBI应用的整体调用流程图
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def generate_mermaid_diagram():
    """生成Mermaid格式的流程图"""
    
    mermaid_code = """
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
        ANALYZER[DataAnalystAgent<br/>数据分析智能体]
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
    ORCH --> CHART
    ORCH --> SQL_EXEC
    ORCH --> ANALYZER
    
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
"""
    
    return mermaid_code

def generate_component_analysis():
    """生成组件分析报告"""
    
    analysis = """
# ChatBI 组件详细分析

## 1. 核心组件依赖关系

### 前端到后端的调用链
```
Gradio UI → ChatBIApp → IntegrationAdapter → Orchestrator → Agents → Database
```

### 认证流程
```
用户登录 → UserManager → AuthDatabase → SessionManager → PermissionFilter
```

### 查询流程
```
自然语言查询 → SQLGeneratorAgent → RAG检索 → LLM生成 → SQL执行 → 结果返回
```

## 2. 关键配置文件

### 环境配置 (.env)
- 数据库连接配置
- DashScope API密钥
- 模型配置
- RAG配置参数
- 认证系统配置

### 主配置 (config.py)
- DatabaseConfig: 数据库配置
- LLMConfig: 大模型配置
- RAGConfig: RAG系统配置
- RetryConfig: 重试机制配置
- AuthConfig: 认证配置
- PermissionConfig: 权限配置

## 3. 数据流向

### 查询数据流
1. **输入**: 用户自然语言查询
2. **认证**: 验证用户身份和权限
3. **RAG检索**: 搜索相似历史查询
4. **SQL生成**: LLM生成SQL查询
5. **权限过滤**: 根据用户权限过滤表/字段
6. **执行**: 在数据库中执行SQL
7. **分析**: 可选的数据分析和可视化
8. **输出**: 返回结果给用户

### 元数据流
1. **Schema获取**: 从数据库获取表结构
2. **权限过滤**: 根据用户权限过滤
3. **缓存**: 存储到本地缓存
4. **业务增强**: 添加用户定义的业务信息
5. **LLM使用**: 作为上下文提供给LLM

## 4. 缓存策略

### Schema缓存
- 文件: `./data/knowledge_base/schema_cache.json`
- TTL: 3600秒（可配置）
- 策略: 按用户ID分别缓存

### 知识库缓存
- 向量数据库: ChromaDB
- 本地存储: `./data/knowledge_base/`
- 策略: 持久化存储，支持增量更新

### 表元数据缓存
- 文件: `./data/knowledge_base/table_metadata.json`
- 策略: 实时更新，持久化存储

## 5. 错误处理和重试机制

### 数据库连接
- 自动重连机制
- 连接池管理
- 超时处理

### LLM调用
- 指数退避重试
- 多次尝试机制
- 响应质量验证

### RAG系统
- 降级策略
- 缓存回退
- 错误恢复

## 6. 性能优化点

### 数据库层面
- 连接池复用
- Schema缓存
- 查询结果缓存

### LLM调用
- 提示词优化
- 批量处理
- 响应缓存

### RAG系统
- 向量索引优化
- 相似度计算优化
- 结果重排序

## 7. 安全考虑

### 认证授权
- JWT会话管理
- 基于角色的权限控制
- Schema级别的访问控制

### SQL安全
- SQL注入防护
- 只允许SELECT查询
- 权限过滤

### 数据安全
- 敏感信息脱敏
- 审计日志记录
- 会话超时管理
"""
    
    return analysis

def generate_deployment_script():
    """生成部署和维护脚本"""
    
    script = """
# ChatBI 部署和维护脚本

## 1. 环境准备脚本

### install_dependencies.sh
```bash
#!/bin/bash
# 安装Python依赖
pip install -r requirements.txt

# 安装额外的RAG依赖
pip install chromadb sentence-transformers

# 创建必要的目录
mkdir -p data/knowledge_base
mkdir -p logs

# 设置权限
chmod +x *.py
```

### setup_database.sh
```bash
#!/bin/bash
# 初始化认证系统数据库
python init_auth_system.py

# 清理缓存
python clear_schema_cache.py

# 测试数据库连接
python debug_table_list.py
```

## 2. 启动脚本

### start_chatbi.sh
```bash
#!/bin/bash
# 启动ChatBI应用
export PYTHONPATH=$PWD:$PYTHONPATH

# 检查环境变量
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "错误: 请设置DASHSCOPE_API_KEY环境变量"
    exit 1
fi

# 启动应用
python start_chatbi_auth.py
```

### start_development.sh
```bash
#!/bin/bash
# 开发模式启动
export DEBUG=true
export LOG_LEVEL=DEBUG

python gradio_app_chat.py
```

## 3. 维护脚本

### maintenance.py
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def clear_all_cache():
    \"\"\"清理所有缓存\"\"\"
    from clear_schema_cache import clear_schema_cache
    from chatbi.knowledge_base import get_knowledge_manager
    
    # 清理Schema缓存
    clear_schema_cache()
    
    # 清理知识库缓存
    kb_manager = get_knowledge_manager()
    if kb_manager.enabled:
        kb_manager.clear_cache()
    
    print("✅ 所有缓存已清理")

def backup_knowledge_base():
    \"\"\"备份知识库\"\"\"
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup/knowledge_base_{timestamp}"
    
    shutil.copytree("data/knowledge_base", backup_dir)
    print(f"✅ 知识库已备份到: {backup_dir}")

def health_check():
    \"\"\"健康检查\"\"\"
    from debug_table_list import main as debug_main
    from test_column_update import main as test_main
    
    print("🔍 执行健康检查...")
    
    # 测试数据库连接和表获取
    debug_main()
    
    # 测试字段更新功能
    test_main()
    
    print("✅ 健康检查完成")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python maintenance.py [clear_cache|backup|health_check]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "clear_cache":
        clear_all_cache()
    elif command == "backup":
        backup_knowledge_base()
    elif command == "health_check":
        health_check()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)
```

## 4. 监控脚本

### monitor.py
```python
#!/usr/bin/env python3
import time
import logging
from datetime import datetime

def monitor_system():
    \"\"\"系统监控\"\"\"
    while True:
        try:
            # 检查数据库连接
            from chatbi.database import get_database_connector
            connector = get_database_connector()
            
            if not connector.is_connected:
                logging.warning("数据库连接断开，尝试重连...")
                connector.connect()
            
            # 检查知识库状态
            from chatbi.knowledge_base import get_knowledge_manager
            kb_manager = get_knowledge_manager()
            
            if kb_manager.enabled:
                stats = kb_manager.get_stats()
                logging.info(f"知识库状态: {stats}")
            
            # 检查缓存大小
            import os
            cache_dir = "data/knowledge_base"
            if os.path.exists(cache_dir):
                size = sum(os.path.getsize(os.path.join(cache_dir, f)) 
                          for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f)))
                logging.info(f"缓存大小: {size / 1024 / 1024:.2f} MB")
            
            time.sleep(300)  # 5分钟检查一次
            
        except Exception as e:
            logging.error(f"监控异常: {str(e)}")
            time.sleep(60)  # 出错后1分钟重试

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor_system()
```

## 5. 配置管理脚本

### config_manager.py
```python
#!/usr/bin/env python3
import os
import json
from pathlib import Path

def update_config(key, value):
    \"\"\"更新配置\"\"\"
    env_file = Path(".env")
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\\n"
                updated = True
                break
        
        if not updated:
            lines.append(f"{key}={value}\\n")
        
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ 配置已更新: {key}={value}")
    else:
        print("❌ .env 文件不存在")

def show_config():
    \"\"\"显示当前配置\"\"\"
    from chatbi.config import config
    
    print("📊 当前配置:")
    print(f"  数据库类型: {config.database.type}")
    print(f"  数据库主机: {config.database.host}")
    print(f"  RAG启用: {config.rag.enabled}")
    print(f"  模型名称: {config.llm.model_name}")
    print(f"  日志级别: {config.log_level}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        show_config()
    elif len(sys.argv) == 3:
        update_config(sys.argv[1], sys.argv[2])
    else:
        print("用法: python config_manager.py [key value]")
```
"""
    
    return script

def main():
    """主函数"""
    print("🚀 生成ChatBI应用流程图和分析文档...")
    
    # 生成流程图
    mermaid_diagram = generate_mermaid_diagram()
    with open("ChatBI_Flow_Diagram.md", "w", encoding="utf-8") as f:
        f.write(mermaid_diagram)
    print("✅ 流程图已生成: ChatBI_Flow_Diagram.md")
    
    # 生成组件分析
    component_analysis = generate_component_analysis()
    with open("ChatBI_Component_Analysis.md", "w", encoding="utf-8") as f:
        f.write(component_analysis)
    print("✅ 组件分析已生成: ChatBI_Component_Analysis.md")
    
    # 生成部署脚本
    deployment_script = generate_deployment_script()
    with open("ChatBI_Deployment_Guide.md", "w", encoding="utf-8") as f:
        f.write(deployment_script)
    print("✅ 部署指南已生成: ChatBI_Deployment_Guide.md")
    
    print("\n📋 生成的文件:")
    print("  1. ChatBI_Flow_Diagram.md - 系统架构流程图")
    print("  2. ChatBI_Component_Analysis.md - 组件详细分析")
    print("  3. ChatBI_Deployment_Guide.md - 部署和维护指南")
    
    print("\n💡 使用建议:")
    print("  - 在支持Mermaid的编辑器中查看流程图（如VS Code、Typora）")
    print("  - 根据分析文档了解系统架构和优化点")
    print("  - 使用部署指南中的脚本进行系统维护")

if __name__ == "__main__":
    main()