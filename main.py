"""
碳盘查自动审核系统 - 主入口
使用 Playwright 自动化浏览器操作，按规则审核碳排放项目
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

# ============================================================
# 配置
# ============================================================
PLATFORM_URL = "https://cc.cscec.com/"
USERNAME = os.getenv("CARBON_USERNAME", "测试公司")
PASSWORD = os.getenv("CARBON_PASSWORD", "KzmPJDswrr_8gj")
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

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


# ============================================================
# 浏览器控制层
# ============================================================
class CarbonPlatformBrowser:
    """封装所有与碳排放平台的浏览器交互"""

    def __init__(self, page):
        self.page = page

    async def login(self):
        """登录平台"""
        await self.page.goto(PLATFORM_URL)
        await self.page.wait_for_load_state("networkidle")

        # 填入用户名密码
        username_input = self.page.locator("input[placeholder='账号']").first
        password_input = self.page.locator("input[placeholder='密码']").first
        await username_input.fill(USERNAME)
        await password_input.fill(PASSWORD)

        # 点击登录
        await self.page.get_by_role("button", name="登 录").click()
        await self.page.wait_for_url("**/index**", timeout=10000)
        print("✅ 登录成功")

    async def navigate_to_all_projects(self):
        """导航到所有项目页面"""
        # 展开碳核查管理菜单
        await self.page.get_by_text("碳核查管理").click()
        await self.page.wait_for_timeout(500)
        await self.page.get_by_text("所有项目").click()
        await self.page.wait_for_url("**/carbonCheck/all**", timeout=5000)
        await self.page.wait_for_timeout(1000)
        print("✅ 已导航到所有项目页面")

    async def get_project_list(self):
        """获取项目列表"""
        projects = []
        rows = await self.page.locator("table tbody tr").all()
        for row in rows:
            cells = await row.locator("td").all()
            if len(cells) >= 6:
                projects.append({
                    "序号": await cells[1].text_content(),
                    "名称": (await cells[2].text_content()).strip(),
                    "提交单位": (await cells[3].text_content()).strip(),
                    "当前处理节点": (await cells[7].text_content()).strip(),
                })
        return projects

    async def open_project(self, row_index: int):
        """点击查看按钮打开指定项目"""
        view_btns = await self.page.get_by_role("button", name="查看").all()
        if row_index < len(view_btns):
            await view_btns[row_index].click()
            await self.page.wait_for_url("**/projectfactorList**", timeout=5000)
            await self.page.wait_for_timeout(1000)

    async def get_project_overview(self):
        """获取项目概况信息"""
        # 点击项目概况
        await self.page.get_by_text("项目概况").click()
        await self.page.wait_for_timeout(1500)

        # 使用JavaScript提取所有字段
        info = await self.page.evaluate("""
        () => {
            const dialog = document.querySelector('.simple-dialog-container') ||
                           document.querySelector('.el-dialog');
            if (!dialog) return {};

            const result = {};
            const labels = dialog.querySelectorAll('label, .label, [class*="label"]');

            // 获取所有input和select的值
            const inputs = dialog.querySelectorAll('input, select, .el-input__inner');
            inputs.forEach(input => {
                const label = input.closest('.el-form-item')?.querySelector('label')?.textContent?.trim();
                if (label) {
                    result[label] = input.value || input.textContent?.trim();
                }
            });

            return result;
        }
        """)

        # 关闭弹窗
        close_btn = self.page.locator("button:has-text('关闭')").first
        if await close_btn.is_visible():
            await close_btn.click()
        else:
            await self.page.locator(".el-dialog__headerbtn").first.click()
        await self.page.wait_for_timeout(500)

        return info

    async def get_category_data(self, category: str):
        """切换到指定分类并提取数据"""
        # 点击分类标签
        tab = self.page.get_by_role("button", name=category).first
        await tab.click()
        await self.page.wait_for_timeout(1000)

        # 提取表格数据
        data = await self.page.evaluate("""
        () => {
            const rows = document.querySelectorAll('.app-main-content table tbody tr');
            const records = [];
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length > 2) {
                    records.push({
                        序号: cells[1]?.textContent?.trim(),
                        类别: cells[3]?.textContent?.trim(),
                        小类: cells[4]?.textContent?.trim(),
                        名称: cells[5]?.textContent?.trim(),
                        规格: cells[6]?.textContent?.trim(),
                        资源消耗: cells[8]?.textContent?.trim(),
                        排放量: cells[9]?.textContent?.trim(),
                    });
                }
            });
            const totalMatch = document.querySelector('.el-pagination')
                ?.textContent?.match(/共\\s*(\\d+)\\s*条/);
            return {
                total: totalMatch ? parseInt(totalMatch[1]) : records.length,
                records: records
            };
        }
        """)
        return data

    async def get_record_count(self, category_name: str):
        """获取某个记录的填报记录条数（如当年产值的月度记录数）"""
        # 点击查看记录按钮
        # 这需要先定位到对应行的查看记录按钮
        pass

    async def go_back(self):
        """返回项目列表"""
        back_btn = self.page.get_by_role("button", name="返回").first
        await back_btn.click()
        await self.page.wait_for_url("**/carbonCheck/all**", timeout=5000)
        await self.page.wait_for_timeout(1000)


# ============================================================
# 审核引擎
# ============================================================
class CarbonAuditor:
    """基于规则的碳盘查审核引擎"""

    def __init__(self):
        self.issues = []  # 存储发现的问题
        self.data_log = {}  # 存储审核过程中的数据

    def reset(self):
        self.issues = []
        self.data_log = {}

    def check_building_area(self, area: float):
        """检查建筑面积范围"""
        min_area, max_area = RULES["building_area_range"]
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
        for func_key, (min_r, max_r) in RULES["public_area_ratio"].items():
            if func_key in project_function:
                if ratio < min_r or ratio > max_r:
                    self.issues.append(
                        f"公区面积占比 {ratio:.1%} 不在 {func_key} 类项目"
                        f"要求的 {min_r:.0%}-{max_r:.0%} 范围内"
                    )
                    return False
                return True
        return True  # 未匹配到类型，跳过检查

    def check_fixed_sources(self, records: list):
        """检查固定源合规性"""
        allowed = RULES["allowed_fixed_source_types"]
        required_sub = RULES["fixed_source_required_subcategory"]

        for r in records:
            name = r.get("名称", "")
            subcategory = r.get("小类", "")
            consumption = r.get("资源消耗", "")

            # 检查是否有实际消耗数据
            has_data = bool(consumption) and not consumption.endswith(
                ("t", "万立方米", "%", "GJ", "MWh")
            )

            # 仅检查有数据的记录
            if has_data or any(c.isdigit() for c in consumption):
                # 检查类型是否允许
                if not any(a in name for a in allowed):
                    self.issues.append(
                        f"固定源类型 '{name}' 不在允许列表内"
                        f"（仅允许：{', '.join(allowed)}），"
                        f"消耗量: {consumption}"
                    )

                # 检查小类
                if subcategory != required_sub:
                    self.issues.append(
                        f"固定源 '{name}' 小类为 '{subcategory}'，"
                        f"应为 '{required_sub}'"
                    )

    def check_energy(self, records: list, project_region: str):
        """检查能源数据"""
        mandatory = RULES["mandatory_energy"]
        heat_regions = RULES["heat_energy_regions"]

        has_mandatory = False
        for r in records:
            name = r.get("名称", "")
            subcategory = r.get("小类", "")
            consumption = r.get("资源消耗", "")
            full_name = f"{subcategory}-{name}"

            # 检查必填项
            if "净外购电网电力" in name and "办公生活" in subcategory:
                # 检查是否有实际数据
                if consumption and any(c.isdigit() for c in consumption):
                    has_mandatory = True
                else:
                    self.issues.append(
                        f"'{mandatory}' 为必填项但缺少消耗数据"
                    )

            # 检查净外购热力的区域限制
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

    def check_conservation(self, records: list):
        """检查节能降碳措施必填项"""
        for r in records:
            name = r.get("名称", "")
            consumption = r.get("资源消耗", "")

            if "是1/否0" in name:
                if not consumption or consumption.strip() == "":
                    self.issues.append(
                        f"节能降碳必填项 '{r.get('小类', '')}' 未填写"
                    )

    def get_verdict(self):
        """获取审核结论"""
        if self.issues:
            return "驳回", self.issues
        return "通过", []


# ============================================================
# 报告生成
# ============================================================
class AuditReporter:
    """生成审核报告"""

    @staticmethod
    def generate_log(project_name: str, project_info: dict,
                     category_data: dict, verdict: str,
                     issues: list) -> str:
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

    @staticmethod
    def save_log(project_name: str, content: str):
        """保存日志文件"""
        safe_name = project_name.replace("/", "_").replace("\\", "_")
        filepath = LOG_DIR / f"{safe_name}_审核日志.txt"
        filepath.write_text(content, encoding="utf-8")
        print(f"📝 日志已保存: {filepath}")
        return filepath


# ============================================================
# 主流程
# ============================================================
async def main():
    """主审核流程"""
    print("🚀 碳盘查自动审核系统启动")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    async with async_playwright() as p:
        # 启动浏览器（headless=False 可看到操作过程）
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        platform = CarbonPlatformBrowser(page)
        reporter = AuditReporter()

        try:
            # 1. 登录
            await platform.login()

            # 2. 导航到所有项目
            await platform.navigate_to_all_projects()

            # 3. 获取项目列表
            projects = await platform.get_project_list()
            print(f"📋 共找到 {len(projects)} 个项目")

            # 4. 逐项审核
            results = []
            for i, project in enumerate(projects):
                print(f"\n{'='*50}")
                print(f"🔍 审核项目 {i+1}/{len(projects)}: {project['名称']}")

                auditor = CarbonAuditor()

                # 打开项目
                await platform.open_project(i)

                # 获取项目概况
                overview = await platform.get_project_overview()

                # TODO: 从overview中提取具体字段做检查
                # auditor.check_building_area(...)
                # auditor.check_public_area_ratio(...)

                # 逐分类获取数据
                category_data = {}
                for category in ["生产经营数据", "固定源", "能源", "节能降碳措施"]:
                    try:
                        data = await platform.get_category_data(category)
                        category_data[category] = data

                        # 按分类执行审核
                        if category == "固定源":
                            auditor.check_fixed_sources(data.get("records", []))
                        elif category == "能源":
                            region = overview.get("项目区域", "")
                            auditor.check_energy(data.get("records", []), region)
                        elif category == "节能降碳措施":
                            auditor.check_conservation(data.get("records", []))
                    except Exception as e:
                        print(f"  ⚠️ 获取 {category} 数据失败: {e}")

                # 获取审核结论
                verdict, issues = auditor.get_verdict()
                results.append({
                    "项目": project["名称"],
                    "结果": verdict,
                    "问题数": len(issues),
                })

                # 生成并保存日志
                log_content = reporter.generate_log(
                    project["名称"], overview, category_data, verdict, issues
                )
                reporter.save_log(project["名称"], log_content)

                print(f"  📋 审核结果: {verdict} (发现 {len(issues)} 个问题)")

                # 返回项目列表
                await platform.go_back()

            # 5. 输出汇总
            print(f"\n{'='*50}")
            print("📊 审核汇总")
            print(f"{'='*50}")
            for r in results:
                emoji = "✅" if r["结果"] == "通过" else "❌"
                print(f"  {emoji} {r['项目']} - {r['结果']} ({r['问题数']} 个问题)")

        except Exception as e:
            print(f"❌ 审核过程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    print(f"\n🏁 审核完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
