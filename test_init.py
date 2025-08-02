#!/usr/bin/env python3
"""
测试认证系统初始化
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试导入"""
    try:
        print("🔍 测试导入...")
        
        from chatbi.config import config
        print("✅ 主配置导入成功")
        
        from chatbi.auth import AuthDatabase, AllowedEmployeeManager
        print("✅ 认证模块导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_database_init():
    """测试数据库初始化"""
    try:
        print("🔍 测试数据库初始化...")
        
        from chatbi.config import config
        from chatbi.auth import AuthDatabase
        
        auth_database = AuthDatabase(config.database)
        print("✅ 数据库对象创建成功")
        
        # 测试初始化方法是否存在
        if hasattr(auth_database, 'initialize_database'):
            print("✅ initialize_database 方法存在")
        else:
            print("❌ initialize_database 方法不存在")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 数据库初始化测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_employee_manager():
    """测试员工管理器"""
    try:
        print("🔍 测试员工管理器...")
        
        from chatbi.config import config
        from chatbi.auth import AuthDatabase, AllowedEmployeeManager
        
        auth_database = AuthDatabase(config.database)
        employee_manager = AllowedEmployeeManager(auth_database)
        print("✅ 员工管理器创建成功")
        
        # 测试方法是否存在
        if hasattr(employee_manager, 'add_allowed_employee'):
            print("✅ add_allowed_employee 方法存在")
        else:
            print("❌ add_allowed_employee 方法不存在")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 员工管理器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试认证系统组件...")
    
    success = True
    success &= test_imports()
    success &= test_database_init()
    success &= test_employee_manager()
    
    if success:
        print("\n🎉 所有测试通过！可以运行初始化脚本了。")
    else:
        print("\n❌ 测试失败，请检查错误信息。")
    
    sys.exit(0 if success else 1)