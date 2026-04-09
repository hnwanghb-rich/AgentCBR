"""碳盘查审核引擎"""
from typing import List, Dict, Tuple

class CarbonAuditor:
    """基于规则的碳盘查审核引擎"""

    # 审核规则配置
    RULES = {
        "building_area_range": (5000, 2000000),
        "public_area_ratio": {
            "住宅": (0.25, 0.50),
            "住宅-社区": (0.25, 0.50),
            "商业": (0.30, 0.60),
        },
        "allowed_fixed_source_types": ["柴油", "汽油", "天然气", "液化石油气"],
        "fixed_source_required_subcategory": "办公生活",
        "allowed_mobile_source_types": ["汽油"],
        "mandatory_energy": "办公生活-净外购电网电力",
        "heat_energy_regions": ["东北", "华北", "西北"],
        "required_monthly_records": 12,
        "category_tabs": [
            "生产经营数据", "固定源", "移动源", "机械台班",
            "能源", "采购建材", "过程排放", "节能降碳措施", "碳资产信息"
        ],
    }

    def __init__(self):
        self.issues = []
        self.data_log = {}

    def reset(self):
        """重置审核状态"""
        self.issues = []
        self.data_log = {}

    def check_building_area(self, area: float):
        """检查建筑面积范围"""
        min_area, max_area = self.RULES["building_area_range"]
        if area < min_area or area > max_area:
            self.issues.append(
                f"建筑面积 {area} m² 超出合规范围 ({min_area}-{max_area} m²)"
            )
            return False
        return True

    def check_public_area_ratio(self, public_area: float, total_area: float,
                                 project_function: str):
        """检查公区面积占比"""
        if total_area == 0:
            self.issues.append("总建筑面积为0，无法计算公区面积占比")
            return False

        ratio = public_area / total_area
        for func_key, (min_r, max_r) in self.RULES["public_area_ratio"].items():
            if func_key in project_function:
                if ratio < min_r or ratio > max_r:
                    self.issues.append(
                        f"公区面积占比 {ratio:.1%} 不在 {func_key} 类项目"
                        f"要求的 {min_r:.0%}-{max_r:.0%} 范围内"
                    )
                    return False
                return True
        return True

    def check_fixed_sources(self, records: List[Dict]):
        """检查固定源合规性"""
        allowed = self.RULES["allowed_fixed_source_types"]
        required_sub = self.RULES["fixed_source_required_subcategory"]

        for r in records:
            name = r.get("名称", "")
            subcategory = r.get("小类", "")
            consumption = r.get("资源消耗", "")

            has_data = bool(consumption) and not consumption.endswith(
                ("t", "万立方米", "%", "GJ", "MWh")
            )

            if has_data or any(c.isdigit() for c in consumption):
                if not any(a in name for a in allowed):
                    self.issues.append(
                        f"固定源类型 '{name}' 不在允许列表内"
                        f"（仅允许：{', '.join(allowed)}），"
                        f"消耗量: {consumption}"
                    )

                if subcategory != required_sub:
                    self.issues.append(
                        f"固定源 '{name}' 小类为 '{subcategory}'，"
                        f"应为 '{required_sub}'"
                    )

    def check_mobile_sources(self, records: List[Dict]):
        """检查移动源合规性"""
        allowed = self.RULES["allowed_mobile_source_types"]

        for r in records:
            name = r.get("名称", "")
            consumption = r.get("资源消耗", "")

            if consumption and any(c.isdigit() for c in consumption):
                if not any(a in name for a in allowed):
                    self.issues.append(
                        f"移动源类型 '{name}' 不在允许列表内"
                        f"（仅允许：{', '.join(allowed)}）"
                    )

    def check_energy(self, records: List[Dict], project_region: str):
        """检查能源数据"""
        mandatory = self.RULES["mandatory_energy"]
        heat_regions = self.RULES["heat_energy_regions"]

        has_mandatory = False
        for r in records:
            name = r.get("名称", "")
            subcategory = r.get("小类", "")
            consumption = r.get("资源消耗", "")

            if "净外购电网电力" in name and "办公生活" in subcategory:
                if consumption and any(c.isdigit() for c in consumption):
                    has_mandatory = True
                else:
                    self.issues.append(
                        f"'{mandatory}' 为必填项但缺少消耗数据"
                    )

            if "净外购热力" in name and consumption and any(
                c.isdigit() for c in consumption
            ):
                if not any(region in project_region for region in heat_regions):
                    self.issues.append(
                        f"项目位于 {project_region}，净外购热力仅适用于"
                        f"{'、'.join(heat_regions)}地区，"
                        f"但填报了 {consumption}"
                    )

        if not has_mandatory:
            self.issues.append(f"缺少必填能源项: {mandatory}")

    def check_conservation(self, records: List[Dict]):
        """检查节能降碳措施必填项"""
        for r in records:
            name = r.get("名称", "")
            consumption = r.get("资源消耗", "")

            if "是1/否0" in name:
                if not consumption or consumption.strip() == "":
                    self.issues.append(
                        f"节能降碳必填项 '{r.get('小类', '')}' 未填写"
                    )

    def get_verdict(self) -> Tuple[str, List[str]]:
        """获取审核结论"""
        if self.issues:
            return "驳回", self.issues
        return "通过", []
