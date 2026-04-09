import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
from pathlib import Path
from base_scraper import BaseScraper
from carbon_platform import CarbonPlatformBrowser
from carbon_auditor import CarbonAuditor
from audit_reporter import AuditReporter
from data_scraper import DataScraper
from logger import Logger
import pandas as pd

class AgentCBRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("碳盘查自动审核系统")
        self.root.geometry("1200x800")

        self.config = self.load_config()
        self.scraper = None
        self.is_running = False
        self.current_data = []  # 当前显示的数据
        self.tree_data = {}  # 树节点数据存储 {item_id: data}

        self.create_widgets()

    def load_config(self):
        import sys
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent
        config_path = base_path / "config" / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_widgets(self):
        # 配置区
        config_frame = ttk.LabelFrame(self.root, text="系统配置", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="系统URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = ttk.Entry(config_frame, width=50)
        self.url_entry.insert(0, self.config['website']['url'])
        self.url_entry.grid(row=0, column=1, padx=5)

        ttk.Label(config_frame, text="用户名:").grid(row=1, column=0, sticky="w")
        self.user_entry = ttk.Entry(config_frame, width=50)
        self.user_entry.insert(0, self.config['website']['username'])
        self.user_entry.grid(row=1, column=1, padx=5)

        ttk.Label(config_frame, text="密码:").grid(row=2, column=0, sticky="w")
        self.pass_entry = ttk.Entry(config_frame, width=50, show="*")
        self.pass_entry.insert(0, self.config['website']['password'])
        self.pass_entry.grid(row=2, column=1, padx=5)

        # 控制按钮
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x", padx=10)

        self.audit_btn = ttk.Button(btn_frame, text="开始审核", command=self.start_audit)
        self.audit_btn.pack(side="left", padx=5)

        self.factor_btn = ttk.Button(btn_frame, text="项目因子管理", command=self.start_project_factor)
        self.factor_btn.pack(side="left", padx=5)

        self.emission_btn = ttk.Button(btn_frame, text="项目碳排放采集", command=self.start_carbon_emission)
        self.emission_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self.stop_task, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="打开输出目录", command=self.open_output).pack(side="left", padx=5)

        # 进度显示
        progress_frame = ttk.LabelFrame(self.root, text="执行进度", padding=10)
        progress_frame.pack(fill="x", padx=10, pady=5)

        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.pack()

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill="x", pady=5)

        # 创建Notebook（标签页）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Tab 1: 项目审核日志
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="项目审核日志")

        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=20)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 2: 数据浏览（树结构 + 表格）
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text="数据浏览")

        # 左侧：树结构
        tree_frame = ttk.Frame(self.data_frame)
        tree_frame.pack(side="left", fill="both", expand=False, padx=5, pady=5)

        ttk.Label(tree_frame, text="项目树结构").pack()

        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")

        self.project_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set, height=25)
        self.project_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.config(command=self.project_tree.yview)

        self.project_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 右侧：数据表格
        table_frame = ttk.Frame(self.data_frame)
        table_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ttk.Label(table_frame, text="数据详情").pack()

        # 表格滚动条
        table_scroll_y = ttk.Scrollbar(table_frame)
        table_scroll_y.pack(side="right", fill="y")

        table_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        table_scroll_x.pack(side="bottom", fill="x")

        # 数据表格
        self.data_table = ttk.Treeview(
            table_frame,
            yscrollcommand=table_scroll_y.set,
            xscrollcommand=table_scroll_x.set,
            height=25
        )
        self.data_table.pack(side="left", fill="both", expand=True)

        table_scroll_y.config(command=self.data_table.yview)
        table_scroll_x.config(command=self.data_table.xview)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self, current, total, message=""):
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = current
        self.progress_label.config(text=f"{message} ({current}/{total})")
        self.root.update_idletasks()

    def disable_buttons(self):
        self.audit_btn.config(state="disabled")
        self.factor_btn.config(state="disabled")
        self.emission_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def enable_buttons(self):
        self.audit_btn.config(state="normal")
        self.factor_btn.config(state="normal")
        self.emission_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def start_audit(self):
        self.is_running = True
        self.disable_buttons()
        self.update_config()

        thread = threading.Thread(target=self.run_audit)
        thread.daemon = True
        thread.start()

    def start_project_factor(self):
        self.is_running = True
        self.disable_buttons()
        self.update_config()

        thread = threading.Thread(target=self.run_project_factor)
        thread.daemon = True
        thread.start()

    def start_carbon_emission(self):
        self.is_running = True
        self.disable_buttons()
        self.update_config()

        thread = threading.Thread(target=self.run_carbon_emission)
        thread.daemon = True
        thread.start()

    def update_config(self):
        self.config['website']['url'] = self.url_entry.get()
        self.config['website']['username'] = self.user_entry.get()
        self.config['website']['password'] = self.pass_entry.get()

    def run_project_factor(self):
        """执行项目因子管理数据采集"""
        try:
            from datetime import datetime
            import time
            self.log(f"{'='*50}")
            self.log("📋 项目因子管理数据采集")
            self.log(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"{'='*50}\n")

            logger = Logger(self.config['log']['directory'])
            logger.info = self.log
            logger.read = self.log

            scraper = BaseScraper(self.config, logger)
            scraper.init_browser()

            if not scraper.login():
                self.log("❌ 登录失败")
                return

            self.log("✅ 登录成功\n")
            page = scraper.page

            # 跳转到项目因子管理页面
            url = "https://cc.cscec.com/carbonfillin/projectList"
            self.log(f"跳转到: {url}")
            page.goto(url, timeout=30000)
            page.wait_for_load_state('networkidle', timeout=15000)
            self.log("页面加载完成\n")

            # 清空树结构
            self.project_tree.delete(*self.project_tree.get_children())
            self.tree_data.clear()
            root_node = self.project_tree.insert("", "end", text="项目因子管理", open=True)
            all_project_data = {}

            # ── 步骤2: 找到树节点并点击（跳过index=0的根节点） ──
            tree_spans = page.query_selector_all('span.tree-node-text-label')
            tree_count = len(tree_spans)
            self.log(f"找到 {tree_count} 个树节点（跳过第0个根节点）")

            for span_idx in range(1, tree_count):  # 从1开始，跳过根节点
                if not self.is_running:
                    break

                # 每次重新查询树节点，避免DOM分离
                tree_spans = page.query_selector_all('span.tree-node-text-label')
                if span_idx >= len(tree_spans):
                    break

                span = tree_spans[span_idx]
                span_text = span.inner_text().strip()
                self.log(f"\n[树节点 {span_idx}] 点击: {span_text}")
                span.click()
                time.sleep(1.5)

                # 等待表格A出现
                try:
                    page.wait_for_selector('table tbody tr', timeout=8000)
                except Exception:
                    self.log(f"  ⚠️ 表格未出现，跳过")
                    continue

                # 树节点
                span_node = self.project_tree.insert(root_node, "end", text=span_text, open=True)

                # ── 步骤3-5: 遍历表格A（支持翻页） ──
                page_a_num = 1
                while True:
                    if not self.is_running:
                        break

                    self.log(f"  [表格A 第{page_a_num}页]")

                    # 读取表格A
                    headers_a = [th.inner_text().strip() for th in page.query_selector_all('table thead th')]
                    rows_a = page.query_selector_all('table tbody tr')
                    self.log(f"    共 {len(rows_a)} 行")

                    # ── 步骤4: 遍历表格A每行，点击"进入"按钮 ──
                    for row_idx in range(len(rows_a)):
                        if not self.is_running:
                            break

                        # 重新获取行（防止stale）
                        rows_a = page.query_selector_all('table tbody tr')
                        if row_idx >= len(rows_a):
                            break

                        row = rows_a[row_idx]
                        cells = row.query_selector_all('td')

                        # 提取项目名称（第3列，index=2）
                        project_name = cells[2].inner_text().strip() if len(cells) > 2 else f"项目{row_idx+1}"
                        row_data = {headers_a[i]: cells[i].inner_text().strip()
                                   for i in range(min(len(headers_a), len(cells)))}

                        self.log(f"    [{row_idx+1}/{len(rows_a)}] {project_name}")

                        # 在树中添加项目节点
                        project_node = self.project_tree.insert(span_node, "end", text=project_name)

                        # 找到"进入"按钮 (role=button, name=进入)
                        enter_clicked = False
                        try:
                            # 方法1: 通过role查找
                            enter_btns = page.query_selector_all('button[role="button"]')
                            for btn in enter_btns:
                                if '进入' in btn.inner_text():
                                    # 检查按钮是否在当前行内
                                    btn_row = btn.evaluate('el => el.closest("tr")')
                                    if btn_row == row.evaluate('el => el'):
                                        btn.click()
                                        enter_clicked = True
                                        break
                        except Exception:
                            pass

                        if not enter_clicked:
                            # 方法2: 在行内直接查找
                            btns = row.query_selector_all('button, a')
                            for btn in btns:
                                if '进入' in ''.join(btn.inner_text().split()):
                                    btn.click()
                                    enter_clicked = True
                                    break

                        if not enter_clicked:
                            self.log(f"      ⚠️ 未找到进入按钮")
                            continue

                        page.wait_for_load_state('networkidle', timeout=10000)
                        time.sleep(0.8)

                        # ── 窗体B: 逐页抓取表格B ──
                        b_data = self._scrape_table_b(page)
                        self.log(f"      ✓ 窗体B 共采集 {len(b_data)} 条")

                        all_project_data[project_name] = b_data

                        # 存入树节点
                        self.tree_data[project_node] = b_data

                        # 返回窗体A
                        page.go_back()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        time.sleep(0.8)

                        # 重新点击树节点以恢复表格A
                        tree_spans = page.query_selector_all('span.tree-node-text-label')
                        if span_idx < len(tree_spans):
                            tree_spans[span_idx].click()
                            time.sleep(1.5)
                            try:
                                page.wait_for_selector('table tbody tr', timeout=8000)
                            except Exception:
                                pass

                            # 如果不是第一页，需要翻回到当前页
                            if page_a_num > 1:
                                for _ in range(page_a_num - 1):
                                    next_btn_a = page.query_selector('button.btn-next')
                                    if next_btn_a and next_btn_a.get_attribute('disabled') is None:
                                        next_btn_a.click()
                                        time.sleep(1)

                    # ── 步骤5: 检查表格A的下一页按钮 ──
                    next_btn_a = page.query_selector('button.btn-next')
                    if next_btn_a and next_btn_a.get_attribute('disabled') is None:
                        self.log(f"  → 表格A翻页到第{page_a_num + 1}页")
                        next_btn_a.click()
                        time.sleep(1.5)
                        page_a_num += 1
                    else:
                        self.log(f"  ✓ 表格A已完成所有页")
                        break

            # 保存数据
            self.save_project_factor_data(all_project_data)

            scraper.close()
            self.log(f"\n🏁 采集完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            import traceback
            self.log(f"\n❌ 采集出错: {str(e)}")
            self.log(traceback.format_exc())
        finally:
            self.enable_buttons()
            self.is_running = False

    def _scrape_table_b(self, page) -> list:
        """抓取窗体B的表格数据，支持翻页（btn-next不disabled则翻页）"""
        import time
        all_data = []
        page_num = 1

        while True:
            try:
                page.wait_for_selector('table tbody tr', timeout=8000)
            except Exception:
                self.log(f"        ⚠️ 第{page_num}页表格未出现")
                break

            # 读取表头
            headers = [th.inner_text().strip() for th in page.query_selector_all('table thead th')]
            rows = page.query_selector_all('table tbody tr')

            page_data = []
            for row in rows:
                cells = row.query_selector_all('td')
                if cells:
                    row_dict = {headers[i]: cells[i].inner_text().strip()
                                for i in range(min(len(headers), len(cells)))}
                    page_data.append(row_dict)

            all_data.extend(page_data)
            self.log(f"        第{page_num}页: {len(page_data)} 条")

            # 检查下一页按钮
            next_btn = page.query_selector('button.btn-next')
            if next_btn and next_btn.get_attribute('disabled') is None:
                next_btn.click()
                time.sleep(1)
                page_num += 1
            else:
                break

        return all_data

    def _process_table_a(self, page, span_node, att_dir, span_idx):
        """处理表格A（项目列表），支持翻页"""
        import time
        page_a_num = 1

        while True:
            if not self.is_running:
                break

            self.log(f"  [表格A 第{page_a_num}页]")

            try:
                page.wait_for_selector('table tbody tr', timeout=8000)
            except Exception:
                break

            headers_a = [th.inner_text().strip() for th in page.query_selector_all('table thead th')]
            rows_a = page.query_selector_all('table tbody tr')
            self.log(f"    共 {len(rows_a)} 行")

            for row_idx in range(len(rows_a)):
                if not self.is_running:
                    break

                rows_a = page.query_selector_all('table tbody tr')
                if row_idx >= len(rows_a):
                    break

                row = rows_a[row_idx]
                cells = row.query_selector_all('td')
                project_name = cells[2].inner_text().strip() if len(cells) > 2 else f"项目{row_idx+1}"

                self.log(f"    [{row_idx+1}/{len(rows_a)}] {project_name}")
                project_node = self.project_tree.insert(span_node, "end", text=project_name)

                # 点击"进入"按钮 - 尝试多种选择器
                enter_btn = row.query_selector('button:has-text("进入")')
                if not enter_btn:
                    # 尝试其他选择器
                    btns = row.query_selector_all('button')
                    for btn in btns:
                        if '进入' in btn.inner_text():
                            enter_btn = btn
                            break

                if not enter_btn:
                    self.log(f"      ⚠️ 未找到进入按钮，跳过")
                    continue

                self.log(f"      → 点击进入按钮")
                enter_btn.click(force=True)
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(0.8)

                # 进入窗体B
                self._process_table_b(page, project_node, att_dir)

                # 返回表格A
                self.log(f"      ← 返回表格A")
                page.go_back()
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(1.5)

            # 检查表格A下一页
            next_btn_a = page.query_selector('button.btn-next')
            if next_btn_a and next_btn_a.get_attribute('disabled') is None:
                self.log(f"  → 表格A翻页到第{page_a_num + 1}页")
                next_btn_a.click()
                time.sleep(1.5)
                page_a_num += 1
            else:
                self.log(f"  ✓ 表格A已完成所有页")
                break

    def _process_table_b(self, page, project_node, att_dir):
        """处理表格B，支持翻页，点击查看记录进入表格C"""
        import time

        while True:
            if not self.is_running:
                break

            try:
                page.wait_for_selector('table tbody tr', timeout=8000)
                time.sleep(1)  # 额外等待表格渲染
            except Exception:
                self.log(f"      ⚠️ 表格B未出现")
                break

            # 检查分页信息
            pagination_text = page.evaluate("""
                () => {
                    const pagination = document.querySelector('.el-pagination');
                    return pagination ? pagination.textContent : '';
                }
            """)
            self.log(f"      [表格B 分页信息: {pagination_text.strip()}]")

            headers = [th.inner_text().strip() for th in page.query_selector_all('table thead th')]
            rows = page.query_selector_all('table tbody tr')
            self.log(f"      [表格B 当前页: {len(rows)} 条]")

            for row_idx in range(len(rows)):
                if not self.is_running:
                    break

                rows = page.query_selector_all('table tbody tr')
                if row_idx >= len(rows):
                    break

                row = rows[row_idx]
                cells = row.query_selector_all('td')
                row_name = cells[1].inner_text().strip() if len(cells) > 1 else f"记录{row_idx+1}"

                # 点击"查看记录"按钮
                view_btn = row.query_selector('button:has-text("查看记录")')
                if not view_btn:
                    continue

                view_btn.click(force=True)
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(0.8)

                # 进入表格C
                self._process_table_c(page, project_node, att_dir, row_name)

                # 返回表格B
                page.go_back()
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(0.8)

            # 检查下一页
            next_btn = page.query_selector('button.btn-next')
            if next_btn and next_btn.get_attribute('disabled') is None:
                self.log(f"      → 表格B翻页")
                next_btn.click()
                time.sleep(1.5)
            else:
                self.log(f"      ✓ 表格B已完成所有页")
                break

    def _process_table_c(self, page, project_node, att_dir, row_name):
        """处理表格C，点击查看按钮进入窗体D"""
        import time

        try:
            page.wait_for_selector('table tbody tr', timeout=8000)
        except Exception:
            return

        rows = page.query_selector_all('table tbody tr')
        self.log(f"        [表格C: {len(rows)} 条]")

        for row_idx in range(len(rows)):
            if not self.is_running:
                break

            rows = page.query_selector_all('table tbody tr')
            if row_idx >= len(rows):
                break

            row = rows[row_idx]

            # 点击"查看"按钮
            view_btn = row.query_selector('button:has-text("查看")')
            if not view_btn:
                continue

            view_btn.click(force=True)
            time.sleep(1)

            # 进入窗体D（弹窗）
            self._process_window_d(page, att_dir)

            # 关闭弹窗
            try:
                close_btn = page.query_selector('button:has-text("关闭")')
                if close_btn:
                    close_btn.click()
                else:
                    page.query_selector('.el-dialog__headerbtn').click()
                time.sleep(0.5)
            except Exception:
                pass

    def _process_window_d(self, page, att_dir):
        """处理窗体D，下载所有附件"""
        import time

        # 查找所有"下载"按钮
        download_btns = page.query_selector_all('button:has-text("下载")')
        self.log(f"          [窗体D: 找到 {len(download_btns)} 个下载按钮]")

        for btn_idx, btn in enumerate(download_btns):
            if not self.is_running:
                break

            try:
                with page.expect_download(timeout=30000) as download_info:
                    btn.evaluate('el => el.click()')
                download = download_info.value
                filename = download.suggested_filename
                save_path = att_dir / filename
                download.save_as(save_path)
                self.log(f"            ✓ 下载: {filename}")
                time.sleep(0.5)
            except Exception as e:
                self.log(f"            ⚠️ 下载失败: {e}")

    def run_carbon_emission(self):
        """执行项目碳排放采集 - 多级树结构遍历"""
        try:
            from datetime import datetime
            import time
            self.log(f"{'='*50}")
            self.log("🌍 项目碳排放数据采集")
            self.log(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"{'='*50}\n")

            logger = Logger(self.config['log']['directory'])
            logger.info = self.log
            logger.read = self.log

            scraper = BaseScraper(self.config, logger)
            scraper.init_browser()

            if not scraper.login():
                self.log("❌ 登录失败")
                return

            self.log("✅ 登录成功\n")
            page = scraper.page

            # 跳转到碳排放采集页面
            url = "https://cc.cscec.com/carbonfillin/collect"
            self.log(f"跳转到: {url}")
            page.goto(url, timeout=30000)
            page.wait_for_load_state('networkidle', timeout=15000)
            self.log("页面加载完成\n")

            # 清空树结构
            self.project_tree.delete(*self.project_tree.get_children())
            self.tree_data.clear()
            root_node = self.project_tree.insert("", "end", text="项目碳排放采集", open=True)

            # 创建附件下载目录
            from pathlib import Path
            att_dir = Path("att")
            att_dir.mkdir(exist_ok=True)

            # 步骤2: 点击组织树节点
            tree_spans = page.query_selector_all('span.tree-node-text-label')
            tree_count = len(tree_spans)
            self.log(f"找到 {tree_count} 个树节点（跳过第0个根节点）")

            for span_idx in range(1, tree_count):
                if not self.is_running:
                    break

                tree_spans = page.query_selector_all('span.tree-node-text-label')
                if span_idx >= len(tree_spans):
                    break

                span = tree_spans[span_idx]
                span_text = span.inner_text().strip()
                self.log(f"\n[树节点 {span_idx}] 点击: {span_text}")
                span.click()
                time.sleep(1.5)

                try:
                    page.wait_for_selector('table tbody tr', timeout=8000)
                except Exception:
                    self.log(f"  ⚠️ 表格未出现，跳过")
                    continue

                span_node = self.project_tree.insert(root_node, "end", text=span_text, open=True)

                # 步骤3-4: 遍历表格A（支持翻页）
                self._process_table_a(page, span_node, att_dir, span_idx)

                # 完成后返回主页，准备点击下一个树节点
                self.log(f"  ← 返回主页面，继续下一个树节点")
                page.goto(url, timeout=30000)
                page.wait_for_load_state('networkidle', timeout=15000)
                time.sleep(1)

            scraper.close()
            self.log(f"\n🏁 采集完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            import traceback
            self.log(f"\n❌ 采集出错: {str(e)}")
            self.log(traceback.format_exc())
        finally:
            self.enable_buttons()
            self.is_running = False

    def run_audit(self):
        """执行项目审核"""
        try:
            from datetime import datetime
            self.log(f"{'='*50}")
            self.log("🚀 碳盘查自动审核系统启动")
            self.log(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"{'='*50}\n")

            logger = Logger(self.config['log']['directory'])
            logger.info = self.log
            logger.read = self.log

            scraper = BaseScraper(self.config, logger)
            scraper.init_browser()

            if not scraper.login():
                self.log("❌ 登录失败")
                return

            self.log("✅ 登录成功\n")

            platform = CarbonPlatformBrowser(scraper.page, logger)
            reporter = AuditReporter(self.config['output']['directory'])

            if not platform.navigate_to_all_projects():
                self.log("❌ 导航失败")
                return

            projects = platform.get_project_list()
            self.log(f"📋 共找到 {len(projects)} 个项目\n")

            if not projects:
                self.log("⚠️ 没有找到项目")
                return

            # 清空树结构
            self.project_tree.delete(*self.project_tree.get_children())
            self.tree_data.clear()
            root_node = self.project_tree.insert("", "end", text="审核项目列表", open=True)

            results = []
            for i, project in enumerate(projects):
                if not self.is_running:
                    self.log("\n⏸️ 用户停止审核")
                    break

                self.update_progress(i, len(projects), f"审核项目: {project['名称']}")
                self.log(f"\n{'='*50}")
                self.log(f"🔍 审核项目 {i+1}/{len(projects)}: {project['名称']}")

                auditor = CarbonAuditor()

                if not platform.open_project(i):
                    self.log(f"  ⚠️ 无法打开项目")
                    continue

                overview = platform.get_project_overview()
                self.log(f"  📄 已获取项目概况")

                # 基础信息检查
                try:
                    building_area = float(overview.get("建筑面积", "0").replace(",", ""))
                    if building_area > 0:
                        auditor.check_building_area(building_area)

                    public_area = float(overview.get("公区面积", "0").replace(",", ""))
                    total_area = float(overview.get("总建筑面积", building_area))
                    project_function = overview.get("项目功能", "")
                    if public_area > 0 and total_area > 0:
                        auditor.check_public_area_ratio(public_area, total_area, project_function)
                except Exception as e:
                    self.log(f"  ⚠️ 基础信息检查失败: {e}")

                # 分类数据审核
                category_data = {}
                categories_to_check = ["生产经营数据", "固定源", "移动源", "能源", "节能降碳措施"]

                for category in categories_to_check:
                    if not self.is_running:
                        break

                    try:
                        data = platform.get_category_data(category)
                        category_data[category] = data
                        self.log(f"  ✓ {category}: {data.get('total', 0)} 条记录")

                        if category == "固定源":
                            auditor.check_fixed_sources(data.get("records", []))
                        elif category == "移动源":
                            auditor.check_mobile_sources(data.get("records", []))
                        elif category == "能源":
                            region = overview.get("项目区域", "")
                            auditor.check_energy(data.get("records", []), region)
                        elif category == "节能降碳措施":
                            auditor.check_conservation(data.get("records", []))

                    except Exception as e:
                        self.log(f"  ⚠️ 获取 {category} 数据失败: {e}")

                verdict, issues = auditor.get_verdict()
                results.append({
                    "项目名称": project["名称"],
                    "提交单位": project["提交单位"],
                    "审核结果": verdict,
                    "问题数": len(issues),
                    "问题详情": "; ".join(issues) if issues else ""
                })

                # 添加到树结构
                project_node = self.project_tree.insert(
                    root_node, "end",
                    text=f"{project['名称']} [{verdict}]",
                    values=(f"audit_{i}",)
                )
                audit_info = {
                    "overview": overview,
                    "category_data": category_data,
                    "verdict": verdict,
                    "issues": issues
                }
                self.tree_data[project_node] = audit_info

                log_content = reporter.generate_log(
                    project["名称"], overview, category_data, verdict, issues
                )
                reporter.save_log(project["名称"], log_content)

                emoji = "✅" if verdict == "通过" else "❌"
                self.log(f"  {emoji} 审核结果: {verdict} (发现 {len(issues)} 个问题)")
                if issues:
                    for issue in issues[:3]:
                        self.log(f"    - {issue}")
                    if len(issues) > 3:
                        self.log(f"    ... 更多问题见日志文件")

                platform.go_back()

            if results:
                summary_file = reporter.save_summary(results)
                self.log(f"\n📊 审核汇总已保存: {summary_file}")

                self.log(f"\n{'='*50}")
                self.log("📊 审核汇总")
                self.log(f"{'='*50}")
                pass_count = sum(1 for r in results if r["审核结果"] == "通过")
                reject_count = len(results) - pass_count
                self.log(f"  总项目数: {len(results)}")
                self.log(f"  ✅ 通过: {pass_count}")
                self.log(f"  ❌ 驳回: {reject_count}")

            scraper.close()
            self.update_progress(len(projects), len(projects), "审核完成")
            self.log(f"\n🏁 审核完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            import traceback
            self.log(f"\n❌ 审核过程出错: {str(e)}")
            self.log(traceback.format_exc())
        finally:
            self.enable_buttons()
            self.is_running = False

    def on_tree_select(self, event):
        """树节点选择事件"""
        selection = self.project_tree.selection()
        if not selection:
            return

        item = selection[0]
        data = self.tree_data.get(item)

        if data is None:
            return

        try:
            # 清空表格
            self.data_table.delete(*self.data_table.get_children())
            for col in self.data_table["columns"]:
                self.data_table.heading(col, text="")
            self.data_table["columns"] = ()

            # 显示数据
            if isinstance(data, list) and data:
                # 列表数据（项目因子、碳排放）
                columns = list(data[0].keys())
                self.data_table["columns"] = columns
                self.data_table["show"] = "headings"

                for col in columns:
                    self.data_table.heading(col, text=col)
                    self.data_table.column(col, width=100)

                for record in data:
                    values = [record.get(col, "") for col in columns]
                    self.data_table.insert("", "end", values=values)

            elif isinstance(data, dict):
                # 字典数据（审核信息）
                self.data_table["columns"] = ("字段", "值")
                self.data_table["show"] = "headings"
                self.data_table.heading("字段", text="字段")
                self.data_table.heading("值", text="值")
                self.data_table.column("字段", width=150)
                self.data_table.column("值", width=400)

                # 显示概况
                if "overview" in data:
                    self.data_table.insert("", "end", values=("=== 项目概况 ===", ""))
                    for k, v in data["overview"].items():
                        self.data_table.insert("", "end", values=(k, v))

                # 显示审核结果
                if "verdict" in data:
                    self.data_table.insert("", "end", values=("", ""))
                    self.data_table.insert("", "end", values=("=== 审核结果 ===", ""))
                    self.data_table.insert("", "end", values=("结论", data["verdict"]))
                    self.data_table.insert("", "end", values=("问题数", len(data.get("issues", []))))

                    if data.get("issues"):
                        self.data_table.insert("", "end", values=("", ""))
                        self.data_table.insert("", "end", values=("=== 问题详情 ===", ""))
                        for i, issue in enumerate(data["issues"], 1):
                            self.data_table.insert("", "end", values=(f"问题{i}", issue))

        except Exception as e:
            self.log(f"显示数据失败: {e}")

    def save_project_factor_data(self, data):
        """保存项目因子数据"""
        try:
            output_dir = Path(self.config['output']['directory'])
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "项目因子数据.xlsx"

            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for project_name, project_data in data.items():
                    if project_data:
                        df = pd.DataFrame(project_data)
                        sheet_name = project_name[:31]
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

            self.log(f"✓ 项目因子数据已保存: {output_file}")
        except Exception as e:
            self.log(f"⚠️ 保存项目因子数据失败: {e}")

    def save_carbon_emission_data(self, data):
        """保存碳排放数据"""
        try:
            output_dir = Path(self.config['output']['directory'])
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "项目碳排放数据.xlsx"

            if data:
                df = pd.DataFrame(data)
                df.to_excel(output_file, index=False)
                self.log(f"✓ 碳排放数据已保存: {output_file}")
        except Exception as e:
            self.log(f"⚠️ 保存碳排放数据失败: {e}")

    def stop_task(self):
        self.is_running = False
        self.log("\n⏸️ 正在停止...")

    def open_output(self):
        import os
        import sys
        output_dir = self.config['output']['directory']
        if sys.platform == 'win32':
            os.startfile(output_dir)
        else:
            os.system(f'open "{output_dir}"')

if __name__ == "__main__":
    root = tk.Tk()
    app = AgentCBRGUI(root)
    root.mainloop()
