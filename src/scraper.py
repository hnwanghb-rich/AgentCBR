from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import requests
from pathlib import Path
from progress import ProgressTracker
from document_processor import DocumentProcessor
from output_generator import OutputGenerator

class WebScraper:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.progress = ProgressTracker(config['log']['directory'])
        self.doc_processor = DocumentProcessor(logger)
        self.output_gen = OutputGenerator(config['output']['directory'], logger)
        self.driver = None

    def init_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(self.config['website']['timeout'])

    def login(self):
        try:
            self.driver.get(self.config['website']['url'])
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            self.driver.find_element(By.NAME, "username").send_keys(self.config['website']['username'])
            self.driver.find_element(By.NAME, "password").send_keys(self.config['website']['password'])
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(2)
            self.logger.info("登录成功")
            return True
        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            return False

    def download_attachment(self, url, filename):
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        file_path = temp_dir / filename
        try:
            response = requests.get(url, timeout=30)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
        except Exception as e:
            self.logger.error(f"下载附件失败: {e}")
            return None

    def process_row(self, row_element, index):
        try:
            title = row_element.find_element(By.CSS_SELECTOR, ".title").text
            content = row_element.find_element(By.CSS_SELECTOR, ".content").text

            attachments = row_element.find_elements(By.CSS_SELECTOR, "a.attachment")
            attachment_data = []

            for att in attachments:
                url = att.get_attribute("href")
                filename = att.text
                file_path = self.download_attachment(url, filename)

                if file_path:
                    ext = file_path.suffix.lower()
                    if ext == '.pdf':
                        text = self.doc_processor.process_pdf(file_path)
                        attachment_data.append({"type": "text", "content": text})
                    elif ext in ['.jpg', '.png', '.jpeg']:
                        text, img = self.doc_processor.process_image(file_path)
                        attachment_data.append({"type": "image", "content": text, "image": img})
                    elif ext in ['.doc', '.docx']:
                        text = self.doc_processor.process_word(file_path)
                        attachment_data.append({"type": "text", "content": text})
                    elif ext in ['.xls', '.xlsx']:
                        text = self.doc_processor.process_excel(file_path)
                        attachment_data.append({"type": "text", "content": text})

            self.output_gen.generate_document(title, content, attachment_data, index)
            self.progress.update_index(index)
            self.logger.info(f"处理完成第 {index} 条记录: {title}")

        except Exception as e:
            self.logger.error(f"处理第 {index} 条记录失败: {e}")

    def run(self):
        self.init_driver()
        if not self.login():
            return

        last_index = self.progress.get_last_index()
        self.logger.info(f"从第 {last_index + 1} 条记录开始处理")

        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".list-row")
            for i, row in enumerate(rows):
                if i <= last_index:
                    continue
                self.process_row(row, i)
        except TimeoutException:
            self.logger.warning("会话超时，尝试重新登录")
            self.login()

    def close(self):
        if self.driver:
            self.driver.quit()
