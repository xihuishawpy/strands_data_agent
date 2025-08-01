"""
会话管理器
实现用户会话的创建、验证和管理功能
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .models import UserSession
from .database import AuthDatabase
from .config import get_auth_config


@dataclass
class SessionResult:
    """会话操作结果"""
    success: bool
    session_token: Optional[str] = None
    session: Optional[UserSession] = None
    message: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SessionManager:
    """会话管理器类"""
    
    def __init__(self, database: AuthDatabase):
        """
        初始化会话管理器
        
        Args:
            database: 认证数据库实例
        """
        self.database = database
        self.auth_config = get_auth_config()
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, user_id: str, ip_address: str = None, 
                      user_agent: str = None) -> SessionResult:
        """
        创建用户会话
        
        Args:
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理字符串
            
        Returns:
            SessionResult: 会话创建结果
        """
        try:
            self.logger.info(f"开始创建会话: {user_id}")
            
            # 1. 验证输入参数
            if not user_id:
                return SessionResult(
                    success=False,
                    message="用户ID不能为空",
                    errors=["invalid_input"]
                )
            
            # 2. 检查用户是否存在且活跃
            user = self.database.get_user_by_id(user_id)
            if not user or not user.is_active:
                return SessionResult(
                    success=False,
                    message="用户不存在或已被禁用",
                    errors=["user_not_found"]
                )
            
            # 3. 检查用户会话数量限制
            active_sessions = self._get_user_active_sessions(user_id)
            if len(active_sessions) >= self.auth_config.max_sessions_per_user:
                # 清理最旧的会话
                self._cleanup_oldest_sessions(user_id, len(active_sessions) - self.auth_config.max_sessions_per_user + 1)
            
            # 4. 生成会话令牌
            session_token = self._generate_session_token()
            
            # 5. 创建会话对象
            session = UserSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=self.auth_config.session_timeout),
                last_activity=datetime.now(),
                is_active=True
            )
            
            # 6. 保存到数据库
            if self.database.create_session(session):
                self.logger.info(f"会话创建成功: {user_id}")
                
                # 记录审计日志
                self._log_session_action(
                    user_id=user_id,
                    action="session_created",
                    details={
                        "session_id": session.id,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "created_time": datetime.now().isoformat()
                    }
                )
                
                return SessionResult(
                    success=True,
                    session_token=session_token,
                    session=session,
                    message="会话创建成功"
                )
            else:
                self.logger.error(f"会话创建失败，数据库保存错误: {user_id}")
                return SessionResult(
                    success=False,
                    message="会话创建失败，请稍后重试",
                    errors=["database_error"]
                )
                
        except Exception as e:
            self.logger.error(f"创建会话异常: {user_id} - {str(e)}")
            return SessionResult(
                success=False,
                message="创建会话过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def validate_session(self, session_token: str) -> SessionResult:
        """
        验证会话令牌
        
        Args:
            session_token: 会话令牌
            
        Returns:
            SessionResult: 验证结果
        """
        try:
            self.logger.debug(f"开始验证会话: {session_token[:10]}...")
            
            # 1. 验证输入参数
            if not session_token:
                return SessionResult(
                    success=False,
                    message="会话令牌不能为空",
                    errors=["invalid_input"]
                )
            
            # 2. 从数据库获取会话
            session = self.database.get_session_by_token(session_token)
            if not session:
                return SessionResult(
                    success=False,
                    message="会话不存在或已失效",
                    errors=["session_not_found"]
                )
            
            # 3. 检查会话状态
            if not session.is_valid():
                # 会话已过期或无效，清理它
                self._deactivate_session(session.id)
                return SessionResult(
                    success=False,
                    message="会话已过期，请重新登录",
                    errors=["session_expired"]
                )
            
            # 4. 更新会话活动时间
            if self.database.update_session_activity(session.id):
                session.update_activity()
            
            self.logger.debug(f"会话验证成功: {session.user_id}")
            return SessionResult(
                success=True,
                session=session,
                message="会话有效"
            )
            
        except Exception as e:
            self.logger.error(f"验证会话异常: {str(e)}")
            return SessionResult(
                success=False,
                message="验证会话过程中发生错误",
                errors=["internal_error"]
            )
    
    def refresh_session(self, session_token: str) -> SessionResult:
        """
        刷新会话（延长过期时间）
        
        Args:
            session_token: 会话令牌
            
        Returns:
            SessionResult: 刷新结果
        """
        try:
            self.logger.info(f"开始刷新会话: {session_token[:10]}...")
            
            # 1. 验证会话
            validation_result = self.validate_session(session_token)
            if not validation_result.success:
                return validation_result
            
            session = validation_result.session
            
            # 2. 更新过期时间
            new_expires_at = datetime.now() + timedelta(seconds=self.auth_config.session_timeout)
            
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE user_sessions 
            SET expires_at = {placeholder}, last_activity = {placeholder}
            WHERE id = {placeholder}
            """
            
            affected = self.database.execute_update(sql, (new_expires_at, datetime.now(), session.id))
            
            if affected > 0:
                session.expires_at = new_expires_at
                session.last_activity = datetime.now()
                
                self.logger.info(f"会话刷新成功: {session.user_id}")
                
                # 记录审计日志
                self._log_session_action(
                    user_id=session.user_id,
                    action="session_refreshed",
                    details={
                        "session_id": session.id,
                        "new_expires_at": new_expires_at.isoformat(),
                        "refreshed_time": datetime.now().isoformat()
                    }
                )
                
                return SessionResult(
                    success=True,
                    session=session,
                    message="会话刷新成功"
                )
            else:
                return SessionResult(
                    success=False,
                    message="会话刷新失败",
                    errors=["refresh_failed"]
                )
                
        except Exception as e:
            self.logger.error(f"刷新会话异常: {str(e)}")
            return SessionResult(
                success=False,
                message="刷新会话过程中发生错误",
                errors=["internal_error"]
            )
    
    def destroy_session(self, session_token: str) -> SessionResult:
        """
        销毁会话（登出）
        
        Args:
            session_token: 会话令牌
            
        Returns:
            SessionResult: 销毁结果
        """
        try:
            self.logger.info(f"开始销毁会话: {session_token[:10]}...")
            
            # 1. 获取会话信息
            session = self.database.get_session_by_token(session_token)
            if not session:
                return SessionResult(
                    success=True,  # 会话不存在也算成功
                    message="会话已不存在"
                )
            
            # 2. 停用会话
            if self._deactivate_session(session.id):
                self.logger.info(f"会话销毁成功: {session.user_id}")
                
                # 记录审计日志
                self._log_session_action(
                    user_id=session.user_id,
                    action="session_destroyed",
                    details={
                        "session_id": session.id,
                        "destroyed_time": datetime.now().isoformat()
                    }
                )
                
                return SessionResult(
                    success=True,
                    message="会话销毁成功"
                )
            else:
                return SessionResult(
                    success=False,
                    message="会话销毁失败",
                    errors=["destroy_failed"]
                )
                
        except Exception as e:
            self.logger.error(f"销毁会话异常: {str(e)}")
            return SessionResult(
                success=False,
                message="销毁会话过程中发生错误",
                errors=["internal_error"]
            )
    
    def destroy_user_sessions(self, user_id: str, exclude_session_id: str = None) -> int:
        """
        销毁用户的所有会话（除了指定的会话）
        
        Args:
            user_id: 用户ID
            exclude_session_id: 要排除的会话ID
            
        Returns:
            int: 销毁的会话数量
        """
        try:
            self.logger.info(f"开始销毁用户所有会话: {user_id}")
            
            placeholder = self.database._get_placeholder()
            
            if exclude_session_id:
                sql = f"""
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE user_id = {placeholder} AND id != {placeholder} AND is_active = 1
                """
                params = (user_id, exclude_session_id)
            else:
                sql = f"""
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE user_id = {placeholder} AND is_active = 1
                """
                params = (user_id,)
            
            affected = self.database.execute_update(sql, params)
            
            if affected > 0:
                self.logger.info(f"销毁用户会话成功: {user_id} - {affected} 个")
                
                # 记录审计日志
                self._log_session_action(
                    user_id=user_id,
                    action="user_sessions_destroyed",
                    details={
                        "destroyed_count": affected,
                        "exclude_session_id": exclude_session_id,
                        "destroyed_time": datetime.now().isoformat()
                    }
                )
            
            return affected
            
        except Exception as e:
            self.logger.error(f"销毁用户会话异常: {user_id} - {str(e)}")
            return 0
    
    def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[UserSession]:
        """
        获取用户的会话列表
        
        Args:
            user_id: 用户ID
            active_only: 是否只返回活跃会话
            
        Returns:
            List[UserSession]: 会话列表
        """
        try:
            placeholder = self.database._get_placeholder()
            
            if active_only:
                sql = f"""
                SELECT * FROM user_sessions 
                WHERE user_id = {placeholder} AND is_active = 1
                ORDER BY last_activity DESC
                """
            else:
                sql = f"""
                SELECT * FROM user_sessions 
                WHERE user_id = {placeholder}
                ORDER BY last_activity DESC
                """
            
            results = self.database.execute_query(sql, (user_id,))
            return [UserSession.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"获取用户会话异常: {user_id} - {str(e)}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话
        
        Returns:
            int: 清理的会话数量
        """
        try:
            affected = self.database.cleanup_expired_sessions()
            
            if affected > 0:
                self.logger.info(f"清理过期会话: {affected} 个")
            
            return affected
            
        except Exception as e:
            self.logger.error(f"清理过期会话异常: {str(e)}")
            return 0
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            stats = {}
            
            # 总会话数
            sql = "SELECT COUNT(*) as count FROM user_sessions"
            result = self.database.execute_query(sql)
            stats['total_sessions'] = result[0]['count'] if result else 0
            
            # 活跃会话数
            sql = "SELECT COUNT(*) as count FROM user_sessions WHERE is_active = 1"
            result = self.database.execute_query(sql)
            stats['active_sessions'] = result[0]['count'] if result else 0
            
            # 过期会话数
            placeholder = self.database._get_placeholder()
            sql = f"SELECT COUNT(*) as count FROM user_sessions WHERE expires_at < {placeholder} AND is_active = 1"
            result = self.database.execute_query(sql, (datetime.now(),))
            stats['expired_sessions'] = result[0]['count'] if result else 0
            
            # 今日创建的会话数
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            sql = f"SELECT COUNT(*) as count FROM user_sessions WHERE created_at >= {placeholder}"
            result = self.database.execute_query(sql, (today,))
            stats['today_sessions'] = result[0]['count'] if result else 0
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取会话统计异常: {str(e)}")
            return {}
    
    def _generate_session_token(self) -> str:
        """生成安全的会话令牌"""
        return secrets.token_urlsafe(32)
    
    def _get_user_active_sessions(self, user_id: str) -> List[UserSession]:
        """获取用户的活跃会话"""
        try:
            placeholder = self.database._get_placeholder()
            sql = f"""
            SELECT * FROM user_sessions 
            WHERE user_id = {placeholder} AND is_active = 1 AND expires_at > {placeholder}
            ORDER BY last_activity DESC
            """
            
            results = self.database.execute_query(sql, (user_id, datetime.now()))
            return [UserSession.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"获取用户活跃会话异常: {user_id} - {str(e)}")
            return []
    
    def _cleanup_oldest_sessions(self, user_id: str, count: int):
        """清理用户最旧的会话"""
        try:
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE user_sessions 
            SET is_active = 0 
            WHERE id IN (
                SELECT id FROM user_sessions 
                WHERE user_id = {placeholder} AND is_active = 1
                ORDER BY last_activity ASC 
                LIMIT {placeholder}
            )
            """
            
            affected = self.database.execute_update(sql, (user_id, count))
            
            if affected > 0:
                self.logger.info(f"清理用户最旧会话: {user_id} - {affected} 个")
            
        except Exception as e:
            self.logger.error(f"清理最旧会话异常: {user_id} - {str(e)}")
    
    def _deactivate_session(self, session_id: str) -> bool:
        """停用会话"""
        try:
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE user_sessions 
            SET is_active = 0 
            WHERE id = {placeholder}
            """
            
            affected = self.database.execute_update(sql, (session_id,))
            return affected > 0
            
        except Exception as e:
            self.logger.error(f"停用会话异常: {session_id} - {str(e)}")
            return False
    
    def _log_session_action(self, user_id: str, action: str, details: Dict[str, Any] = None):
        """记录会话操作审计日志"""
        try:
            from .models import AuditLog
            
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="session",
                resource_id=user_id,
                details=details or {},
                created_at=datetime.now()
            )
            
            self.database.create_audit_log(audit_log)
        except Exception as e:
            # 审计日志失败不应该影响主要功能
            self.logger.warning(f"记录审计日志失败: {str(e)}")