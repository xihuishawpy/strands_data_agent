#!/usr/bin/env python3
"""
测试search_knowledge方法
"""

import logging
import sys
import time

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_search_knowledge():
    """测试search_knowledge方法"""
    try:
        from chatbi.knowledge_base.sql_knowledge_manager import get_knowledge_manager
        
        logger.info("获取知识库管理器...")
        knowledge_manager = get_knowledge_manager()
        
        if not knowledge_manager.enabled:
            logger.error("知识库未启用")
            return False
        
        # 测试查询
        test_question = "物料预算"
        logger.info(f"测试查询: {test_question}")
        
        start_time = time.time()
        result = knowledge_manager.search_knowledge(test_question)
        elapsed = time.time() - start_time
        
        logger.info(f"搜索完成，耗时: {elapsed:.2f}秒")
        logger.info(f"找到匹配: {result.found_match}")
        
        if result.found_match:
            logger.info(f"最佳匹配置信度: {result.confidence:.3f}")
            logger.info(f"是否使用缓存: {result.should_use_cached}")
            logger.info(f"相似示例数量: {len(result.similar_examples)}")
            
            if result.best_match:
                logger.info(f"最佳匹配问题: {result.best_match['question']}")
                logger.info(f"最佳匹配SQL: {result.best_match['sql']}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    logger.info("开始测试search_knowledge方法...")
    
    if test_search_knowledge():
        logger.info("✓ 测试通过")
        return 0
    else:
        logger.error("✗ 测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())