"""基础爬虫类 - 提供浏览器初始化和登录功能"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time

class BaseScraper:
    """基础爬虫类，提供浏览器初始化和登录功能"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.playwright = None
        self.browser = None
        self.page = None

    def init_browser(self):
        """初始化浏览器（无头模式）"""
        self.logger.read("初始化浏览器（无头模式）")
        try:
            import os
            chrome_exe = os.path.join(
                os.environ.get('LOCALAPPDATA', ''),
                'ms-playwright', 'chromium-1208', 'chrome-win64', 'chrome.exe'
            )
            self.logger.read(f"浏览器路径: {chrome_exe}")

            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                executable_path=chrome_exe,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = self.browser.new_context()
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.page = context.new_page()
            self.logger.read("浏览器初始化完成")
        except Exception as e:
            self.logger.read(f"浏览器初始化失败: {str(e)}")
            raise

    def login(self):
        """登录碳盘查系统"""
        try:
            url = self.config['website']['url']
            self.logger.read(f"访问登录页面: {url}")
            self.page.goto(url, wait_until="networkidle", timeout=60000)
            self.page.wait_for_selector('input', timeout=15000)
            self.logger.read(f"登录表单已加载，当前URL={self.page.url}")

            usel = "input[type='text'], input:not([type])"
            psel = "input[type='password']"
            bsel = "button[type='submit']"

            return self._do_login(url, usel, psel, bsel)

        except Exception as e:
            self.logger.read(f"登录异常: {str(e)}")
            return False

    def _do_login(self, url, usel, psel, bsel):
        """执行登录操作"""
        username = self.config['website']['username']
        password = self.config['website']['password']

        u_input = self.page.locator("input[type='text']:visible, input:not([type]):visible").first
        p_input = self.page.locator("input[type='password']:visible").first

        u_input.click()
        self.page.keyboard.press("Control+a")
        self.page.keyboard.press("Delete")
        u_input.fill(username)
        self.page.evaluate("""
            (sel) => {
                const el = document.querySelector(sel);
                if (el) {
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }
        """, usel)

        p_input.click()
        self.page.keyboard.press("Control+a")
        self.page.keyboard.press("Delete")
        p_input.fill(password)
        self.page.evaluate("""
            (sel) => {
                const el = document.querySelector(sel);
                if (el) {
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }
        """, psel)

        self.page.evaluate("""
            () => {
                const btn = document.querySelector("button[type='submit']")
                    || document.querySelector('.el-button--primary')
                    || [...document.querySelectorAll('button')].find(
                        b => b.innerText.replace(/\\s/g, '').includes('登录')
                    );
                if (btn) btn.click();
            }
        """)
        self.logger.read("已点击登录按钮")

        return self._wait_login_success(url)

    def _wait_login_success(self, url):
        """等待登录跳转并验证结果"""
        try:
            self.page.wait_for_function("""
                () => {
                    if (location.pathname === '/index') return true;
                    if (!location.href.includes('login') && location.href !== '%s') return true;
                    return false;
                }
            """ % url, timeout=20000)
        except PlaywrightTimeoutError:
            pass

        current_url = self.page.url
        if 'login' in current_url.lower():
            self.logger.read(f"登录失败，仍在登录页: {current_url}")
            return False

        self.logger.read(f"登录成功，当前URL={self.page.url}")
        self._log_page_content()
        return True

    def _log_page_content(self):
        """输出当前页面URL和内容摘要"""
        try:
            url = self.page.url
            title = self.page.title()
            content = self.page.evaluate("""
                () => {
                    return document.body.innerText.substring(0, 500);
                }
            """)
            self.logger.read(f"\n【页面信息】")
            self.logger.read(f"URL: {url}")
            self.logger.read(f"标题: {title}")
            self.logger.read(f"内容摘要: {content[:200]}...")
        except Exception as e:
            self.logger.read(f"获取页面内容失败: {e}")

    def goto_page(self, url):
        """跳转到指定页面并输出内容"""
        self.logger.read(f"\n跳转到: {url}")
        self.page.goto(url, timeout=30000)
        self.page.wait_for_load_state('networkidle', timeout=10000)
        self._log_page_content()

    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
