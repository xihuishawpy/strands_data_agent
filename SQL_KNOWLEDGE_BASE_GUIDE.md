# SQL知识库功能使用指南

## 🎯 功能概述

SQL知识库是ChatBI的核心功能之一，通过RAG（检索增强生成）技术，基于用户反馈持续改进SQL生成质量。

## 🏗️ 架构设计

```
用户问题 → RAG检索 → 相似度判断 → SQL生成策略
    ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  高相似度(>0.8) │  │  中相似度(0.6-0.8)│  │  低相似度(<0.6) │
│  直接使用缓存   │  │  示例辅助生成   │  │  常规生成流程   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
    ↓                    ↓                    ↓
用户点赞 → 存储到向量数据库 → 持续改进
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install chromadb sentence-transformers
```

### 2. 配置环境变量

```bash
# .env文件
DASHSCOPE_API_KEY=your_api_key_here
RAG_ENABLED=true
RAG_SIMILARITY_THRESHOLD=0.7
RAG_CONFIDENCE_THRESHOLD=0.85
```

### 3. 测试功能

```bash
# 测试embedding服务
python test_embedding_only.py

# 测试完整知识库功能
python test_sql_knowledge_base.py

# 启动带反馈功能的Web界面
python gradio_app_with_feedback.py
```

## 💡 核心功能

### 1. 智能检索匹配

- **语义搜索**: 基于Qwen embedding模型进行向量相似度计算
- **Q-Q相似度**: 计算用户问题与历史问题的语义相似度
- **智能缓存**: 高相似度查询直接返回历史SQL，避免重复生成

### 2. 用户反馈机制

- **点赞收集**: 用户对满意结果进行👍点赞
- **知识积累**: 点赞的问题-SQL对自动存储到向量数据库
- **质量标记**: 被点赞的查询获得更高的权重和优先级

### 3. 渐进式学习

- **使用统计**: 跟踪每个SQL的使用频次
- **评分系统**: 基于用户反馈的动态评分机制
- **持续优化**: 随着使用增加，系统准确性不断提升

## 🔧 技术实现

### 向量数据库

```python
from chatbi.knowledge_base.vector_store import get_vector_store

# 获取向量存储实例
vector_store = get_vector_store()

# 添加SQL知识
vector_store.add_sql_knowledge(
    question="查询用户总数",
    sql="SELECT COUNT(*) FROM users",
    description="统计用户表中的总用户数",
    tags=["用户统计", "计数查询"],
    rating=1.0
)

# 搜索相似问题
similar_items = vector_store.search_similar_questions(
    question="用户数量是多少",
    top_k=5,
    similarity_threshold=0.7
)
```

### RAG集成

```python
from chatbi.knowledge_base.sql_knowledge_manager import get_knowledge_manager

# 获取知识库管理器
knowledge_manager = get_knowledge_manager()

# 搜索知识库
rag_result = knowledge_manager.search_knowledge("查询活跃用户")

if rag_result.should_use_cached:
    # 直接使用缓存的SQL
    sql = rag_result.best_match["sql"]
else:
    # 使用相似示例辅助生成
    examples = rag_result.similar_examples
```

### 主控制器集成

```python
from chatbi.orchestrator import get_orchestrator

orchestrator = get_orchestrator()

# 执行查询（自动使用RAG）
result = orchestrator.query("显示用户统计信息")

# 添加正面反馈
if result.success:
    orchestrator.add_positive_feedback(
        question="显示用户统计信息",
        sql=result.sql_query,
        description="用户统计查询"
    )
```

## 📊 配置参数

| 参数                       | 默认值 | 说明                               |
| -------------------------- | ------ | ---------------------------------- |
| `RAG_ENABLED`              | true   | 是否启用RAG功能                    |
| `RAG_SIMILARITY_THRESHOLD` | 0.7    | 相似度阈值（低于此值不返回结果）   |
| `RAG_CONFIDENCE_THRESHOLD` | 0.85   | 置信度阈值（高于此值直接使用缓存） |
| `RAG_MAX_EXAMPLES`         | 3      | 最大示例数量                       |

## 🎨 Web界面使用

### 带反馈功能的界面

```bash
python gradio_app_with_feedback.py
```

功能特点：
- 📝 自然语言查询输入
- 🔍 实时SQL生成和执行
- 📊 智能数据分析
- 👍 一键反馈机制
- 📈 知识库统计展示

### 使用流程

1. **输入问题**: 在文本框中输入自然语言问题
2. **执行查询**: 点击"🚀 执行查询"按钮
3. **查看结果**: 查看生成的SQL、数据结果和分析
4. **提供反馈**: 如果满意，点击"👍 满意，添加到知识库"
5. **持续改进**: 系统自动学习，提升后续查询质量

## 📈 性能优化

### 1. 向量缓存

- 使用ChromaDB持久化存储，避免重复计算
- 支持增量更新，新增数据不影响现有索引

### 2. 相似度计算

- 使用余弦相似度进行快速匹配
- 支持批量查询，提升处理效率

### 3. 智能阈值

- 动态调整相似度阈值，平衡准确性和召回率
- 基于历史表现自动优化参数

## 🔍 故障排除

### 常见问题

1. **ChromaDB初始化失败**
   ```bash
   pip install chromadb sentence-transformers
   ```

2. **Embedding API调用失败**
   - 检查`DASHSCOPE_API_KEY`是否正确设置
   - 确认网络连接正常

3. **搜索结果为空**
   - 检查知识库是否有数据
   - 降低`similarity_threshold`参数

4. **向量维度不匹配**
   - 确保使用相同的embedding模型
   - 重新创建向量数据库

### 调试命令

```bash
# 查看知识库统计
python -c "
from chatbi.orchestrator import get_orchestrator
stats = get_orchestrator().get_knowledge_stats()
print(stats)
"

# 测试embedding服务
python test_embedding_only.py

# 完整功能测试
python test_sql_knowledge_base.py
```

## 🚀 最佳实践

### 1. 数据质量

- 确保添加到知识库的SQL查询语法正确
- 为每个查询添加清晰的描述和标签
- 定期清理低质量或过时的条目

### 2. 用户反馈

- 鼓励用户对满意的结果进行点赞
- 收集用户对不满意结果的具体反馈
- 定期分析反馈数据，优化系统参数

### 3. 系统维护

- 定期备份向量数据库
- 监控系统性能和响应时间
- 根据使用情况调整配置参数

## 📚 扩展功能

### 1. 批量导入

```python
# 批量导入历史SQL
sql_examples = [
    {"question": "...", "sql": "...", "description": "..."},
    # 更多示例...
]

for example in sql_examples:
    knowledge_manager.add_positive_feedback(**example)
```

### 2. 导出知识库

```python
# 导出知识库数据
stats = knowledge_manager.get_knowledge_stats()
all_data = vector_store.collection.get(include=['documents', 'metadatas'])
```

### 3. 自定义标签

```python
# 添加自定义标签
vector_store.add_sql_knowledge(
    question="查询VIP用户",
    sql="SELECT * FROM users WHERE vip_level > 0",
    tags=["VIP用户", "会员查询", "高价值客户"]
)
```

## 🎯 未来规划

- [ ] 支持多语言查询
- [ ] 集成更多embedding模型
- [ ] 添加查询性能分析
- [ ] 支持SQL优化建议
- [ ] 实现联邦学习机制

---

**注意**: 本功能需要有效的DashScope API密钥才能正常工作。请确保在使用前正确配置环境变量。