"""碳排放数据审核模块"""
import pandas as pd
from typing import List, Dict, Any

class EmissionDataAuditor:
    """碳排放数据审核器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.threshold = config.get('threshold', 0.3)  # 默认30%阈值

    def audit_data(self, current_data: pd.DataFrame, historical_data: pd.DataFrame = None) -> List[Dict]:
        """审核碳排放数据，返回问题列表"""
        issues = []

        # 1. 数据缺失检测
        issues.extend(self._check_missing_data(current_data))

        # 2. 单位异常检测
        issues.extend(self._check_unit_anomaly(current_data))

        # 3. 极值检测
        issues.extend(self._check_extreme_values(current_data))

        # 4. 同比突增突降检测（需要历史数据）
        if historical_data is not None:
            issues.extend(self._check_yoy_change(current_data, historical_data))

        return issues

    def _check_missing_data(self, df: pd.DataFrame) -> List[Dict]:
        """检测数据缺失"""
        issues = []
        required_fields = ['项目名称', '城市', '产值', '碳排放量']

        for idx, row in df.iterrows():
            for field in required_fields:
                if pd.isna(row.get(field)) or str(row.get(field)).strip() == '':
                    issues.append({
                        'project': row.get('项目名称', f'行{idx+1}'),
                        'company': row.get('二级公司', ''),
                        'city': row.get('城市', ''),
                        'issue_type': '数据缺失',
                        'field': field,
                        'description': f'{field}未填写',
                        'suggestion': f'请补充{field}信息',
                        'priority': '高'
                    })
        return issues

    def _check_unit_anomaly(self, df: pd.DataFrame) -> List[Dict]:
        """检测单位异常（如kWh误填为MWh）"""
        issues = []
        for idx, row in df.iterrows():
            emission = row.get('碳排放量', 0)
            if pd.notna(emission) and float(emission) > 100000:  # 异常大值
                issues.append({
                    'project': row.get('项目名称', f'行{idx+1}'),
                    'company': row.get('二级公司', ''),
                    'city': row.get('城市', ''),
                    'issue_type': '单位异常',
                    'field': '碳排放量',
                    'description': f'碳排放量异常大: {emission}，可能单位错误',
                    'suggestion': '请检查单位是否正确（kWh/MWh）',
                    'priority': '高'
                })
        return issues

    def _check_extreme_values(self, df: pd.DataFrame) -> List[Dict]:
        """检测极值"""
        issues = []
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if col in ['碳排放量', '产值', '用电量']:
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 3 * iqr
                upper = q3 + 3 * iqr

                outliers = df[(df[col] < lower) | (df[col] > upper)]
                for idx, row in outliers.iterrows():
                    issues.append({
                        'project': row.get('项目名称', f'行{idx+1}'),
                        'company': row.get('二级公司', ''),
                        'city': row.get('城市', ''),
                        'issue_type': '极值异常',
                        'field': col,
                        'description': f'{col}为极值: {row[col]}',
                        'suggestion': '请核实数据准确性',
                        'priority': '中'
                    })
        return issues

    def _check_yoy_change(self, current: pd.DataFrame, historical: pd.DataFrame) -> List[Dict]:
        """检测同比突增突降"""
        issues = []
        for idx, curr_row in current.iterrows():
            project = curr_row.get('项目名称')
            hist_row = historical[historical['项目名称'] == project]

            if hist_row.empty:
                continue

            hist_row = hist_row.iloc[0]
            curr_emission = curr_row.get('碳排放量', 0)
            hist_emission = hist_row.get('碳排放量', 0)

            if hist_emission > 0:
                change_rate = (curr_emission - hist_emission) / hist_emission
                if abs(change_rate) > self.threshold:
                    issues.append({
                        'project': project,
                        'company': curr_row.get('二级公司', ''),
                        'city': curr_row.get('城市', ''),
                        'issue_type': '同比异常',
                        'field': '碳排放量',
                        'description': f'同比变化{change_rate*100:.1f}%（当前:{curr_emission}, 历史:{hist_emission}）',
                        'suggestion': '请说明变化原因',
                        'priority': '中'
                    })
        return issues
