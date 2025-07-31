#!/usr/bin/env python3
"""
向量维度修复工具
检查并修复ChromaDB集合的向量维度不匹配问题
"""

import os
import sys
import logging
import json
from typing import Dict, Any, List
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_embedding_dimension():
    """检查当前嵌入模型的实际输出维度"""
    try:
        from chatbi.knowledge_base.embedding_service import get_embedding_service
        
        embedding_service = get_embedding_service()
        
        # 测试文本
        test_text = "这是一个测试文本"
        
        # 获取嵌入向量
        embedding = embedding_service.embed_text(test_text)
        
        actual_dimension = len(embedding)
        logger.info(f"实际嵌入维度: {actual_dimension}")
        
        return actual_dimension
        
    except Exception as e:
        logger.error(f"检查嵌入维度失败: {e}")
        return None

def check_chromadb_collections():
    """检查ChromaDB集合的配置"""
    try:
        import chromadb
        from chromadb.config import Settings
        
        persist_directory = os.path.join("data", "knowledge_base", "vectors")
        
        if not os.path.exists(persist_directory):
            logger.info("ChromaDB目录不存在，无需修复")
            return {}
        
        client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        collections = client.list_collections()
        collection_info = {}
        
        for collection in collections:
            try:
                # 获取集合信息
                coll = client.get_collection(collection.name)
                count = coll.count()
                
                collection_info[collection.name] = {
                    'count': count,
                    'metadata': collection.metadata
                }
                
                # 如果有数据，检查第一个向量的维度
                if count > 0:
                    try:
                        sample = coll.get(limit=1, include=['embeddings'])
                        if sample['embeddings'] and len(sample['embeddings']) > 0 and sample['embeddings'][0] is not None:
                            embedding = sample['embeddings'][0]
                            # 处理可能的NumPy数组或列表
                            if hasattr(embedding, '__len__'):
                                dimension = len(embedding)
                                collection_info[collection.name]['dimension'] = dimension
                                logger.info(f"集合 {collection.name}: {count} 条记录, 维度: {dimension}")
                            else:
                                logger.info(f"集合 {collection.name}: {count} 条记录, 向量格式异常")
                        else:
                            logger.info(f"集合 {collection.name}: {count} 条记录, 无向量数据")
                    except Exception as e:
                        logger.warning(f"无法获取集合 {collection.name} 的向量维度: {e}")
                else:
                    logger.info(f"集合 {collection.name}: 空集合")
                    
            except Exception as e:
                logger.error(f"检查集合 {collection.name} 失败: {e}")
        
        return collection_info
        
    except Exception as e:
        logger.error(f"检查ChromaDB集合失败: {e}")
        return {}

def backup_collection_data(collection_name: str = "sql_knowledge_base"):
    """备份集合数据"""
    try:
        import chromadb
        from chromadb.config import Settings
        
        persist_directory = os.path.join("data", "knowledge_base", "vectors")
        
        client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        try:
            collection = client.get_collection(collection_name)
        except:
            logger.info(f"集合 {collection_name} 不存在，无需备份")
            return None
        
        # 获取所有数据
        all_data = collection.get(
            include=['documents', 'metadatas', 'embeddings']
        )
        
        if not all_data['ids']:
            logger.info("集合为空，无需备份")
            return None
        
        # 创建备份文件
        backup_dir = os.path.join("data", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"{collection_name}_backup_{timestamp}.json")
        
        # 保存数据
        backup_data = {
            'collection_name': collection_name,
            'timestamp': timestamp,
            'count': len(all_data['ids']),
            'data': {
                'ids': all_data['ids'],
                'documents': all_data['documents'],
                'metadatas': all_data['metadatas']
                # 不保存embeddings，因为需要重新生成
            }
        }
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"数据备份完成: {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"备份数据失败: {e}")
        return None

def recreate_collection_with_correct_dimension(collection_name: str = "sql_knowledge_base", 
                                             backup_file: str = None):
    """使用正确的维度重新创建集合"""
    try:
        import chromadb
        from chromadb.config import Settings
        
        persist_directory = os.path.join("data", "knowledge_base", "vectors")
        
        client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 删除现有集合
        try:
            client.delete_collection(collection_name)
            logger.info(f"删除现有集合: {collection_name}")
        except:
            logger.info(f"集合 {collection_name} 不存在或已删除")
        
        # 创建新集合
        new_collection = client.create_collection(
            name=collection_name,
            metadata={"description": "SQL查询知识库"}
        )
        logger.info(f"创建新集合: {collection_name}")
        
        # 如果有备份文件，恢复数据
        if backup_file and os.path.exists(backup_file):
            logger.info(f"从备份恢复数据: {backup_file}")
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            data = backup_data['data']
            
            if data['ids']:
                # 重新生成embeddings
                from chatbi.knowledge_base.embedding_service import get_embedding_service
                embedding_service = get_embedding_service()
                
                logger.info(f"重新生成 {len(data['documents'])} 个向量...")
                
                # 批量生成embeddings
                new_embeddings = embedding_service.embed_texts(data['documents'])
                
                # 添加到新集合
                new_collection.add(
                    ids=data['ids'],
                    documents=data['documents'],
                    metadatas=data['metadatas'],
                    embeddings=new_embeddings
                )
                
                logger.info(f"成功恢复 {len(data['ids'])} 条记录")
        
        return True
        
    except Exception as e:
        logger.error(f"重新创建集合失败: {e}")
        return False

def update_env_dimension(actual_dimension: int):
    """更新.env文件中的向量维度配置"""
    try:
        env_file = Path('.env')
        
        if not env_file.exists():
            logger.warning(".env文件不存在")
            return False
        
        # 读取现有内容
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 更新RAG_VECTOR_DIMENSION
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('RAG_VECTOR_DIMENSION='):
                lines[i] = f'RAG_VECTOR_DIMENSION={actual_dimension}\n'
                updated = True
                break
        
        # 如果没找到，添加到末尾
        if not updated:
            lines.append(f'RAG_VECTOR_DIMENSION={actual_dimension}\n')
        
        # 写回文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        logger.info(f"更新.env文件中的向量维度为: {actual_dimension}")
        return True
        
    except Exception as e:
        logger.error(f"更新.env文件失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始向量维度检查和修复...")
    
    # 1. 检查实际嵌入维度
    logger.info("步骤1: 检查实际嵌入维度")
    actual_dimension = check_embedding_dimension()
    
    if actual_dimension is None:
        logger.error("无法获取实际嵌入维度，退出")
        return 1
    
    # 2. 检查ChromaDB集合
    logger.info("步骤2: 检查ChromaDB集合")
    collection_info = check_chromadb_collections()
    
    # 3. 检查是否需要修复
    need_fix = False
    for name, info in collection_info.items():
        stored_dimension = info.get('dimension')
        if stored_dimension and stored_dimension != actual_dimension:
            logger.warning(f"集合 {name} 维度不匹配: 存储={stored_dimension}, 实际={actual_dimension}")
            need_fix = True
    
    if not need_fix:
        logger.info("所有集合维度正确，无需修复")
        # 仍然更新.env文件以确保配置正确
        update_env_dimension(actual_dimension)
        return 0
    
    # 4. 询问用户是否进行修复
    try:
        response = input(f"\n发现维度不匹配问题，是否进行自动修复? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            logger.info("用户取消修复")
            return 0
    except KeyboardInterrupt:
        logger.info("\n用户取消")
        return 0
    
    # 5. 备份数据
    logger.info("步骤3: 备份现有数据")
    backup_file = backup_collection_data()
    
    # 6. 重新创建集合
    logger.info("步骤4: 重新创建集合")
    if recreate_collection_with_correct_dimension(backup_file=backup_file):
        logger.info("✓ 集合重新创建成功")
    else:
        logger.error("✗ 集合重新创建失败")
        return 1
    
    # 7. 更新配置文件
    logger.info("步骤5: 更新配置文件")
    if update_env_dimension(actual_dimension):
        logger.info("✓ 配置文件更新成功")
    else:
        logger.warning("配置文件更新失败")
    
    logger.info("向量维度修复完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())