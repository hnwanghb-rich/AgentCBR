"""审核报告生成器"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class AuditReporter:
    """生成审核报告"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_log(self, project_name: str, project_info: Dict,
                     category_data: Dict, verdict: str,
                     issues: List[str]) -> str:
        """生成审核日志文本"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=" * 50,
            "碳盘查审核日志",
            "=" * 50,
            f"项目名称: {project_name}",
            f"审核时间: {timestamp}",
            f"审核结果: {verdict}",
            "",
        ]

        if issues:
            lines.append("【驳回原因】")
            for i, issue in enumerate(issues, 1):
                lines.append(f"  {i}. {issue}")
            lines.append("")

        lines.append("【项目基础信息】")
        for key, value in project_info.items():
            lines.append(f"  {key}: {value}")
        lines.append("")

        for category, data in category_data.items():
            lines.append(f"【{category}】(共{data.get('total', 0)}条)")
            for record in data.get("records", [])[:10]:
                lines.append(
                    f"  - {record.get('小类', '')}/{record.get('名称', '')} "
                    f"= {record.get('资源消耗', '无数据')}"
                )
            if data.get("total", 0) > 10:
                lines.append(f"  ... (更多记录省略)")
            lines.append("")

        lines.append("=" * 50)
        return "\n".join(lines)

    def save_log(self, project_name: str, content: str) -> Path:
        """保存日志文件"""
        safe_name = project_name.replace("/", "_").replace("\\", "_")
        filepath = self.output_dir / f"{safe_name}_审核日志.txt"
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def save_summary(self, results: List[Dict]):
        """保存审核汇总"""
        import pandas as pd

        df = pd.DataFrame(results)
        filepath = self.output_dir / f"审核汇总_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filepath, index=False)
        return filepath
