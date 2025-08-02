#!/usr/bin/env python3
"""
用户权限授权脚本
为指定用户授予数据库schema访问权限
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from chatbi.config import config
from chatbi.auth import AuthDatabase, PermissionManager

def grant_schema_permission(employee_id: str, schema_name: str, permission_level: str = "read"):
    """
    为用户授予schema权限
    
    Args:
        employee_id: 员工ID
        schema_name: 数据库schema名称
        permission_level: 权限级别 (read/write/admin)
    """
    try:
        print(f"🔐 开始为用户 {employee_id} 授予 {schema_name} 的 {permission_level} 权限...")
        
        # 初始化认证数据库和权限管理器
        auth_database = AuthDatabase(config.database)
        permission_manager = PermissionManager(auth_database)
        
        # 获取用户信息
        user_query = auth_database.execute_query(
            "SELECT id, employee_id FROM users WHERE employee_id = %s",
            (employee_id,)
        )
        
        if not user_query:
            print(f"❌ 用户 {employee_id} 不存在")
            return False
        
        user_id = user_query[0]['id']
        print(f"✅ 找到用户: {employee_id} (ID: {user_id})")
        
        # 获取管理员用户ID（用作授权者）
        admin_query = auth_database.execute_query(
            "SELECT id FROM users WHERE employee_id = 'admin'",
        )
        
        if not admin_query:
            print("❌ 找不到管理员用户")
            return False
        
        admin_user_id = admin_query[0]['id']
        
        # 授予权限
        result = permission_manager.assign_schema_permission(
            user_id=user_id,
            schema_name=schema_name,
            permission_level=permission_level,
            granted_by=admin_user_id
        )
        
        if result.success:
            print(f"✅ 权限授予成功: {employee_id} -> {schema_name} ({permission_level})")
            return True
        else:
            print(f"❌ 权限授予失败: {result.message}")
            return False
            
    except Exception as e:
        print(f"❌ 授权过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def list_user_permissions(employee_id: str):
    """列出用户的所有权限"""
    try:
        print(f"📋 查询用户 {employee_id} 的权限...")
        
        auth_database = AuthDatabase(config.database)
        
        # 获取用户信息
        user_query = auth_database.execute_query(
            "SELECT id, employee_id FROM users WHERE employee_id = %s",
            (employee_id,)
        )
        
        if not user_query:
            print(f"❌ 用户 {employee_id} 不存在")
            return
        
        user_id = user_query[0]['id']
        
        # 查询用户权限
        permissions_query = auth_database.execute_query(
            """SELECT schema_name, permission_level, granted_at, is_active 
               FROM user_permissions 
               WHERE user_id = %s 
               ORDER BY granted_at DESC""",
            (user_id,)
        )
        
        if not permissions_query:
            print(f"📋 用户 {employee_id} 暂无任何权限")
            return
        
        print(f"📋 用户 {employee_id} 的权限列表:")
        for perm in permissions_query:
            status = "✅ 活跃" if perm['is_active'] else "❌ 已禁用"
            print(f"  - Schema: {perm['schema_name']}")
            print(f"    权限级别: {perm['permission_level']}")
            print(f"    授予时间: {perm['granted_at']}")
            print(f"    状态: {status}")
            print()
            
    except Exception as e:
        print(f"❌ 查询权限时发生错误: {str(e)}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python grant_user_permissions.py grant <员工ID> <schema名称> [权限级别]")
        print("  python grant_user_permissions.py list <员工ID>")
        print()
        print("示例:")
        print("  python grant_user_permissions.py grant 50992 root read")
        print("  python grant_user_permissions.py list 50992")
        return
    
    command = sys.argv[1]
    
    if command == "grant":
        if len(sys.argv) < 4:
            print("❌ 参数不足，需要: grant <员工ID> <schema名称> [权限级别]")
            return
        
        employee_id = sys.argv[2]
        schema_name = sys.argv[3]
        permission_level = sys.argv[4] if len(sys.argv) > 4 else "read"
        
        grant_schema_permission(employee_id, schema_name, permission_level)
        
    elif command == "list":
        if len(sys.argv) < 3:
            print("❌ 参数不足，需要: list <员工ID>")
            return
        
        employee_id = sys.argv[2]
        list_user_permissions(employee_id)
        
    else:
        print(f"❌ 未知命令: {command}")
        print("支持的命令: grant, list")

if __name__ == "__main__":
    main()