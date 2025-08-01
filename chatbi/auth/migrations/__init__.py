"""
认证模块数据库迁移脚本
"""

from .migration_manager import MigrationManager
from .create_auth_tables import create_auth_tables_migration

__all__ = ['MigrationManager', 'create_auth_tables_migration']