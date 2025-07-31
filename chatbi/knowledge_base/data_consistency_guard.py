"""
数据一致性保护机制
防止损坏数据影响系统稳定性
"""

import logging
import json
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """验证级别"""
    BASIC = "basic"           # 基础验证
    STANDARD = "standard"     # 标准验证
    STRICT = "strict"         # 严格验证

class DataIssueType(Enum):
    """数据问题类型"""
    MISSING_FIELD = "missing_field"
    INVALID_TYPE = "invalid_type"
    INVALID_VALUE = "invalid_value"
    CORRUPTED_DATA = "corrupted_data"
    DUPLICATE_DATA = "duplicate_data"
    INCONSISTENT_DATA = "inconsistent_data"

@dataclass
class ValidationIssue:
    """验证问题"""
    issue_type: DataIssueType
    field_name: str
    description: str
    severity: str  # "error", "warning", "info"
    suggested_fix: Optional[str] = None

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    issues: List[ValidationIssue]
    corrected_data: Optional[Dict[str, Any]] = None
    
    def add_issue(self, issue: ValidationIssue):
        """添加验证问题"""
        self.issues.append(issue)
        if issue.severity == "error":
            self.is_valid = False

class DataConsistencyGuard:
    """数据一致性保护器"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """
        初始化数据一致性保护器
        
        Args:
            validation_level: 验证级别
        """
        self.validation_level = validation_level
        self._known_hashes: Set[str] = set()  # 用于检测重复数据
        self._field_schemas = self._init_field_schemas()
        
        logger.info(f"数据一致性保护器初始化完成，验证级别: {validation_level.value}")
    
    def _init_field_schemas(self) -> Dict[str, Dict[str, Any]]:
        """初始化字段模式"""
        return {
            "question": {
                "type": str,
                "required": True,
                "min_length": 1,
                "max_length": 2000,
                "pattern": None
            },
            "sql": {
                "type": str,
                "required": True,
                "min_length": 1,
                "max_length": 10000,
                "pattern": r"^\s*(SELECT|WITH|select|with)"
            },
            "description": {
                "type": str,
                "required": False,
                "min_length": 0,
                "max_length": 5000,
                "pattern": None
            },
            "tags": {
                "type": list,
                "required": False,
                "min_items": 0,
                "max_items": 20,
                "item_type": str
            },
            "rating": {
                "type": [int, float],
                "required": False,
                "min_value": -10.0,
                "max_value": 10.0
            },
            "usage_count": {
                "type": int,
                "required": False,
                "min_value": 0,
                "max_value": 1000000
            },
            "created_at": {
                "type": str,
                "required": False,
                "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
            },
            "updated_at": {
                "type": str,
                "required": False,
                "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
            }
        }
    
    def validate_knowledge_item(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证知识库条目
        
        Args:
            data: 知识库条目数据
            
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True, issues=[])
        corrected_data = data.copy()
        
        # 基础验证
        self._validate_required_fields(data, result)
        self._validate_field_types(data, result, corrected_data)
        self._validate_field_values(data, result, corrected_data)
        
        # 标准验证
        if self.validation_level in [ValidationLevel.STANDARD, ValidationLevel.STRICT]:
            self._validate_data_consistency(data, result)
            self._validate_sql_safety(data, result)
            self._check_duplicate_data(data, result)
        
        # 严格验证
        if self.validation_level == ValidationLevel.STRICT:
            self._validate_data_quality(data, result)
            self._validate_metadata_integrity(data, result)
        
        # 如果有修正，设置修正后的数据
        if corrected_data != data:
            result.corrected_data = corrected_data
        
        return result
    
    def _validate_required_fields(self, data: Dict[str, Any], result: ValidationResult):
        """验证必需字段"""
        for field_name, schema in self._field_schemas.items():
            if schema.get("required", False) and field_name not in data:
                result.add_issue(ValidationIssue(
                    issue_type=DataIssueType.MISSING_FIELD,
                    field_name=field_name,
                    description=f"缺少必需字段: {field_name}",
                    severity="error",
                    suggested_fix=f"添加字段 {field_name}"
                ))
    
    def _validate_field_types(self, data: Dict[str, Any], 
                             result: ValidationResult, 
                             corrected_data: Dict[str, Any]):
        """验证字段类型"""
        for field_name, value in data.items():
            if field_name not in self._field_schemas:
                continue
            
            schema = self._field_schemas[field_name]
            expected_type = schema["type"]
            
            # 处理多种类型的情况
            if isinstance(expected_type, list):
                type_match = any(isinstance(value, t) for t in expected_type)
            else:
                type_match = isinstance(value, expected_type)
            
            if not type_match:
                # 尝试类型转换
                try:
                    if expected_type == str:
                        corrected_value = str(value)
                    elif expected_type == int:
                        corrected_value = int(value)
                    elif expected_type == float:
                        corrected_value = float(value)
                    elif expected_type == list:
                        if isinstance(value, str):
                            corrected_value = json.loads(value)
                        else:
                            corrected_value = list(value)
                    elif isinstance(expected_type, list):
                        # 多种类型，尝试转换为合适的类型
                        if int in expected_type and str(value).isdigit():
                            corrected_value = int(value)
                        elif float in expected_type:
                            corrected_value = float(value)
                        elif str in expected_type:
                            corrected_value = str(value)
                        else:
                            raise ValueError("无法转换类型")
                    else:
                        raise ValueError("无法转换类型")
                    
                    corrected_data[field_name] = corrected_value
                    type_name = expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_TYPE,
                        field_name=field_name,
                        description=f"字段类型不匹配，已自动转换: {field_name}",
                        severity="warning",
                        suggested_fix=f"将 {field_name} 转换为 {type_name}"
                    ))
                    
                except (ValueError, TypeError, json.JSONDecodeError):
                    type_name = expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_TYPE,
                        field_name=field_name,
                        description=f"字段类型无效且无法转换: {field_name}",
                        severity="error",
                        suggested_fix=f"确保 {field_name} 为 {type_name} 类型"
                    ))
    
    def _validate_field_values(self, data: Dict[str, Any], 
                              result: ValidationResult, 
                              corrected_data: Dict[str, Any]):
        """验证字段值"""
        for field_name, value in data.items():
            if field_name not in self._field_schemas:
                continue
            
            schema = self._field_schemas[field_name]
            
            # 字符串长度验证
            if isinstance(value, str):
                min_length = schema.get("min_length", 0)
                max_length = schema.get("max_length", float('inf'))
                
                if len(value) < min_length:
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_VALUE,
                        field_name=field_name,
                        description=f"字段长度过短: {field_name} (最小: {min_length})",
                        severity="error"
                    ))
                
                if len(value) > max_length:
                    # 截断过长的字符串
                    corrected_data[field_name] = value[:max_length]
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_VALUE,
                        field_name=field_name,
                        description=f"字段长度过长，已截断: {field_name}",
                        severity="warning",
                        suggested_fix=f"将 {field_name} 长度限制在 {max_length} 字符内"
                    ))
                
                # 正则表达式验证
                pattern = schema.get("pattern")
                if pattern:
                    import re
                    if not re.match(pattern, value):
                        result.add_issue(ValidationIssue(
                            issue_type=DataIssueType.INVALID_VALUE,
                            field_name=field_name,
                            description=f"字段格式不匹配: {field_name}",
                            severity="error",
                            suggested_fix=f"确保 {field_name} 符合格式要求"
                        ))
            
            # 数值范围验证
            if isinstance(value, (int, float)):
                min_value = schema.get("min_value", float('-inf'))
                max_value = schema.get("max_value", float('inf'))
                
                if value < min_value:
                    corrected_data[field_name] = min_value
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_VALUE,
                        field_name=field_name,
                        description=f"数值过小，已调整为最小值: {field_name}",
                        severity="warning"
                    ))
                
                if value > max_value:
                    corrected_data[field_name] = max_value
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_VALUE,
                        field_name=field_name,
                        description=f"数值过大，已调整为最大值: {field_name}",
                        severity="warning"
                    ))
            
            # 列表验证
            if isinstance(value, list):
                min_items = schema.get("min_items", 0)
                max_items = schema.get("max_items", float('inf'))
                
                if len(value) < min_items:
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_VALUE,
                        field_name=field_name,
                        description=f"列表项目过少: {field_name}",
                        severity="error"
                    ))
                
                if len(value) > max_items:
                    corrected_data[field_name] = value[:max_items]
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_VALUE,
                        field_name=field_name,
                        description=f"列表项目过多，已截断: {field_name}",
                        severity="warning"
                    ))
                
                # 验证列表项类型
                item_type = schema.get("item_type")
                if item_type:
                    for i, item in enumerate(value):
                        if not isinstance(item, item_type):
                            result.add_issue(ValidationIssue(
                                issue_type=DataIssueType.INVALID_TYPE,
                                field_name=f"{field_name}[{i}]",
                                description=f"列表项类型不匹配: {field_name}[{i}]",
                                severity="error"
                            ))
    
    def _validate_data_consistency(self, data: Dict[str, Any], result: ValidationResult):
        """验证数据一致性"""
        # 检查时间戳一致性
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        if created_at and updated_at:
            try:
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                updated_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                
                if updated_time < created_time:
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INCONSISTENT_DATA,
                        field_name="updated_at",
                        description="更新时间早于创建时间",
                        severity="error",
                        suggested_fix="确保更新时间不早于创建时间"
                    ))
            except ValueError:
                result.add_issue(ValidationIssue(
                    issue_type=DataIssueType.INVALID_VALUE,
                    field_name="timestamp",
                    description="时间戳格式无效",
                    severity="error"
                ))
        
        # 检查评分和使用次数的一致性
        rating = data.get("rating", 0)
        usage_count = data.get("usage_count", 0)
        
        # 确保数据类型正确
        try:
            rating = float(rating) if rating is not None else 0.0
            usage_count = int(usage_count) if usage_count is not None else 0
        except (ValueError, TypeError):
            # 如果转换失败，跳过一致性检查
            return
        
        if usage_count > 0 and rating == 0:
            result.add_issue(ValidationIssue(
                issue_type=DataIssueType.INCONSISTENT_DATA,
                field_name="rating",
                description="有使用记录但评分为0，可能存在数据不一致",
                severity="warning",
                suggested_fix="检查评分计算逻辑"
            ))
    
    def _validate_sql_safety(self, data: Dict[str, Any], result: ValidationResult):
        """验证SQL安全性"""
        sql = data.get("sql", "")
        if not sql:
            return
        
        sql_upper = sql.upper()
        
        # 检查危险操作
        dangerous_keywords = [
            "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE",
            "EXEC", "EXECUTE", "CALL", "DECLARE", "GRANT", "REVOKE"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                result.add_issue(ValidationIssue(
                    issue_type=DataIssueType.INVALID_VALUE,
                    field_name="sql",
                    description=f"SQL包含潜在危险操作: {keyword}",
                    severity="error",
                    suggested_fix="移除危险SQL操作，仅保留SELECT查询"
                ))
        
        # 检查SQL注入风险
        injection_patterns = [
            "--", "/*", "*/", ";", "xp_", "sp_", "@@", "char(", "nchar(",
            "varchar(", "nvarchar(", "alter", "begin", "cast", "create", "cursor",
            "declare", "delete", "drop", "end", "exec", "execute", "fetch",
            "insert", "kill", "open", "select", "sys", "sysobjects", "syscolumns",
            "table", "update"
        ]
        
        sql_lower = sql.lower()
        suspicious_patterns = [pattern for pattern in injection_patterns if pattern in sql_lower]
        
        if suspicious_patterns:
            result.add_issue(ValidationIssue(
                issue_type=DataIssueType.INVALID_VALUE,
                field_name="sql",
                description=f"SQL包含可疑模式: {', '.join(suspicious_patterns[:3])}",
                severity="warning",
                suggested_fix="检查SQL是否包含注入风险"
            ))
    
    def _check_duplicate_data(self, data: Dict[str, Any], result: ValidationResult):
        """检查重复数据"""
        # 生成数据哈希
        question = data.get("question", "")
        sql = data.get("sql", "")
        
        content_hash = hashlib.md5(f"{question}_{sql}".encode()).hexdigest()
        
        if content_hash in self._known_hashes:
            result.add_issue(ValidationIssue(
                issue_type=DataIssueType.DUPLICATE_DATA,
                field_name="content",
                description="检测到重复的问题-SQL组合",
                severity="warning",
                suggested_fix="检查是否为重复数据"
            ))
        else:
            self._known_hashes.add(content_hash)
    
    def _validate_data_quality(self, data: Dict[str, Any], result: ValidationResult):
        """验证数据质量"""
        question = data.get("question", "")
        sql = data.get("sql", "")
        
        # 检查问题质量
        if question:
            # 检查是否过于简单
            if len(question.split()) < 3:
                result.add_issue(ValidationIssue(
                    issue_type=DataIssueType.INVALID_VALUE,
                    field_name="question",
                    description="问题过于简单，可能影响搜索效果",
                    severity="info",
                    suggested_fix="提供更详细的问题描述"
                ))
            
            # 检查是否包含有意义的词汇
            meaningful_chars = sum(1 for c in question if c.isalnum())
            if meaningful_chars / len(question) < 0.5:
                result.add_issue(ValidationIssue(
                    issue_type=DataIssueType.INVALID_VALUE,
                    field_name="question",
                    description="问题包含过多无意义字符",
                    severity="warning"
                ))
        
        # 检查SQL质量
        if sql:
            # 检查SQL复杂度
            sql_upper = sql.upper()
            complexity_score = 0
            
            if "JOIN" in sql_upper:
                complexity_score += 2
            if "GROUP BY" in sql_upper:
                complexity_score += 1
            if "ORDER BY" in sql_upper:
                complexity_score += 1
            if "HAVING" in sql_upper:
                complexity_score += 1
            if "UNION" in sql_upper:
                complexity_score += 2
            
            # 过于简单的SQL
            if complexity_score == 0 and len(sql.split()) < 5:
                result.add_issue(ValidationIssue(
                    issue_type=DataIssueType.INVALID_VALUE,
                    field_name="sql",
                    description="SQL过于简单，可能价值有限",
                    severity="info"
                ))
    
    def _validate_metadata_integrity(self, data: Dict[str, Any], result: ValidationResult):
        """验证元数据完整性"""
        # 检查标签的合理性
        tags = data.get("tags", [])
        if isinstance(tags, list):
            # 检查标签重复
            if len(tags) != len(set(tags)):
                result.add_issue(ValidationIssue(
                    issue_type=DataIssueType.DUPLICATE_DATA,
                    field_name="tags",
                    description="标签列表包含重复项",
                    severity="warning",
                    suggested_fix="移除重复标签"
                ))
            
            # 检查标签长度
            for tag in tags:
                if isinstance(tag, str) and len(tag) > 50:
                    result.add_issue(ValidationIssue(
                        issue_type=DataIssueType.INVALID_VALUE,
                        field_name="tags",
                        description=f"标签过长: {tag[:20]}...",
                        severity="warning"
                    ))
    
    def sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理数据
        
        Args:
            data: 原始数据
            
        Returns:
            Dict[str, Any]: 清理后的数据
        """
        validation_result = self.validate_knowledge_item(data)
        
        if validation_result.corrected_data:
            logger.info(f"数据已清理，发现 {len(validation_result.issues)} 个问题")
            return validation_result.corrected_data
        
        return data
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        return {
            "validation_level": self.validation_level.value,
            "known_hashes_count": len(self._known_hashes),
            "field_schemas_count": len(self._field_schemas)
        }
    
    def clear_known_hashes(self):
        """清空已知哈希（用于重置重复检测）"""
        self._known_hashes.clear()
        logger.info("已知数据哈希已清空")

# 全局数据一致性保护器实例
_consistency_guard: Optional[DataConsistencyGuard] = None

def get_consistency_guard() -> DataConsistencyGuard:
    """获取全局数据一致性保护器实例"""
    global _consistency_guard
    
    if _consistency_guard is None:
        _consistency_guard = DataConsistencyGuard()
    
    return _consistency_guard