"""碳盘查审核系统 GUI"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import sys
import os
from pathlib import Path
import pandas as pd

class CarbonAuditGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("碳盘查审核系统")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        self.config = self.load_config()
        self.scraper = None
        self.is_running = False
        self.issues = []

        self.create_widgets()

    def get_resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.dirname(__file__), '..', relative_path)

    def load_config(self):
        config_path = Path(self.get_resource_path("config/config.json"))
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                'website': {'url': 'https://cc.cscec.com', 'username': '', 'password': ''},
                'output': {'directory': 'output'},
                'log': {'directory': 'logs'}
            }

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

        # 功能按钮区
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x", padx=10)

        self.audit_btn = ttk.Button(btn_frame, text="开始审核", command=self.start_audit)
        self.audit_btn.pack(side="left", padx=5)

        self.export_btn = ttk.Button(btn_frame, text="导出问题清单", command=self.export_issues, state="disabled")
        self.export_btn.pack(side="left", padx=5)

        self.report_btn = ttk.Button(btn_frame, text="生成报告", command=self.generate_report, state="disabled")
        self.report_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="打开输出目录", command=self.open_output).pack(side="left", padx=5)

        # Tab 分页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Tab 1: 执行日志
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="执行日志")
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 2: 问题清单
        issue_frame = ttk.Frame(self.notebook)
        self.notebook.add(issue_frame, text="问题清单")
        self.issue_tree = ttk.Treeview(issue_frame, columns=("项目", "问题", "优先级"), show="headings")
        self.issue_tree.heading("项目", text="项目名称")
        self.issue_tree.heading("问题", text="问题描述")
        self.issue_tree.heading("优先级", text="优先级")
        self.issue_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 3: 抓取数据
        data_frame = ttk.Frame(self.notebook)
        self.notebook.add(data_frame, text="抓取数据")

        # 左右分栏
        paned = ttk.PanedWindow(data_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        # 左侧树
        tree_frame = ttk.Frame(paned)
        paned.add(tree_frame, weight=2)
        self.project_tree = ttk.Treeview(tree_frame, show="tree")
        self.project_tree.pack(fill="both", expand=True)
        self.project_tree.bind("<<TreeviewSelect>>", self.on_project_select)

        # 右侧表格
        table_frame = ttk.Frame(paned)
        paned.add(table_frame, weight=8)
        self.data_tree = ttk.Treeview(table_frame, show="headings")
        self.data_tree.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.data_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.data_tree.configure(yscrollcommand=scrollbar.set)

        self.project_data = {}  # 存储项目数据

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def on_project_select(self, event):
        """树节点选择事件"""
        selection = self.project_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        if item_id in self.project_data:
            self.show_data_in_table(self.project_data[item_id])

    def add_project_to_tree(self, project_name, df):
        """添加项目到树"""
        item_id = self.project_tree.insert('', 'end', text=f"📁 {project_name}")
        self.project_data[item_id] = df
        self.log(f"  添加项目: {project_name} ({len(df)}条数据)")

    def show_data_in_table(self, df):
        """在表格中显示数据"""
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)

        if df.empty:
            return

        columns = list(df.columns)
        self.data_tree['columns'] = columns
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=100)

        for idx, row in df.iterrows():
            self.data_tree.insert('', 'end', values=list(row))

    def start_audit(self):
        self.log("开始审核...")
        self.audit_btn.config(state="disabled")
        thread = threading.Thread(target=self.run_audit)
        thread.daemon = True
        thread.start()

    def run_audit(self):
        try:
            self.log("=" * 50)
            self.log("步骤1: 导入模块...")
            from base_scraper import BaseScraper
            from emission_auditor import EmissionDataAuditor
            from logger import Logger
            self.log("✓ 模块导入成功")

            self.log("\n步骤2: 初始化日志系统...")
            logger = Logger(self.config['log']['directory'])
            logger.info = self.log
            logger.read = self.log
            self.log("✓ 日志系统初始化完成")

            self.log("\n步骤3: 初始化浏览器...")
            scraper = BaseScraper(self.config, logger)
            scraper.init_browser()
            self.log("✓ 浏览器初始化完成")

            self.log("\n步骤4: 登录系统...")
            if not scraper.login():
                self.log("✗ 登录失败")
                return
            self.log("✓ 登录成功")

            self.log("\n步骤5: 开始遍历左侧菜单...")
            from data_scraper import DataScraper
            data_scraper = DataScraper(scraper.page, logger)

            menu_items = data_scraper.get_menu_items()
            self.log(f"找到 {len(menu_items)} 个菜单项")

            all_rows = []
            for menu_idx, menu_text in enumerate(menu_items, 1):
                self.log(f"\n[菜单 {menu_idx}/{len(menu_items)}] {menu_text}")

                if not data_scraper.click_menu(menu_text):
                    self.log(f"  跳过菜单: {menu_text}")
                    continue

                current_url = scraper.page.url
                self.log(f"  当前URL: {current_url}")

                if "carbonfillin/collect" in current_url:
                    self.log("  检测到级联结构，使用DFS遍历...")
                    cascade_data = data_scraper.scrape_cascade_structure()
                    if cascade_data:
                        df = pd.DataFrame(cascade_data)
                        self.root.after(0, lambda m=menu_text, d=df: self.add_project_to_tree(m, d))
                        all_rows.extend(cascade_data)
                elif data_scraper.has_tree_structure():
                    self.log("  检测到树结构，开始遍历...")
                    tree_nodes = data_scraper.get_tree_nodes()
                    if tree_nodes and len(tree_nodes) > 0:
                        data_scraper.click_tree_node(tree_nodes[0])
                        project_data = data_scraper.scrape_table_with_drill_down()
                        for project_name, data_list in project_data.items():
                            df = pd.DataFrame(data_list)
                            self.root.after(0, lambda m=menu_text, p=project_name, d=df: self.add_project_to_tree(f"{m}/{p}", d))
                            all_rows.extend(data_list)
                else:
                    self.log("  无树结构，跳过")

            df = pd.DataFrame(all_rows)

            self.log("\n步骤7: 数据审核...")
            auditor = EmissionDataAuditor(self.config)
            self.issues = auditor.audit_data(df)
            self.log(f"✓ 审核完成，发现 {len(self.issues)} 个问题")

            # 显示问题到界面
            for issue in self.issues[:5]:  # 显示前5个
                self.log(f"  - {issue.get('project', '')}: {issue.get('description', '')}")

            self.log("\n" + "=" * 50)
            self.log("流程执行完成")
            self.export_btn.config(state="normal")
            self.report_btn.config(state="normal")
        except Exception as e:
            self.log(f"\n✗ 错误: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.audit_btn.config(state="normal")

    def export_issues(self):
        try:
            self.log("\n开始导出问题清单...")
            from issue_generator import IssueListGenerator

            generator = IssueListGenerator(self.config['output']['directory'])
            filepath = generator.generate_excel(self.issues)

            self.log(f"✓ 问题清单已生成")
            self.log(f"文件路径: {filepath}")
            self.log(f"完整路径: {Path(filepath).absolute()}")
        except Exception as e:
            self.log(f"✗ 导出失败: {str(e)}")

    def generate_report(self):
        try:
            self.log("\n开始生成报告...")
            from report_generator import ReportGenerator

            generator = ReportGenerator(self.config['output']['directory'])
            data = {'company': '测试公司', 'project': '测试项目'}
            filepath = generator.generate_report(data, self.issues)

            self.log(f"✓ 报告已生成")
            self.log(f"文件路径: {filepath}")
            self.log(f"完整路径: {Path(filepath).absolute()}")
        except Exception as e:
            self.log(f"✗ 生成失败: {str(e)}")

    def open_output(self):
        import os
        os.startfile(self.config['output']['directory'])

if __name__ == "__main__":
    root = tk.Tk()
    app = CarbonAuditGUI(root)
    root.mainloop()


