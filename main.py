# main.py
import requests
import cloudscraper
import os
import json
import re
import time
from datetime import datetime

class KlpbbsSign:
    def __init__(self):
        self.url = "https://www.klpbbs.com"
        self.cookie_file = "cookies.json"
        # 从环境变量获取账号密码
        self.username = os.environ.get("KLP_USERNAME")
        self.password = os.environ.get("KLP_PASSWORD")
        
        # 使用 cloudscraper 绕过 Cloudflare
        self.scraper = cloudscraper.create_scraper()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Referer": "https://www.klpbbs.com/forum.php"
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
            except Exception as e:
                print(f"[!] Cookie 文件读取失败: {e}")
        return False

    def save_cookies(self):
        """保存Cookie到本地"""
        try:
            with open(self.cookie_file, 'w') as f:
                json.dump(self.scraper.cookies.get_dict(), f)
            print("[-] Cookie 已保存/更新")
        except Exception as e:
            print(f"[!] Cookie 保存失败: {e}")

    def get_formhash(self, text):
        """正则提取 formhash"""
        match = re.search(r'name="formhash" value="(.+?)"', text)
        if match:
            return match.group(1)
        return None

    def check_login_status(self):
        """检查是否登录成功"""
        try:
            res = self.scraper.get(f"{self.url}/home.php?mod=space&do=profile", headers=self.headers)
            if self.username in res.text or "用户组" in res.text:
                return True, res.text
            return False, res.text
        except Exception as e:
            print(f"[!] 检查登录状态出错: {e}")
            return False, ""

    def login(self):
        """执行登录"""
        print("[-] Cookie 失效或不存在，尝试账号密码登录...")
        if not self.username or not self.password:
            print("[!] 未检测到环境变量 KLP_USERNAME 或 KLP_PASSWORD")
            return False

        login_url = f"{self.url}/member.php?mod=logging&action=login&infloat=yes&handlekey=login&inajax=1&ajaxtarget=fwin_content_login"
        
        try:
            # 1. 获取登录页面的 formhash
            res = self.scraper.get(login_url, headers=self.headers)
            formhash = self.get_formhash(res.text)
            
            if not formhash:
                print("[!] 无法获取登录 formhash")
                return False

            # 2. 提交登录
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
            
            if "欢迎您回来" in resp.text or "succeed" in resp.text:
                print("[-] 登录成功")
                self.save_cookies()
                return True
            else:
                print(f"[!] 登录失败，响应内容摘要: {resp.text[:100]}...")
                return False
                
        except Exception as e:
            print(f"[!] 登录过程发生异常: {e}")
            return False

    def run_sign(self):
        """执行签到"""
        # 加载 Cookie 或 登录
        self.load_cookies()
        is_logged_in, html_text = self.check_login_status()
        
        if not is_logged_in:
            if not self.login():
                print("[X] 登录失败，终止签到")
                return
        
        # 获取签到页面的 formhash
        print("[-] 准备签到...")
        plugin_url = f"{self.url}/plugin.php?id=dsu_paulsign:sign"
        
        try:
            res = self.scraper.get(plugin_url, headers=self.headers)
            if "您今天已经签到过了" in res.text:
                print("[*] 今天已经签到过了")
                return

            formhash = self.get_formhash(res.text)
            if not formhash:
                # 尝试再次获取（有时页面结构不同）
                formhash = self.get_formhash(html_text)
            
            if not formhash:
                print("[!] 无法获取签到 formhash，可能需要手动验证或网站结构变更")
                return

            # 构造签到请求
            sign_api = f"{self.url}/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&inajax=1"
            data = {
                "formhash": formhash,
                "qdxq": "kx",  # 开心
                "qdmode": "1", # 1=自己填写, 2=快速签到, 3=表情
                "todaysay": "每日签到，自动执行",
                "fastreply": "0"
            }
            
            sign_res = self.scraper.post(sign_api, data=data, headers=self.headers)
            
            if "succeed" in sign_res.text or "恭喜你签到成功" in sign_res.text:
                print("[√] 签到成功！")
            elif "已经签到" in sign_res.text:
                print("[*] 重复检测：今天已经签到过了")
            else:
                print(f"[!] 签到返回未知结果: {sign_res.text[:200]}")

        except Exception as e:
            print(f"[!] 签到请求异常: {e}")

if __name__ == "__main__":
    print(f"--- 开始执行: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    bot = KlpbbsSign()
    bot.run_sign()