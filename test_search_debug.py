#!/usr/bin/env python3
"""
搜索功能调试脚本
测试向量搜索是否正常工作
"""

import logging
import sys
import time

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_embedding_service():
    """测试嵌入服务"""
    try:
        from chatbi.knowledge_base.embedding_service import get_embedding_service
        
        logger.info("测试嵌入服务...")
        embedding_service = get_embedding_service()
        
        test_text = "查询用户信息"
        logger.info(f"测试文本: {test_text}")
        
        start_time = time.time()
        embedding = embedding_service.embed_text(test_text)
        elapsed = time.time() - start_time
        
        if embedding:
            logger.info(f"✓ 嵌入生成成功，维度: {len(embedding)}, 耗时: {elapsed:.2f}秒")
            return True
        else:
            logger.error("✗ 嵌入生成失败")
            return False
            
    except Exception as e:
        logger.error(f"✗ 嵌入服务测试失败: {e}")
        return False

def test_vector_store():
    """测试向量存储"""
    try:
        from chatbi.knowledge_base.vector_store import get_vector_store
        
        logger.info("测试向量存储...")
        vector_store = get_vector_store()
        
        # 检查集合状态
        count = vector_store.collection.count()
        logger.info(f"集合中有 {count} 个条目")
        
        if count == 0:
            logger.warning("集合为空，添加测试数据...")
            # 添加测试数据
            test_id = vector_store.add_sql_knowledge(
                question="查询所有用户信息",
                sql="SELECT * FROM users",
                description="获取用户表中的所有记录"
            )
            logger.info(f"添加测试数据: {test_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 向量存储测试失败: {e}")
        return False

def test_search():
    """测试搜索功能"""
    try:
        from chatbi.knowledge_base.vector_store import get_vector_store
        
        logger.info("测试搜索功能...")
        vector_store = get_vector_store()
        
        test_question = "如何查询用户"
        logger.info(f"搜索问题: {test_question}")
        
        start_time = time.time()
        results = vector_store.search_similar_questions(
            question=test_question,
            top_k=3,
            similarity_threshold=0.1  # 降低阈值以获得更多结果
        )
        elapsed = time.time() - start_time
        
        logger.info(f"搜索完成，耗时: {elapsed:.2f}秒")
        logger.info(f"找到 {len(results)} 个结果")
        
        for i, result in enumerate(results):
            logger.info(f"结果 {i+1}: {result['question']} (相似度: {result['similarity']:.3f})")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 搜索测试失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    logger.info("开始搜索功能调试...")
    
    # 测试步骤
    tests = [
        ("嵌入服务", test_embedding_service),
        ("向量存储", test_vector_store),
        ("搜索功能", test_search)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"测试: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                logger.info(f"✓ {test_name} 测试通过")
                passed += 1
            else:
                logger.error(f"✗ {test_name} 测试失败")
        except Exception as e:
            logger.error(f"✗ {test_name} 测试异常: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"测试结果: {passed}/{total} 通过")
    logger.info(f"{'='*50}")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())