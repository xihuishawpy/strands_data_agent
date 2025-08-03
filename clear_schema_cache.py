#!/usr/bin/env python3
"""
清理Schema缓存
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def clear_schema_cache():
    """清理Schema缓存"""
    print("🧹 开始清理Schema缓存...")
    
    try:
        from chatbi.config import config
        
        # 获取缓存文件路径
        cache_file = Path(config.knowledge_base_path) / "schema_cache.json"
        
        if cache_file.exists():
            os.remove(cache_file)
            print(f"✅ 已删除缓存文件: {cache_file}")
        else:
            print(f"ℹ️ 缓存文件不存在: {cache_file}")
        
        # 测试重新获取Schema
        print("\n🔄 测试重新获取Schema...")
        from chatbi.database import get_schema_manager
        
        schema_manager = get_schema_manager()
        
        # 强制刷新缓存
        schema_manager.refresh_cache()
        print("✅ Schema缓存已刷新")
        
        # 验证表列表
        tables = schema_manager.get_all_tables()
        print(f"📋 获取到 {len(tables)} 个表:")
        for i, table in enumerate(tables[:10]):
            print(f"  {i+1}. {table}")
        
        if len(tables) > 10:
            print(f"  ... 还有 {len(tables) - 10} 个表")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理缓存失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 开始清理Schema缓存...")
    print("=" * 50)
    
    if clear_schema_cache():
        print("\n🎉 Schema缓存清理完成！")
        print("💡 现在可以重新启动前端应用，表信息维护功能应该能正常工作了。")
    else:
        print("\n❌ Schema缓存清理失败，请检查错误信息。")

if __name__ == "__main__":
    main()