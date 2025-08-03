
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
