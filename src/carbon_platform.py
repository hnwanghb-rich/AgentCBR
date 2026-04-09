"""碳盘查平台浏览器控制"""
import time
from typing import List, Dict

class CarbonPlatformBrowser:
    """封装所有与碳排放平台的浏览器交互"""

    def __init__(self, page, logger):
        self.page = page
        self.logger = logger

    def navigate_to_all_projects(self):
        """导航到所有项目页面"""
        try:
            self.logger.read("导航到碳核查管理 > 所有项目")
            # 点击碳核查管理菜单
            self.page.get_by_text("碳核查管理").click()
            time.sleep(0.5)
            self.page.get_by_text("所有项目").click()
            self.page.wait_for_url("**/carbonCheck/all**", timeout=5000)
            time.sleep(1)
            self.logger.read("✓ 已导航到所有项目页面")
            return True
        except Exception as e:
            self.logger.read(f"导航失败: {e}")
            return False

    def get_project_list(self) -> List[Dict]:
        """获取项目列表"""
        projects = []
        try:
            self.page.wait_for_selector("table tbody tr", timeout=10000)
            rows = self.page.query_selector_all("table tbody tr")

            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) >= 6:
                    projects.append({
                        "序号": cells[1].inner_text().strip(),
                        "名称": cells[2].inner_text().strip(),
                        "提交单位": cells[3].inner_text().strip(),
                        "当前处理节点": cells[7].inner_text().strip() if len(cells) > 7 else "",
                    })

            self.logger.read(f"找到 {len(projects)} 个项目")
        except Exception as e:
            self.logger.read(f"获取项目列表失败: {e}")

        return projects

    def open_project(self, row_index: int):
        """点击查看按钮打开指定项目"""
        try:
            view_btns = self.page.query_selector_all("button:has-text('查看')")
            if row_index < len(view_btns):
                view_btns[row_index].click()
                self.page.wait_for_url("**/projectfactorList**", timeout=5000)
                time.sleep(1)
                return True
        except Exception as e:
            self.logger.read(f"打开项目失败: {e}")
        return False

    def get_project_overview(self) -> Dict:
        """获取项目概况信息"""
        try:
            # 点击项目概况
            self.page.get_by_text("项目概况").click()
            time.sleep(1.5)

            # 提取所有字段
            info = self.page.evaluate("""
            () => {
                const dialog = document.querySelector('.simple-dialog-container') ||
                               document.querySelector('.el-dialog');
                if (!dialog) return {};

                const result = {};
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
            close_btn = self.page.query_selector("button:has-text('关闭')")
            if close_btn and close_btn.is_visible():
                close_btn.click()
            else:
                self.page.query_selector(".el-dialog__headerbtn").click()
            time.sleep(0.5)

            return info
        except Exception as e:
            self.logger.read(f"获取项目概况失败: {e}")
            return {}

    def get_category_data(self, category: str) -> Dict:
        """切换到指定分类并提取数据"""
        try:
            # 点击分类标签
            tab = self.page.query_selector(f"button:has-text('{category}')")
            if tab:
                tab.click()
                time.sleep(1)

            # 提取表格数据
            data = self.page.evaluate("""
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
        except Exception as e:
            self.logger.read(f"获取 {category} 数据失败: {e}")
            return {"total": 0, "records": []}

    def go_back(self):
        """返回项目列表"""
        try:
            back_btn = self.page.query_selector("button:has-text('返回')")
            if back_btn:
                back_btn.click()
                self.page.wait_for_url("**/carbonCheck/all**", timeout=5000)
                time.sleep(1)
                return True
        except Exception as e:
            self.logger.read(f"返回失败: {e}")
        return False
