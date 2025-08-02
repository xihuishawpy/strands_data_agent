#!/usr/bin/env python3
"""
权限调试脚本
检查用户权限和配置
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from chatbi.config import config
from chatbi.auth import AuthDatabase, PermissionManager
from chatbi.auth.config import get_permission_config
from chatbi.auth.database_permission_filter import DatabasePermissionFilter

def debug_user_permissions(employee_id: str):
    """调试用户权限"""
    try:
        print(f"🔍 调试用户 {employee_id} 的权限...")
        
        # 初始化组件
        auth_database = AuthDatabase(config.database)
        permission_manager = PermissionManager(auth_database)
        permission_config = get_permission_config()
        
        # 获取用户信息
        user_query = auth_database.execute_query(
            "SELECT id, employee_id, is_admin FROM users WHERE employee_id = %s",
            (employee_id,)
        )
        
        if not user_query:
            print(f"❌ 用户 {employee_id} 不存在")
            return
        
        user_id = user_query[0]['id']
        is_admin = user_query[0]['is_admin']
        
        print(f"✅ 用户信息:")
        print(f"  - ID: {user_id}")
        print(f"  - 员工ID: {employee_id}")
        print(f"  - 是否管理员: {is_admin}")
        print()
        
        # 检查权限配置
        print("📋 权限配置:")
        print(f"  - Schema隔离启用: {permission_config.schema_isolation_enabled}")
        print(f"  - 严格权限检查: {permission_config.strict_permission_check}")
        print(f"  - 管理员继承权限: {permission_config.inherit_admin_permissions}")
        print(f"  - 默认Schema访问: {permission_config.default_schema_access}")
        print(f"  - 管理员Schema: {permission_config.admin_schemas}")
        print(f"  - 公共Schema: {permission_config.public_schemas}")
        print()
        
        # 获取用户权限
        user_permissions = permission_manager.get_user_permissions(user_id)
        print(f"🔐 用户权限 ({len(user_permissions)} 条):")
        for perm in user_permissions:
            print(f"  - Schema: {perm.schema_name}")
            print(f"    权限级别: {perm.permission_level}")
            print(f"    是否有效: {perm.is_valid()}")
            print(f"    是否活跃: {perm.is_active}")
            print()
        
        # 测试权限过滤
        permission_filter = DatabasePermissionFilter(permission_manager, auth_database)
        available_schemas = ["root", "information_schema", "mysql", "performance_schema"]
        
        print(f"🧪 测试Schema过滤:")
        print(f"  - 可用Schema: {available_schemas}")
        
        accessible_schemas = permission_filter.filter_schemas(user_id, available_schemas)
        print(f"  - 可访问Schema: {accessible_schemas}")
        
        # 如果没有可访问的schema，提供解决方案
        if not accessible_schemas:
            print()
            print("💡 解决方案:")
            print("1. 检查用户是否有正确的权限记录")
            print("2. 检查权限配置中的public_schemas或default_schema_access")
            print("3. 如果是管理员，检查admin_schemas配置")
            print("4. 考虑临时禁用schema隔离进行测试")
            
    except Exception as e:
        print(f"❌ 调试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python debug_permissions.py <员工ID>")
        print()
        print("示例:")
        print("  python debug_permissions.py 50992")
        return
    
    employee_id = sys.argv[1]
    debug_user_permissions(employee_id)

if __name__ == "__main__":
    main()