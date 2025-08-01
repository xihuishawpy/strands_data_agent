"""
认证模块命令行工具
提供数据库初始化、用户管理等功能
"""

import argparse
import sys
import logging
from typing import Optional
import getpass
from datetime import datetime

from ..config import config
from .database import AuthDatabase
from .models import User, AllowedEmployee, validate_employee_id, validate_password_strength


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def init_database():
    """初始化数据库"""
    print("正在初始化认证数据库...")
    
    try:
        auth_db = AuthDatabase(config.database)
        success = auth_db.initialize_database()
        
        if success:
            print("✓ 认证数据库初始化成功")
            
            # 显示数据库状态
            status = auth_db.get_database_status()
            print(f"数据库类型: {status['database_type']}")
            print(f"迁移状态: {status['migration_status']['applied_count']}/{status['migration_status']['total_migrations']} 已应用")
            
            return True
        else:
            print("✗ 认证数据库初始化失败")
            return False
            
    except Exception as e:
        print(f"✗ 数据库初始化异常: {str(e)}")
        return False


def create_admin_user():
    """创建管理员用户"""
    print("创建管理员用户")
    
    # 获取工号
    while True:
        employee_id = input("请输入管理员工号: ").strip()
        if not employee_id:
            print("工号不能为空")
            continue
        
        if not validate_employee_id(employee_id):
            print("工号格式无效（只允许字母数字和连字符，3-20位）")
            continue
        
        break
    
    # 获取密码
    while True:
        password = getpass.getpass("请输入密码: ")
        if not password:
            print("密码不能为空")
            continue
        
        password_validation = validate_password_strength(password)
        if not password_validation['valid']:
            print("密码不符合要求:")
            for error in password_validation['errors']:
                print(f"  - {error}")
            continue
        
        if password_validation['warnings']:
            print("密码建议:")
            for warning in password_validation['warnings']:
                print(f"  - {warning}")
        
        confirm_password = getpass.getpass("请确认密码: ")
        if password != confirm_password:
            print("两次输入的密码不一致")
            continue
        
        break
    
    # 获取其他信息
    email = input("请输入邮箱（可选）: ").strip() or None
    full_name = input("请输入姓名（可选）: ").strip() or None
    
    try:
        auth_db = AuthDatabase(config.database)
        
        # 检查用户是否已存在
        existing_user = auth_db.get_user_by_employee_id(employee_id)
        if existing_user:
            print(f"✗ 用户 {employee_id} 已存在")
            return False
        
        # 创建用户
        user = User(
            employee_id=employee_id,
            email=email,
            full_name=full_name,
            is_admin=True,
            is_active=True
        )
        user.set_password(password)
        
        success = auth_db.create_user(user)
        
        if success:
            print(f"✓ 管理员用户 {employee_id} 创建成功")
            
            # 将管理员工号添加到允许列表
            allowed_employee = AllowedEmployee(
                employee_id=employee_id,
                added_by=user.id,
                description="系统管理员"
            )
            auth_db.add_allowed_employee(allowed_employee)
            
            return True
        else:
            print(f"✗ 管理员用户 {employee_id} 创建失败")
            return False
            
    except Exception as e:
        print(f"✗ 创建管理员用户异常: {str(e)}")
        return False


def add_allowed_employee():
    """添加允许注册的工号"""
    print("添加允许注册的工号")
    
    # 获取工号
    while True:
        employee_id = input("请输入工号: ").strip()
        if not employee_id:
            print("工号不能为空")
            continue
        
        if not validate_employee_id(employee_id):
            print("工号格式无效（只允许字母数字和连字符，3-20位）")
            continue
        
        break
    
    description = input("请输入描述（可选）: ").strip() or None
    
    try:
        auth_db = AuthDatabase(config.database)
        
        # 检查工号是否已存在
        if auth_db.is_employee_allowed(employee_id):
            print(f"✗ 工号 {employee_id} 已在允许列表中")
            return False
        
        # 需要一个管理员用户ID，这里简化处理
        # 在实际应用中应该通过认证获取当前用户
        allowed_employee = AllowedEmployee(
            employee_id=employee_id,
            added_by="system",  # 简化处理
            description=description
        )
        
        success = auth_db.add_allowed_employee(allowed_employee)
        
        if success:
            print(f"✓ 工号 {employee_id} 已添加到允许列表")
            return True
        else:
            print(f"✗ 工号 {employee_id} 添加失败")
            return False
            
    except Exception as e:
        print(f"✗ 添加允许工号异常: {str(e)}")
        return False


def show_database_status():
    """显示数据库状态"""
    try:
        auth_db = AuthDatabase(config.database)
        status = auth_db.get_database_status()
        
        print("=== 认证数据库状态 ===")
        print(f"数据库类型: {status['database_type']}")
        print(f"连接状态: {status['connection_status']}")
        
        if 'migration_status' in status:
            migration = status['migration_status']
            print(f"迁移状态: {migration['applied_count']}/{migration['total_migrations']} 已应用")
            
            if migration['pending_count'] > 0:
                print(f"待应用迁移: {migration['pending_migrations']}")
        
        if 'table_statistics' in status:
            print("\n表统计信息:")
            for table, count in status['table_statistics'].items():
                print(f"  {table}: {count} 条记录")
        
        if 'error' in status:
            print(f"错误: {status['error']}")
        
    except Exception as e:
        print(f"✗ 获取数据库状态失败: {str(e)}")


def list_allowed_employees():
    """列出允许注册的工号"""
    try:
        auth_db = AuthDatabase(config.database)
        allowed_employees = auth_db.get_allowed_employees()
        
        if not allowed_employees:
            print("没有允许注册的工号")
            return
        
        print("=== 允许注册的工号列表 ===")
        for emp in allowed_employees:
            print(f"工号: {emp.employee_id}")
            print(f"  添加时间: {emp.added_at}")
            print(f"  描述: {emp.description or '无'}")
            print()
        
    except Exception as e:
        print(f"✗ 获取允许工号列表失败: {str(e)}")


def main():
    """主函数"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description="ChatBI认证模块管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 初始化数据库
    subparsers.add_parser('init-db', help='初始化认证数据库')
    
    # 创建管理员用户
    subparsers.add_parser('create-admin', help='创建管理员用户')
    
    # 添加允许工号
    subparsers.add_parser('add-employee', help='添加允许注册的工号')
    
    # 显示数据库状态
    subparsers.add_parser('status', help='显示数据库状态')
    
    # 列出允许工号
    subparsers.add_parser('list-employees', help='列出允许注册的工号')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'init-db':
            success = init_database()
        elif args.command == 'create-admin':
            success = create_admin_user()
        elif args.command == 'add-employee':
            success = add_allowed_employee()
        elif args.command == 'status':
            show_database_status()
            success = True
        elif args.command == 'list-employees':
            list_allowed_employees()
            success = True
        else:
            print(f"未知命令: {args.command}")
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 操作失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()