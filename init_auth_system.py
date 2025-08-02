#!/usr/bin/env python3
"""
初始化认证系统
创建必要的数据库表和添加初始的允许员工列表
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from chatbi.config import config
from chatbi.auth import AuthDatabase, AllowedEmployeeManager

def init_auth_system():
    """初始化认证系统"""
    print("🚀 开始初始化认证系统...")
    
    try:
        # 1. 初始化认证数据库
        print("📊 初始化认证数据库...")
        auth_database = AuthDatabase(config.database)
        
        # 2. 运行数据库迁移
        print("🔄 运行数据库迁移...")
        migration_result = auth_database.initialize_database()
        if migration_result:
            print("✅ 数据库迁移完成")
        else:
            print("❌ 数据库迁移失败")
            return False
        
        # 3. 创建系统管理员用户（绕过允许列表检查）
        print("👤 创建系统管理员用户...")
        
        # 首先直接在数据库中创建系统管理员用户，绕过正常注册流程
        from chatbi.auth.models import User
        
        # 检查admin用户是否已存在
        try:
            existing_admin_query = auth_database.execute_query(
                "SELECT id, employee_id, is_admin FROM users WHERE employee_id = %s",
                ("admin",)
            )
            
            if existing_admin_query:
                print("  ✅ 系统管理员已存在，使用现有账号")
                system_user_id = existing_admin_query[0]['id']
                
                # 确保现有用户是管理员
                if not existing_admin_query[0]['is_admin']:
                    auth_database.execute_update(
                        "UPDATE users SET is_admin = 1 WHERE id = %s",
                        (system_user_id,)
                    )
                    print("  ✅ 已将现有用户设置为管理员")
            else:
                # 直接创建系统管理员用户
                system_user_id = str(uuid.uuid4())
                admin_user = User(
                    id=system_user_id,
                    employee_id="admin",
                    email="admin@system.local",
                    full_name="系统管理员",
                    is_active=True,
                    is_admin=True,  # 直接设置为管理员
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                admin_user.set_password("102699xxh")  # 临时密码
                
                # 直接插入到数据库
                try:
                    if auth_database.create_user(admin_user):
                        print("  ✅ 系统管理员创建成功")
                    else:
                        print("  ❌ 系统管理员创建失败")
                        return False
                except Exception as e:
                    print(f"  ❌ 创建系统管理员时出错: {e}")
                    return False
        except Exception as e:
            print(f"  ❌ 检查现有管理员时出错: {e}")
            return False
        
        # 现在添加admin到允许员工列表
        try:
            # 检查admin是否已在允许列表中
            existing_allowed = auth_database.execute_query(
                "SELECT id FROM allowed_employees WHERE employee_id = %s",
                ("admin",)
            )
            
            if not existing_allowed:
                # 使用系统用户ID作为添加者
                auth_database.execute_update(
                    """INSERT INTO allowed_employees (id, employee_id, added_by, description, created_at) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (str(uuid.uuid4()), "admin", system_user_id, "系统初始化管理员账号", datetime.now())
                )
                print("  ✅ 已将admin添加到允许员工列表")
            else:
                print("  ✅ admin已在允许员工列表中")
        except Exception as e:
            print(f"  ⚠️ 添加admin到允许列表时出错: {e}")
        
        # 4. 初始化允许员工管理器
        print("👥 初始化允许员工管理器...")
        employee_manager = AllowedEmployeeManager(auth_database)
        
        # 5. 添加一些初始的允许员工ID（示例）
        initial_employees = [
            "admin",      # 管理员账号
            "50992",    # 测试账号1
            "demo",       # 演示账号
            "user001",    # 用户账号1
            "system",     # 系统账号（已创建）
        ]
        
        print("➕ 添加初始允许员工列表...")
        for emp_id in initial_employees:
            result = employee_manager.add_allowed_employee(
                employee_id=emp_id,
                added_by=system_user_id,  # 使用系统用户ID
                description=f"系统初始化添加的员工ID: {emp_id}"
            )
            if result.success:
                print(f"  ✅ 添加员工ID: {emp_id}")
            else:
                print(f"  ⚠️ 员工ID {emp_id} 可能已存在: {result.message}")
        
        print("\n🎉 认证系统初始化完成！")
        print("\n📋 可用的员工ID:")
        for emp_id in initial_employees:
            print(f"  - {emp_id}")
        
        print("\n💡 使用说明:")
        print("1. 启动应用: python gradio_app_chat.py")
        print("2. 在浏览器中打开应用")
        print("3. 在'用户认证'标签页中注册新用户")
        print("4. 使用上述任一员工ID进行注册")
        print("5. 注册成功后即可登录使用")
        
        return True
        
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_auth_system()
    sys.exit(0 if success else 1)