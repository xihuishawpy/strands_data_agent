
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
    """清理所有缓存"""
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
    """备份知识库"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup/knowledge_base_{timestamp}"
    
    shutil.copytree("data/knowledge_base", backup_dir)
    print(f"✅ 知识库已备份到: {backup_dir}")

def health_check():
    """健康检查"""
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
    """系统监控"""
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
    """更新配置"""
    env_file = Path(".env")
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                updated = True
                break
        
        if not updated:
            lines.append(f"{key}={value}\n")
        
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ 配置已更新: {key}={value}")
    else:
        print("❌ .env 文件不存在")

def show_config():
    """显示当前配置"""
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
