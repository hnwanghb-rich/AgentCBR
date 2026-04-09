import json
from openai import OpenAI


class DeepSeekAgent:
    """使用 DeepSeek API 处理页面内容的智能代理（OpenAI 兼容接口）"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        ds_cfg = config.get('deepseek', {})
        self.client = OpenAI(
            api_key=ds_cfg.get('api_key', ''),
            base_url=ds_cfg.get('base_url', 'https://api.deepseek.com')
        )

    def _call(self, system_prompt, user_content, max_tokens=4096):
        try:
            resp = self.client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            self.logger.read(f"[DeepSeek] API调用失败: {e}")
            return ""

    def _parse_json(self, text, fallback):
        try:
            # 去掉可能的 markdown 代码块
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception:
            self.logger.read(f"[DeepSeek] JSON解析失败，原始: {text[:200]}")
            return fallback

    def login(self, page_html, username, password):
        """分析登录页面，返回输入框和提交按钮的 CSS 选择器"""
        system = (
            "你是网页自动化助手。分析登录页面HTML，找到用户名输入框、密码输入框和登录按钮的CSS选择器。"
            "只返回JSON，格式：{\"username_selector\": \"...\", \"password_selector\": \"...\", \"submit_selector\": \"...\"}"
        )
        result = self._call(system, f"页面HTML:\n{page_html[:8000]}")
        return self._parse_json(result, None)

    def extract_table_data(self, page_html, context=""):
        """从页面 HTML 提取表格数据"""
        system = (
            "你是数据提取助手。从HTML中提取表格数据。"
            "只返回JSON，格式：{\"headers\": [\"列名\", ...], \"rows\": [[\"值\", ...], ...]}"
            "如果没有表格，返回 {\"headers\": [], \"rows\": []}"
        )
        prompt = f"{context}\n\n页面HTML:\n{page_html[:10000]}"
        result = self._call(system, prompt)
        return self._parse_json(result, {"headers": [], "rows": []})

    def find_action_buttons(self, page_html, action="进入"):
        """找到指定操作按钮的 CSS 选择器列表"""
        system = (
            f"你是网页分析助手。从HTML中找到所有\"{action}\"按钮的CSS选择器。"
            "只返回JSON，格式：{\"selectors\": [\"selector1\", ...]}"
        )
        result = self._call(system, f"页面HTML:\n{page_html[:8000]}")
        return self._parse_json(result, {"selectors": []}).get("selectors", [])

    def find_org_node(self, page_html):
        """找到组织架构树顶级节点的 CSS 选择器"""
        system = (
            "你是网页分析助手。从HTML中找到组织架构树的顶级节点（通常是公司名称）的CSS选择器。"
            "只返回JSON，格式：{\"selector\": \"...\", \"text\": \"节点文本\"}"
        )
        result = self._call(system, f"页面HTML:\n{page_html[:8000]}")
        return self._parse_json(result, None)

    def find_download_links(self, page_html):
        """找到所有下载按钮或链接的 CSS 选择器"""
        system = (
            "你是网页分析助手。从HTML中找到所有下载按钮或链接的CSS选择器。"
            "只返回JSON，格式：{\"selectors\": [\"selector1\", ...]}"
        )
        result = self._call(system, f"页面HTML:\n{page_html[:8000]}")
        return self._parse_json(result, {"selectors": []}).get("selectors", [])

    def get_pagination_info(self, page_html):
        """获取分页信息：总页数和下一页按钮选择器"""
        system = (
            "你是网页分析助手。从HTML中找到分页组件，返回总页数和下一页按钮选择器。"
            "只返回JSON，格式：{\"total_pages\": 1, \"next_selector\": \"CSS选择器或null\"}"
        )
        result = self._call(system, f"页面HTML:\n{page_html[:5000]}")
        return self._parse_json(result, {"total_pages": 1, "next_selector": None})
