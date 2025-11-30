import requests
import cloudscraper
import os
import json
import re
import time
from datetime import datetime
import xml.etree.ElementTree as ET

class KlpbbsSign:
    def __init__(self):
        self.url = "https://www.klpbbs.com"
        self.cookie_file = "cookies.json"
        self.username = os.environ.get("KLP_USERNAME")
        self.password = os.environ.get("KLP_PASSWORD")
        
        self.scraper = cloudscraper.create_scraper()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Referer": "https://www.klpbbs.com/forum.php",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        }

    def load_cookies(self):
        """加载本地Cookie"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r') as f:
                    cookies = json.load(f)
                    self.scraper.cookies.update(cookies)
                print("[-] 已加载本地 Cookie")
                return True
            except:
                pass
        return False

    def save_cookies(self):
        """保存Cookie"""
        try:
            with open(self.cookie_file, 'w') as f:
                json.dump(self.scraper.cookies.get_dict(), f)
        except:
            pass

    def get_formhash(self, text):
        """正则提取 formhash"""
        match = re.search(r'formhash=([a-zA-Z0-9]+)', text)
        if match: return match.group(1)
        match_input = re.search(r'name="formhash" value="([a-zA-Z0-9]+)"', text)
        if match_input: return match_input.group(1)
        return None

    def login(self):
        """登录逻辑"""
        print("[-] 正在尝试登录...")
        login_page_url = f"{self.url}/member.php?mod=logging&action=login&infloat=yes&handlekey=login&inajax=1&ajaxtarget=fwin_content_login"
        
        try:
            # 1. 获取登录页 formhash
            res = self.scraper.get(login_page_url, headers=self.headers)
            formhash = self.get_formhash(res.text)
            if not formhash:
                print("[!] 无法获取登录 Formhash，可能被防火墙拦截")
                return False

            # 2. 发送登录请求
            data = {
                "formhash": formhash,
                "referer": f"{self.url}/portal.php",
                "username": self.username,
                "password": self.password,
                "questionid": "0",
                "answer": "",
                "loginsubmit": "true"
            }
            post_url = f"{self.url}/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1"
            resp = self.scraper.post(post_url, data=data, headers=self.headers)
            
            if "succeed" in resp.text or "欢迎" in resp.text:
                print("[-] 登录成功")
                self.save_cookies()
                return True
            else:
                print(f"[!] 登录失败: {resp.text[:100]}")
                return False
        except Exception as e:
            print(f"[!] 登录过程异常: {e}")
            return False

    def check_login(self):
        """验证Cookie是否有效"""
        try:
            res = self.scraper.get(f"{self.url}/home.php?mod=spacecp&ac=credit", headers=self.headers)
            if self.username in res.text or "注销" in res.text:
                return True, res.text
            return False, res.text
        except:
            return False, ""

    def run_sign(self):
        # 1. 初始化登录
        self.load_cookies()
        is_login, html_text = self.check_login()
        
        if not is_login:
            if not self.login():
                return
            # 登录后刷新一下页面获取最新的 formhash
            _, html_text = self.check_login()

        print("[-] 准备执行签到...")
        
        # 2. 获取 Formhash (核心步骤)
        # 我们需要从任意一个已登录的页面提取当前的 formhash
        formhash = self.get_formhash(html_text)
        
        if not formhash:
            # 如果从积分页没拿到，尝试去签到插件主页拿
            print("[-] 尝试从插件主页获取 Formhash...")
            plugin_page = self.scraper.get(f"{self.url}/plugin.php?id=k_misign:sign", headers=self.headers)
            formhash = self.get_formhash(plugin_page.text)
        
        if not formhash:
            print("[!] 严重错误: 无法获取 Formhash，无法构建签到链接")
            return

        print(f"[-] 获取到 Formhash: {formhash}")

        # 3. 构建 API 请求 (使用你抓到的接口)
        # 格式: plugin.php?id=k_misign:sign&operation=qiandao&format=text&formhash=xxxx
        sign_url = f"{self.url}/plugin.php?id=k_misign:sign&operation=qiandao&format=text&formhash={formhash}"
        
        try:
            # k_misign 插件通常接受 GET 请求
            res = self.scraper.get(sign_url, headers=self.headers)
            content = res.text

            print(f"[-] 服务器返回: {content}")

            # 4. 结果判定
            # 返回值通常是 XML 格式，例如:
            # <root><![CDATA[恭喜你签到成功!....]]></root>
            # 或者纯文本
            
            if "签到成功" in content or "succeed" in content:
                print("[√] 签到成功！")
            elif "已签到" in content or "来过" in content:
                print("[√] 今天已经签到过了")
            elif "需要先登录" in content:
                print("[!] Cookie 失效，需要重新登录")
            else:
                print("[?] 未知结果，请手动检查上面的服务器返回内容")

        except Exception as e:
            print(f"[!] 签到请求异常: {e}")

if __name__ == "__main__":
    print(f"--- 任务开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    bot = KlpbbsSign()
    bot.run_sign()