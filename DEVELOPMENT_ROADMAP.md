# ChatBI 开发路线图

## 🎯 核心待开发功能

### 1. ChatUI 流式输出

#### 📋 功能需求
- **实时响应**: 用户输入问题后，实时显示AI的处理过程
- **分阶段展示**: 按照查询流程逐步显示结果
- **用户体验**: 减少等待时间，增加交互感

#### 🔧 技术实现方案

##### 方案A: Gradio 流式API (推荐)
```python
# 使用 Gradio 的 yield 机制实现流式输出
def stream_chat_query(message, history):
    # 阶段1: 显示开始处理
    history.append([message, "🚀 开始处理您的查询..."])
    yield history, None
    
    # 阶段2: Schema分析
    history[-1][1] = "📋 正在分析数据库结构..."
    yield history, None
    
    # 阶段3: SQL生成
    history[-1][1] = "🔧 正在生成SQL查询..."
    yield history, None
    
    # 阶段4: 执行查询
    history[-1][1] = "⚡ 正在执行查询..."
    yield history, None
    
    # 阶段5: 数据分析
    history[-1][1] = "🔍 正在分析数据..."
    yield history, None
    
    # 阶段6: 完整结果
    final_response = build_complete_response(result)
    history[-1][1] = final_response
    yield history, chart_data
```

##### 方案B: WebSocket 实现
```python
# 使用 WebSocket 实现真正的实时通信
import asyncio
import websockets

async def websocket_handler(websocket, path):
    async for message in websocket:
        # 处理用户消息
        await websocket.send("🚀 开始处理...")
        
        # 逐步发送处理状态
        for stage in process_stages:
            await websocket.send(f"📋 {stage.description}")
            result = await stage.execute()
            await websocket.send(f"✅ {stage.name} 完成")
```

#### 📊 实现优先级
1. **高优先级**: Gradio yield 方式 (快速实现)
2. **中优先级**: 状态进度条和动画
3. **低优先级**: WebSocket 完整重构

#### 🧪 测试计划
- 单元测试: 各阶段状态更新
- 集成测试: 完整流式查询流程
- 性能测试: 大数据量查询的流式响应
- 用户测试: 交互体验评估

---

### 2. SQL RAG 构建

#### 📋 功能需求
- **知识库构建**: 收集高质量SQL示例和模式
- **语义检索**: 根据用户问题匹配相关SQL示例
- **上下文增强**: 为SQL生成提供更好的参考
- **持续学习**: 从用户查询中学习和优化

#### 🔧 技术实现方案

##### 数据收集策略
```python
# SQL 示例数据结构
sql_examples = {
    "natural_language": "显示销售额最高的前10个区域",
    "sql_query": "SELECT region, SUM(sales_amount) as total_sales FROM sales GROUP BY region ORDER BY total_sales DESC LIMIT 10",
    "schema_context": {
        "tables": ["sales"],
        "columns": ["region", "sales_amount"],
        "relationships": []
    },
    "query_type": "aggregation_ranking",
    "complexity": "medium",
    "tags": ["sales", "ranking", "aggregation"]
}
```

##### 向量数据库实现
```python
import chromadb
from sentence_transformers import SentenceTransformer

class SQLRAGSystem:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("sql_examples")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_sql_example(self, example):
        # 编码自然语言描述
        embedding = self.encoder.encode(example["natural_language"])
        
        # 存储到向量数据库
        self.collection.add(
            embeddings=[embedding.tolist()],
            documents=[example["natural_language"]],
            metadatas=[{
                "sql_query": example["sql_query"],
                "query_type": example["query_type"],
                "complexity": example["complexity"]
            }],
            ids=[f"sql_{len(self.collection.get()['ids'])}"]
        )
    
    def search_similar_sql(self, user_question, top_k=3):
        # 编码用户问题
        query_embedding = self.encoder.encode(user_question)
        
        # 检索相似示例
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        
        return results
```

##### 集成到SQL生成流程
```python
class EnhancedSQLGenerator(SQLGeneratorAgent):
    def __init__(self):
        super().__init__()
        self.rag_system = SQLRAGSystem()
    
    def generate_sql_with_rag(self, question, schema_info):
        # 1. 检索相似SQL示例
        similar_examples = self.rag_system.search_similar_sql(question)
        
        # 2. 构建增强的提示词
        enhanced_prompt = self.build_rag_prompt(
            question, schema_info, similar_examples
        )
        
        # 3. 生成SQL
        return self.llm.generate(enhanced_prompt)
    
    def build_rag_prompt(self, question, schema, examples):
        prompt = f"""
基于以下数据库Schema和相似查询示例，生成SQL查询：

数据库Schema:
{schema}

用户问题: {question}

相似查询示例:
"""
        for example in examples['metadatas'][0]:
            prompt += f"""
示例: {example['natural_language']}
SQL: {example['sql_query']}
---
"""
        
        prompt += "\n请生成准确的SQL查询："
        return prompt
```

#### 📊 数据来源计划
1. **内部收集**: 从现有查询日志中提取
2. **公开数据集**: Spider、WikiSQL等数据集
3. **人工标注**: 针对特定业务场景的SQL示例
4. **用户反馈**: 从用户确认的正确SQL中学习

#### 🧪 评估指标
- **准确率**: SQL生成的正确性
- **相关性**: 检索示例的相关程度
- **覆盖率**: 知识库对查询类型的覆盖
- **性能**: 检索和生成的响应时间

---

## 🗓️ 开发时间线

### Phase 1: 流式输出 (4-6周)
- **Week 1-2**: Gradio流式API研究和原型开发
- **Week 3-4**: 集成到现有对话界面
- **Week 5-6**: 测试优化和用户体验调整

### Phase 2: SQL RAG基础 (6-8周)
- **Week 1-2**: 数据收集和清洗
- **Week 3-4**: 向量数据库搭建和测试
- **Week 5-6**: 集成到SQL生成流程
- **Week 7-8**: 效果评估和优化

### Phase 3: 功能完善 (4-6周)
- **Week 1-2**: 流式输出性能优化
- **Week 3-4**: SQL RAG持续学习机制
- **Week 5-6**: 整体系统测试和文档完善

---

## 🛠️ 技术栈选择

### 流式输出
- **前端**: Gradio (现有) + 自定义JavaScript
- **后端**: Python asyncio + yield
- **通信**: HTTP长连接 或 WebSocket

### SQL RAG
- **向量数据库**: ChromaDB (轻量)
- **嵌入模型**: SentenceTransformers
- **检索算法**: 语义相似度 + 关键词匹配
- **存储**: SQLite (本地) 或 PostgreSQL (生产)

---

## 🤝 贡献指南

### 参与流式输出开发
**技能要求**:
- Python异步编程经验
- Gradio框架熟悉
- 前端JavaScript基础

**任务分工**:
- 后端流式逻辑实现
- 前端状态展示优化
- 用户体验测试

### 参与SQL RAG开发
**技能要求**:
- 机器学习/NLP背景
- 向量数据库使用经验
- SQL专业知识

**任务分工**:
- 数据收集和标注
- 检索算法优化
- 效果评估和调优

### 开发环境搭建
```bash
# 克隆开发分支
git checkout -b feature/streaming-output
# 或
git checkout -b feature/sql-rag

# 安装额外依赖
pip install chromadb sentence-transformers asyncio

# 运行开发测试
python test_streaming.py
python test_rag_system.py
```

---

## 📈 成功指标

### 流式输出成功指标
- ✅ 用户等待时间感知减少50%
- ✅ 界面响应性评分提升至4.5/5
- ✅ 查询中断率降低30%

### SQL RAG成功指标
- ✅ SQL生成准确率提升15%
- ✅ 复杂查询成功率提升25%
- ✅ 用户满意度提升至4.0/5

### 整体系统指标
- ✅ 查询响应时间保持在3秒内
- ✅ 系统稳定性99.5%+
- ✅ 用户活跃度提升20%