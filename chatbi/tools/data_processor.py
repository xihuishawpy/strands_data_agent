"""
数据处理工具
提供数据清洗、转换、聚合等功能
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataProcessor:
    """数据处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        清洗数据
        
        Args:
            data: 原始数据
            
        Returns:
            List[Dict[str, Any]]: 清洗后的数据
        """
        try:
            if not data:
                return data
            
            df = pd.DataFrame(data)
            
            # 处理空值
            df = df.fillna('')
            
            # 转换数据类型
            for col in df.columns:
                # 尝试转换数值类型
                if df[col].dtype == 'object':
                    # 检查是否可以转换为数值
                    try:
                        numeric_series = pd.to_numeric(df[col], errors='coerce')
                        if not numeric_series.isna().all():
                            df[col] = numeric_series.fillna(df[col])
                    except:
                        pass
                    
                    # 检查是否可以转换为日期
                    try:
                        date_series = pd.to_datetime(df[col], errors='coerce')
                        if not date_series.isna().all():
                            df[col] = date_series.fillna(df[col])
                    except:
                        pass
            
            return df.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"数据清洗失败: {str(e)}")
            return data
    
    def aggregate_data(self, 
                      data: List[Dict[str, Any]], 
                      group_by: Union[str, List[str]], 
                      aggregations: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        聚合数据
        
        Args:
            data: 数据
            group_by: 分组字段
            aggregations: 聚合规则，如 {'amount': 'sum', 'count': 'count'}
            
        Returns:
            List[Dict[str, Any]]: 聚合后的数据
        """
        try:
            if not data:
                return []
            
            df = pd.DataFrame(data)
            
            # 执行聚合
            if isinstance(group_by, str):
                group_by = [group_by]
            
            grouped = df.groupby(group_by)
            
            # 应用聚合函数
            agg_result = {}
            for col, func in aggregations.items():
                if col in df.columns:
                    if func == 'sum':
                        agg_result[col] = grouped[col].sum()
                    elif func == 'count':
                        agg_result[col] = grouped[col].count()
                    elif func == 'mean' or func == 'avg':
                        agg_result[col] = grouped[col].mean()
                    elif func == 'max':
                        agg_result[col] = grouped[col].max()
                    elif func == 'min':
                        agg_result[col] = grouped[col].min()
                    elif func == 'std':
                        agg_result[col] = grouped[col].std()
            
            # 组合结果
            result_df = pd.DataFrame(agg_result).reset_index()
            return result_df.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"数据聚合失败: {str(e)}")
            return data
    
    def filter_data(self, 
                   data: List[Dict[str, Any]], 
                   filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        过滤数据
        
        Args:
            data: 数据
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 过滤后的数据
        """
        try:
            if not data or not filters:
                return data
            
            df = pd.DataFrame(data)
            
            for column, condition in filters.items():
                if column not in df.columns:
                    continue
                
                if isinstance(condition, dict):
                    # 复杂条件
                    if 'gt' in condition:  # 大于
                        df = df[df[column] > condition['gt']]
                    if 'gte' in condition:  # 大于等于
                        df = df[df[column] >= condition['gte']]
                    if 'lt' in condition:  # 小于
                        df = df[df[column] < condition['lt']]
                    if 'lte' in condition:  # 小于等于
                        df = df[df[column] <= condition['lte']]
                    if 'eq' in condition:  # 等于
                        df = df[df[column] == condition['eq']]
                    if 'ne' in condition:  # 不等于
                        df = df[df[column] != condition['ne']]
                    if 'in' in condition:  # 包含
                        df = df[df[column].isin(condition['in'])]
                    if 'contains' in condition:  # 包含字符串
                        df = df[df[column].str.contains(condition['contains'], na=False)]
                else:
                    # 简单条件（等于）
                    df = df[df[column] == condition]
            
            return df.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"数据过滤失败: {str(e)}")
            return data
    
    def sort_data(self, 
                 data: List[Dict[str, Any]], 
                 sort_by: Union[str, List[str]], 
                 ascending: Union[bool, List[bool]] = True) -> List[Dict[str, Any]]:
        """
        排序数据
        
        Args:
            data: 数据
            sort_by: 排序字段
            ascending: 是否升序
            
        Returns:
            List[Dict[str, Any]]: 排序后的数据
        """
        try:
            if not data:
                return data
            
            df = pd.DataFrame(data)
            
            # 执行排序
            df_sorted = df.sort_values(by=sort_by, ascending=ascending)
            
            return df_sorted.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"数据排序失败: {str(e)}")
            return data
    
    def pivot_data(self, 
                  data: List[Dict[str, Any]], 
                  index: str, 
                  columns: str, 
                  values: str, 
                  aggfunc: str = 'sum') -> List[Dict[str, Any]]:
        """
        数据透视
        
        Args:
            data: 数据
            index: 行索引字段
            columns: 列字段
            values: 值字段
            aggfunc: 聚合函数
            
        Returns:
            List[Dict[str, Any]]: 透视后的数据
        """
        try:
            if not data:
                return []
            
            df = pd.DataFrame(data)
            
            # 执行透视
            pivot_df = df.pivot_table(
                index=index,
                columns=columns,
                values=values,
                aggfunc=aggfunc,
                fill_value=0
            )
            
            # 重置索引并转换为字典列表
            pivot_df = pivot_df.reset_index()
            pivot_df.columns.name = None
            
            return pivot_df.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"数据透视失败: {str(e)}")
            return data
    
    def calculate_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算统计信息
        
        Args:
            data: 数据
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            if not data:
                return {}
            
            df = pd.DataFrame(data)
            
            stats = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'numeric_columns': [],
                'text_columns': [],
                'date_columns': []
            }
            
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    stats['numeric_columns'].append({
                        'column': col,
                        'count': df[col].count(),
                        'mean': df[col].mean(),
                        'std': df[col].std(),
                        'min': df[col].min(),
                        'max': df[col].max(),
                        'null_count': df[col].isnull().sum()
                    })
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    stats['date_columns'].append({
                        'column': col,
                        'count': df[col].count(),
                        'min_date': df[col].min(),
                        'max_date': df[col].max(),
                        'null_count': df[col].isnull().sum()
                    })
                else:
                    stats['text_columns'].append({
                        'column': col,
                        'count': df[col].count(),
                        'unique_count': df[col].nunique(),
                        'most_frequent': df[col].mode().iloc[0] if not df[col].mode().empty else None,
                        'null_count': df[col].isnull().sum()
                    })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"统计计算失败: {str(e)}")
            return {}
    
    def detect_anomalies(self, 
                        data: List[Dict[str, Any]], 
                        column: str, 
                        method: str = 'iqr') -> List[Dict[str, Any]]:
        """
        检测异常值
        
        Args:
            data: 数据
            column: 检测的列
            method: 检测方法 ('iqr', 'zscore')
            
        Returns:
            List[Dict[str, Any]]: 异常值数据
        """
        try:
            if not data:
                return []
            
            df = pd.DataFrame(data)
            
            if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
                return []
            
            if method == 'iqr':
                # 使用四分位距方法
                Q1 = df[column].quantile(0.25)
                Q3 = df[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                anomalies = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
                
            elif method == 'zscore':
                # 使用Z分数方法
                z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
                anomalies = df[z_scores > 3]
            
            else:
                return []
            
            return anomalies.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"异常值检测失败: {str(e)}")
            return []
    
    def format_for_display(self, data: List[Dict[str, Any]], max_rows: int = 100) -> Dict[str, Any]:
        """
        格式化数据以供显示
        
        Args:
            data: 数据
            max_rows: 最大显示行数
            
        Returns:
            Dict[str, Any]: 格式化后的数据信息
        """
        try:
            if not data:
                return {
                    "data": [],
                    "total_rows": 0,
                    "displayed_rows": 0,
                    "columns": []
                }
            
            # 限制显示行数
            displayed_data = data[:max_rows]
            
            # 获取列信息
            columns = list(data[0].keys()) if data else []
            
            return {
                "data": displayed_data,
                "total_rows": len(data),
                "displayed_rows": len(displayed_data),
                "columns": columns,
                "truncated": len(data) > max_rows
            }
            
        except Exception as e:
            self.logger.error(f"数据格式化失败: {str(e)}")
            return {
                "data": data,
                "total_rows": len(data) if data else 0,
                "displayed_rows": len(data) if data else 0,
                "columns": [],
                "error": str(e)
            }

# 全局数据处理器实例
_data_processor: Optional[DataProcessor] = None

def get_data_processor() -> DataProcessor:
    """获取全局数据处理器实例"""
    global _data_processor
    
    if _data_processor is None:
        _data_processor = DataProcessor()
    
    return _data_processor 