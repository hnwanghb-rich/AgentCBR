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
        """登录系统"""
        try:
            url = self.config['website']['url']
            self.logger.read(f"访问登录页面: {url}")
            self.page.goto(url, wait_until="networkidle", timeout=60000)
            self.logger.read(f"页面加载完成，当前URL={self.page.url}")
            return self._do_login(url)
        except Exception as e:
            self.logger.read(f"登录异常: {str(e)}")
            return False

    def _do_login(self, url):
        """执行登录操作（通过role/name查找输入框，去空格匹配）"""
        username = self.config['website']['username']
        password = self.config['website']['password']

        # 查找账号输入框：name含'账号'（去空格）
        u_input = self.page.get_by_role("textbox", name="账号")
        # 查找密码输入框：name含'密码'（去空格）
        p_input = self.page.get_by_role("textbox", name="密码")

        self.logger.read("填写账号")
        u_input.click()
        u_input.fill(username)
        self.page.evaluate("""
            () => {
                const els = Array.from(document.querySelectorAll('input'));
                const el = els.find(e => (e.placeholder || e.name || e.getAttribute('aria-label') || '').replace(/\\s/g, '').includes('账号'));
                if (el) {
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }
        """)

        self.logger.read("填写密码")
        p_input.click()
        p_input.fill(password)
        self.page.evaluate("""
            () => {
                const els = Array.from(document.querySelectorAll('input'));
                const el = els.find(e => (e.placeholder || e.name || e.getAttribute('aria-label') || '').replace(/\\s/g, '').includes('密码'));
                if (el) {
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }
        """)

        self.logger.read("点击登录按钮")
        # 查找登录按钮：role=button, name去空格后=='登录'
        btn = self.page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                const target = btns.find(b => b.innerText.replace(/\\s/g, '') === '登录');
                if (target) { target.click(); return true; }
                return false;
            }
        """)
        if not btn:
            # fallback: playwright get_by_role
            self.page.get_by_role("button", name="登 录").click()

        try:
            self.page.wait_for_url(lambda u: u != url, timeout=15000)
        except PlaywrightTimeoutError:
            self.logger.read("等待跳转超时，检查当前页面")

        # 该平台登录后URL可能仍含'login'，改为检查登录表单是否消失
        import time
        time.sleep(1)
        login_form_gone = self.page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input[type="password"]');
                return inputs.length === 0;
            }
        """)

        if not login_form_gone:
            self.logger.read("登录失败，密码框仍存在")
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
                () => { return document.body.innerText.substring(0, 500); }
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
