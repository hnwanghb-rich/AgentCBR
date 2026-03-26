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

    def get_menu_items(self) -> List[str]:
        """获取左侧菜单项"""
        try:
            menus = self.page.query_selector_all('.el-menu-item, .el-submenu__title')
            menu_texts = []
            for menu in menus:
                text = ' '.join(menu.inner_text().split()).strip()
                if text and text not in menu_texts:
                    menu_texts.append(text)
            self.logger.read(f"找到 {len(menu_texts)} 个菜单项")
            return menu_texts
        except Exception as e:
            self.logger.read(f"获取菜单失败: {e}")
            return []

    def click_menu(self, menu_text: str) -> bool:
        """点击菜单项"""
        try:
            clicked = self.page.evaluate("""
                (target) => {
                    const menus = document.querySelectorAll('.el-menu-item, .el-submenu__title');
                    for (const menu of menus) {
                        const text = menu.innerText.replace(/\\s+/g, ' ').trim();
                        if (text === target) {
                            menu.click();
                            return true;
                        }
                    }
                    return false;
                }
            """, menu_text)
            if clicked:
                time.sleep(1)
                self.logger.read(f"✓ 已点击菜单: {menu_text}")
                return True
            return False
        except Exception as e:
            self.logger.read(f"点击菜单失败: {e}")
            return False

    def has_tree_structure(self) -> bool:
        """判断当前页面是否有树结构"""
        try:
            tree = self.page.query_selector('.el-tree')
            return tree is not None and tree.is_visible()
        except:
            return False

    def scrape_table_with_drill_down(self) -> Dict[str, List[Dict]]:
        """抓取表格数据，并点击"进入"按钮进入下级，返回按项目分组的数据"""
        project_data = {}

        try:
            self.page.wait_for_selector('table tbody tr', timeout=5000)

            idx = 0
            while idx < 5:
                rows = self.page.query_selector_all('table tbody tr')
                if idx >= len(rows):
                    break

                row = rows[idx]
                # 获取项目名称（第一列）
                project_name = row.query_selector('td').inner_text().strip() if row.query_selector('td') else f"项目{idx+1}"
                self.logger.read(f"\n处理第 {idx + 1} 行: {project_name}")

                enter_btn = None
                btns = row.query_selector_all('a, button, span')
                for btn in btns:
                    text = ''.join(btn.inner_text().split())
                    if '进入' in text:
                        enter_btn = btn
                        break

                if enter_btn:
                    href = enter_btn.get_attribute('href')
                    if href and href.startswith('http'):
                        self.page.goto(href, timeout=30000)
                    else:
                        enter_btn.click()

                    time.sleep(1)
                    self.logger.read(f"✓ 已进入下级页面")

                    sub_data = self.scrape_current_table()
                    project_data[project_name] = sub_data

                    self.page.go_back()
                    time.sleep(1)
                    self.logger.read("✓ 已返回上级")
                else:
                    self.logger.read("  无'进入'按钮")

                idx += 1

        except Exception as e:
            self.logger.read(f"✗ 抓取失败: {e}")

        return project_data

    def scrape_current_table(self) -> List[Dict]:
        """抓取当前页面的表格数据（含翻页）"""
        all_data = []

        try:
            # 获取总条数和每页条数
            total_count = 0
            per_page = 10
            total_pages = 1

            try:
                # 查找"共xx条"文本
                pagination_text = self.page.inner_text('.el-pagination')
                import re
                match = re.search(r'共\s*(\d+)\s*条', pagination_text)
                if match:
                    total_count = int(match.group(1))
                    self.logger.read(f"  共 {total_count} 条数据")

                # 查找"xx条/页"
                match = re.search(r'(\d+)\s*条/页', pagination_text)
                if match:
                    per_page = int(match.group(1))

                # 计算总页数
                if total_count > 0:
                    total_pages = (total_count + per_page - 1) // per_page
                    self.logger.read(f"  每页 {per_page} 条，共 {total_pages} 页")
            except:
                self.logger.read("  未找到分页信息，按单页处理")

            # 逐页抓取
            for page_num in range(1, total_pages + 1):
                self.logger.read(f"  正在抓取第 {page_num}/{total_pages} 页...")

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
                self.logger.read(f"  第{page_num}页: {len(page_data)} 条")

                # 如果不是最后一页，跳转到下一页
                if page_num < total_pages:
                    try:
                        # 输入页码并跳转
                        page_input = self.page.query_selector('.el-pagination__jump input')
                        if page_input:
                            page_input.fill(str(page_num + 1))
                            page_input.press('Enter')
                            time.sleep(1)
                    except:
                        break

            self.logger.read(f"  ✓ 共抓取 {len(all_data)} 条数据")
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
