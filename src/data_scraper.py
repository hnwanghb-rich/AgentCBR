"""数据抓取模块"""
from typing import List, Dict
import pandas as pd
import time

class DataScraper:
    """数据抓取器"""

    def __init__(self, page, logger):
        self.page = page
        self.logger = logger

    def get_tree_nodes(self) -> List[str]:
        """获取左侧树节点"""
        try:
            nodes = self.page.query_selector_all('.el-tree-node__content')
            node_texts = []
            for node in nodes:
                text = ' '.join(node.inner_text().split()).strip()
                if text:
                    node_texts.append(text)
            self.logger.read(f"找到 {len(node_texts)} 个树节点")
            return node_texts
        except Exception as e:
            self.logger.read(f"获取树节点失败: {e}")
            return []

    def click_tree_node(self, node_text: str) -> bool:
        """点击树节点"""
        try:
            clicked = self.page.evaluate("""
                (target) => {
                    const nodes = document.querySelectorAll('.el-tree-node__content');
                    for (const node of nodes) {
                        const text = node.innerText.replace(/[\\r\\n\\u3000]+/g, ' ').replace(/\\s+/g, ' ').trim();
                        if (text === target) {
                            node.click();
                            return true;
                        }
                    }
                    return false;
                }
            """, node_text)

            if clicked:
                time.sleep(1)  # 等待渲染
                self.logger.read(f"✓ 已点击树节点: {node_text}")
                return True
            else:
                self.logger.read(f"✗ 未找到树节点: {node_text}")
                return False
        except Exception as e:
            self.logger.read(f"点击树节点失败: {e}")
            return False

    def scrape_table_with_drill_down(self) -> List[Dict]:
        """抓取表格数据，并点击"进入"按钮进入下级"""
        all_data = []

        try:
            # 等待表格加载
            self.page.wait_for_selector('table tbody tr', timeout=5000)

            idx = 0
            while idx < 5:  # 处理前5行
                # 每次重新查询行元素
                rows = self.page.query_selector_all('table tbody tr')
                if idx >= len(rows):
                    break

                row = rows[idx]
                self.logger.read(f"\n处理第 {idx + 1} 行...")

                # 查找"进入"按钮
                enter_btn = None
                btns = row.query_selector_all('a, button, span')
                for btn in btns:
                    text = ''.join(btn.inner_text().split())
                    if '进入' in text:
                        enter_btn = btn
                        break

                if enter_btn:
                    # 读取href或点击
                    href = enter_btn.get_attribute('href')
                    if href and href.startswith('http'):
                        self.page.goto(href, timeout=30000)
                    else:
                        enter_btn.click()

                    time.sleep(1)
                    self.logger.read(f"✓ 已进入下级页面: {self.page.url}")

                    # 抓取下级数据
                    sub_data = self.scrape_current_table()
                    all_data.extend(sub_data)

                    # 返回上级
                    self.page.go_back()
                    time.sleep(1)
                    self.logger.read("✓ 已返回上级")
                else:
                    self.logger.read("  无'进入'按钮，跳过")

                idx += 1

        except Exception as e:
            self.logger.read(f"✗ 抓取失败: {e}")

        return all_data

    def scrape_current_table(self) -> List[Dict]:
        """抓取当前页面的表格数据（含翻页）"""
        all_data = []
        page_num = 1

        try:
            while True:
                self.page.wait_for_selector('table tbody tr', timeout=5000)
                headers = [h.inner_text().strip() for h in self.page.query_selector_all('table thead th')]
                rows = self.page.query_selector_all('table tbody tr')

                page_data = []
                for row in rows:
                    cells = [c.inner_text().strip() for c in row.query_selector_all('td')]
                    if cells:
                        row_dict = dict(zip(headers, cells))
                        page_data.append(row_dict)

                all_data.extend(page_data)
                self.logger.read(f"  第{page_num}页: {len(page_data)} 条数据")

                # 查找下一页按钮
                next_btn = None
                try:
                    next_btn = self.page.query_selector('button.el-pagination__next:not([disabled])')
                    if next_btn and next_btn.is_visible():
                        next_btn.click()
                        time.sleep(1)
                        page_num += 1
                    else:
                        break
                except:
                    break

            self.logger.read(f"  共抓取 {len(all_data)} 条数据（{page_num}页）")
        except Exception as e:
            self.logger.read(f"  抓取表格失败: {e}")

        return all_data


    def scrape_project_list(self) -> pd.DataFrame:
        """抓取项目列表数据"""
        self.logger.read("开始抓取项目列表...")

        try:
            # 等待表格加载
            self.page.wait_for_selector('table tbody tr', timeout=10000)

            # 获取表头
            headers = []
            header_cells = self.page.query_selector_all('table thead th')
            for cell in header_cells:
                text = cell.inner_text().strip()
                if text:
                    headers.append(text)

            self.logger.read(f"表头: {headers}")

            # 获取数据行
            rows_data = []
            rows = self.page.query_selector_all('table tbody tr')
            self.logger.read(f"找到 {len(rows)} 行数据")

            for idx, row in enumerate(rows[:10], 1):  # 先抓取前10行
                cells = row.query_selector_all('td')
                row_data = []
                for cell in cells:
                    text = cell.inner_text().strip()
                    row_data.append(text)

                if row_data:
                    rows_data.append(row_data)
                    self.logger.read(f"第{idx}行: {row_data[:3]}...")  # 只显示前3列

            # 创建DataFrame
            df = pd.DataFrame(rows_data, columns=headers[:len(rows_data[0])] if rows_data else headers)
            self.logger.read(f"✓ 成功抓取 {len(df)} 条数据")

            return df

        except Exception as e:
            self.logger.read(f"✗ 抓取失败: {str(e)}")
            return pd.DataFrame()
