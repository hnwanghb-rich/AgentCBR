import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
from pathlib import Path
from scraper import WebScraper
from logger import Logger

class AgentCBRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AgentCBR - 网页内容抓取系统")
        self.root.geometry("800x600")

        self.config = self.load_config()
        self.scraper = None
        self.is_running = False

        self.create_widgets()

    def load_config(self):
        with open("config/config.json", 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_widgets(self):
        # 配置区
        config_frame = ttk.LabelFrame(self.root, text="配置", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="网站URL:").grid(row=0, column=0, sticky="w")
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

        self.start_btn = ttk.Button(btn_frame, text="开始抓取", command=self.start_scraping)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self.stop_scraping, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="打开输出目录", command=self.open_output).pack(side="left", padx=5)

        # 日志区
        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20)
        self.log_text.pack(fill="both", expand=True)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def start_scraping(self):
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        self.config['website']['url'] = self.url_entry.get()
        self.config['website']['username'] = self.user_entry.get()
        self.config['website']['password'] = self.pass_entry.get()

        thread = threading.Thread(target=self.run_scraper)
        thread.daemon = True
        thread.start()

    def run_scraper(self):
        try:
            logger = Logger(self.config['log']['directory'])
            logger.info = self.log
            self.scraper = WebScraper(self.config, logger)
            self.scraper.run()
        except Exception as e:
            self.log(f"错误: {str(e)}")
        finally:
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def stop_scraping(self):
        self.is_running = False
        if self.scraper:
            self.scraper.close()
        self.log("已停止")

    def open_output(self):
        import os
        os.startfile(self.config['output']['directory'])

if __name__ == "__main__":
    root = tk.Tk()
    app = AgentCBRGUI(root)
    root.mainloop()
