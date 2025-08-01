"""
允许注册工号管理器
实现工号白名单的增删改查功能
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .models import AllowedEmployee, validate_employee_id
from .database import AuthDatabase


@dataclass
class AllowedEmployeeResult:
    """允许工号操作结果"""
    success: bool
    message: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class AllowedEmployeeManager:
    """允许注册工号管理器类"""
    
    def __init__(self, database: AuthDatabase):
        """
        初始化允许工号管理器
        
        Args:
            database: 认证数据库实例
        """
        self.database = database
        self.logger = logging.getLogger(__name__)
    
    def add_allowed_employee(self, employee_id: str, added_by: str, 
                           description: str = None) -> AllowedEmployeeResult:
        """
        添加允许注册的工号
        
        Args:
            employee_id: 工号
            added_by: 添加者用户ID
            description: 描述信息
            
        Returns:
            AllowedEmployeeResult: 操作结果
        """
        try:
            self.logger.info(f"开始添加允许工号: {employee_id}")
            
            # 1. 验证输入参数
            validation_result = self._validate_employee_input(employee_id, added_by)
            if not validation_result.success:
                return validation_result
            
            # 2. 检查工号是否已存在
            if self.is_employee_allowed(employee_id):
                self.logger.warning(f"工号已在允许列表中: {employee_id}")
                return AllowedEmployeeResult(
                    success=False,
                    message="该工号已在允许列表中",
                    errors=["employee_already_exists"]
                )
            
            # 3. 创建允许工号对象
            allowed_employee = AllowedEmployee(
                employee_id=employee_id,
                added_by=added_by,
                added_at=datetime.now(),
                description=description
            )
            
            # 4. 保存到数据库
            if self.database.add_allowed_employee(allowed_employee):
                self.logger.info(f"允许工号添加成功: {employee_id}")
                
                # 记录审计日志
                self._log_employee_action(
                    user_id=added_by,
                    action="allowed_employee_added",
                    resource_id=employee_id,
                    details={
                        "employee_id": employee_id,
                        "description": description,
                        "added_time": datetime.now().isoformat()
                    }
                )
                
                return AllowedEmployeeResult(
                    success=True,
                    message="工号添加成功"
                )
            else:
                self.logger.error(f"允许工号添加失败，数据库保存错误: {employee_id}")
                return AllowedEmployeeResult(
                    success=False,
                    message="添加失败，请稍后重试",
                    errors=["database_error"]
                )
                
        except Exception as e:
            self.logger.error(f"添加允许工号异常: {employee_id} - {str(e)}")
            return AllowedEmployeeResult(
                success=False,
                message="添加过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def remove_allowed_employee(self, employee_id: str, removed_by: str) -> AllowedEmployeeResult:
        """
        移除允许注册的工号
        
        Args:
            employee_id: 工号
            removed_by: 移除者用户ID
            
        Returns:
            AllowedEmployeeResult: 操作结果
        """
        try:
            self.logger.info(f"开始移除允许工号: {employee_id}")
            
            # 1. 验证输入参数
            validation_result = self._validate_employee_input(employee_id, removed_by)
            if not validation_result.success:
                return validation_result
            
            # 2. 检查工号是否存在
            if not self.is_employee_allowed(employee_id):
                self.logger.warning(f"工号不在允许列表中: {employee_id}")
                return AllowedEmployeeResult(
                    success=False,
                    message="该工号不在允许列表中",
                    errors=["employee_not_found"]
                )
            
            # 3. 从数据库删除
            placeholder = self.database._get_placeholder()
            sql = f"DELETE FROM allowed_employees WHERE employee_id = {placeholder}"
            
            affected = self.database.execute_update(sql, (employee_id,))
            
            if affected > 0:
                self.logger.info(f"允许工号移除成功: {employee_id}")
                
                # 记录审计日志
                self._log_employee_action(
                    user_id=removed_by,
                    action="allowed_employee_removed",
                    resource_id=employee_id,
                    details={
                        "employee_id": employee_id,
                        "removed_time": datetime.now().isoformat()
                    }
                )
                
                return AllowedEmployeeResult(
                    success=True,
                    message="工号移除成功"
                )
            else:
                self.logger.warning(f"允许工号移除失败，没有记录被删除: {employee_id}")
                return AllowedEmployeeResult(
                    success=False,
                    message="移除失败，工号可能不存在",
                    errors=["no_records_affected"]
                )
                
        except Exception as e:
            self.logger.error(f"移除允许工号异常: {employee_id} - {str(e)}")
            return AllowedEmployeeResult(
                success=False,
                message="移除过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def get_allowed_employees(self) -> List[AllowedEmployee]:
        """
        获取所有允许注册的工号
        
        Returns:
            List[AllowedEmployee]: 允许工号列表
        """
        try:
            return self.database.get_allowed_employees()
        except Exception as e:
            self.logger.error(f"获取允许工号列表异常: {str(e)}")
            return []
    
    def is_employee_allowed(self, employee_id: str) -> bool:
        """
        检查工号是否允许注册
        
        Args:
            employee_id: 工号
            
        Returns:
            bool: 是否允许注册
        """
        try:
            return self.database.is_employee_allowed(employee_id)
        except Exception as e:
            self.logger.error(f"检查工号允许状态异常: {employee_id} - {str(e)}")
            return False
    
    def get_allowed_employee_info(self, employee_id: str) -> Optional[AllowedEmployee]:
        """
        获取特定工号的详细信息
        
        Args:
            employee_id: 工号
            
        Returns:
            AllowedEmployee: 工号信息，如果不存在返回None
        """
        try:
            placeholder = self.database._get_placeholder()
            sql = f"SELECT * FROM allowed_employees WHERE employee_id = {placeholder}"
            
            results = self.database.execute_query(sql, (employee_id,))
            if results:
                return AllowedEmployee.from_dict(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"获取允许工号信息异常: {employee_id} - {str(e)}")
            return None
    
    def update_allowed_employee_description(self, employee_id: str, description: str, 
                                          updated_by: str) -> AllowedEmployeeResult:
        """
        更新允许工号的描述信息
        
        Args:
            employee_id: 工号
            description: 新的描述信息
            updated_by: 更新者用户ID
            
        Returns:
            AllowedEmployeeResult: 操作结果
        """
        try:
            self.logger.info(f"开始更新允许工号描述: {employee_id}")
            
            # 1. 验证输入参数
            if not employee_id or not updated_by:
                return AllowedEmployeeResult(
                    success=False,
                    message="工号和更新者ID不能为空",
                    errors=["invalid_input"]
                )
            
            # 2. 检查工号是否存在
            if not self.is_employee_allowed(employee_id):
                return AllowedEmployeeResult(
                    success=False,
                    message="该工号不在允许列表中",
                    errors=["employee_not_found"]
                )
            
            # 3. 更新描述信息
            placeholder = self.database._get_placeholder()
            sql = f"""
            UPDATE allowed_employees 
            SET description = {placeholder}
            WHERE employee_id = {placeholder}
            """
            
            affected = self.database.execute_update(sql, (description, employee_id))
            
            if affected > 0:
                self.logger.info(f"允许工号描述更新成功: {employee_id}")
                
                # 记录审计日志
                self._log_employee_action(
                    user_id=updated_by,
                    action="allowed_employee_description_updated",
                    resource_id=employee_id,
                    details={
                        "employee_id": employee_id,
                        "new_description": description,
                        "updated_time": datetime.now().isoformat()
                    }
                )
                
                return AllowedEmployeeResult(
                    success=True,
                    message="描述信息更新成功"
                )
            else:
                return AllowedEmployeeResult(
                    success=False,
                    message="更新失败，工号可能不存在",
                    errors=["no_records_affected"]
                )
                
        except Exception as e:
            self.logger.error(f"更新允许工号描述异常: {employee_id} - {str(e)}")
            return AllowedEmployeeResult(
                success=False,
                message="更新过程中发生错误，请稍后重试",
                errors=["internal_error"]
            )
    
    def batch_add_allowed_employees(self, employee_ids: List[str], added_by: str, 
                                  description: str = None) -> Dict[str, AllowedEmployeeResult]:
        """
        批量添加允许注册的工号
        
        Args:
            employee_ids: 工号列表
            added_by: 添加者用户ID
            description: 描述信息
            
        Returns:
            Dict[str, AllowedEmployeeResult]: 每个工号的操作结果
        """
        results = {}
        
        for employee_id in employee_ids:
            try:
                result = self.add_allowed_employee(employee_id, added_by, description)
                results[employee_id] = result
            except Exception as e:
                self.logger.error(f"批量添加工号异常: {employee_id} - {str(e)}")
                results[employee_id] = AllowedEmployeeResult(
                    success=False,
                    message="添加过程中发生错误",
                    errors=["internal_error"]
                )
        
        return results
    
    def batch_remove_allowed_employees(self, employee_ids: List[str], 
                                     removed_by: str) -> Dict[str, AllowedEmployeeResult]:
        """
        批量移除允许注册的工号
        
        Args:
            employee_ids: 工号列表
            removed_by: 移除者用户ID
            
        Returns:
            Dict[str, AllowedEmployeeResult]: 每个工号的操作结果
        """
        results = {}
        
        for employee_id in employee_ids:
            try:
                result = self.remove_allowed_employee(employee_id, removed_by)
                results[employee_id] = result
            except Exception as e:
                self.logger.error(f"批量移除工号异常: {employee_id} - {str(e)}")
                results[employee_id] = AllowedEmployeeResult(
                    success=False,
                    message="移除过程中发生错误",
                    errors=["internal_error"]
                )
        
        return results
    
    def search_allowed_employees(self, keyword: str = None, 
                               limit: int = 100) -> List[AllowedEmployee]:
        """
        搜索允许注册的工号
        
        Args:
            keyword: 搜索关键词（在工号和描述中搜索）
            limit: 返回结果数量限制
            
        Returns:
            List[AllowedEmployee]: 搜索结果
        """
        try:
            placeholder = self.database._get_placeholder()
            
            if keyword:
                sql = f"""
                SELECT * FROM allowed_employees 
                WHERE employee_id LIKE {placeholder} OR description LIKE {placeholder}
                ORDER BY added_at DESC 
                LIMIT {placeholder}
                """
                search_pattern = f"%{keyword}%"
                params = (search_pattern, search_pattern, limit)
            else:
                sql = f"""
                SELECT * FROM allowed_employees 
                ORDER BY added_at DESC 
                LIMIT {placeholder}
                """
                params = (limit,)
            
            results = self.database.execute_query(sql, params)
            return [AllowedEmployee.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"搜索允许工号异常: {str(e)}")
            return []
    
    def get_allowed_employees_count(self) -> int:
        """
        获取允许工号的总数
        
        Returns:
            int: 允许工号总数
        """
        try:
            sql = "SELECT COUNT(*) as count FROM allowed_employees"
            results = self.database.execute_query(sql)
            return results[0]['count'] if results else 0
        except Exception as e:
            self.logger.error(f"获取允许工号总数异常: {str(e)}")
            return 0
    
    def _validate_employee_input(self, employee_id: str, user_id: str) -> AllowedEmployeeResult:
        """
        验证工号输入参数
        
        Args:
            employee_id: 工号
            user_id: 用户ID
            
        Returns:
            AllowedEmployeeResult: 验证结果
        """
        errors = []
        
        # 验证工号
        if not employee_id:
            errors.append("工号不能为空")
        elif not validate_employee_id(employee_id):
            errors.append("工号格式无效，只允许字母数字和连字符，长度3-20位")
        
        # 验证用户ID
        if not user_id:
            errors.append("用户ID不能为空")
        
        if errors:
            return AllowedEmployeeResult(
                success=False,
                message="输入参数验证失败",
                errors=errors
            )
        
        return AllowedEmployeeResult(success=True)
    
    def _log_employee_action(self, user_id: str, action: str, resource_id: str = None,
                           details: Dict[str, Any] = None):
        """
        记录工号管理操作审计日志
        
        Args:
            user_id: 用户ID
            action: 操作类型
            resource_id: 资源ID
            details: 操作详情
        """
        try:
            from .models import AuditLog
            
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="allowed_employee",
                resource_id=resource_id,
                details=details or {},
                created_at=datetime.now()
            )
            
            self.database.create_audit_log(audit_log)
        except Exception as e:
            # 审计日志失败不应该影响主要功能
            self.logger.warning(f"记录审计日志失败: {str(e)}")