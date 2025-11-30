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
        self.username = os.environ.get("KLP_USERNAME")
        self.password = os.environ.get("KLP_PASSWORD")
        
        # 创建 scraper
        self.scraper = cloudscraper.create_scraper()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Referer": "https://www.klpbbs.com/forum.php",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }

    def load_cookies(self):
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
        try:
            with open(self.cookie_file, 'w') as f:
                json.dump(self.scraper.cookies.get_dict(), f)
        except:
            pass

    def get_formhash(self, text):
        """尝试多种正则提取 formhash"""
        # 模式1: input 标签中
        match1 = re.search(r'<input\s+type="hidden"\s+name="formhash"\s+value="([a-zA-Z0-9]+)"', text)
        if match1: return match1.group(1)
        
        # 模式2: 链接中 (logout 链接通常包含)
        match2 = re.search(r'formhash=([a-zA-Z0-9]+)', text)
        if match2: return match2.group(1)
        
        return None

    def check_login_status(self):
        """简单的登录检查"""
        try:
            # 访问积分页比主页更轻量且能验证登录
            res = self.scraper.get(f"{self.url}/home.php?mod=spacecp&ac=credit", headers=self.headers)
            if "注销" in res.text or self.username in res.text:
                return True
            return False
        except Exception as e:
            print(f"[!] 状态检查出错: {e}")
            return False

    def login(self):
        print("[-] 正在尝试登录...")
        login_url = f"{self.url}/member.php?mod=logging&action=login&infloat=yes&handlekey=login&inajax=1&ajaxtarget=fwin_content_login"
        
        try:
            res = self.scraper.get(login_url, headers=self.headers)
            formhash = self.get_formhash(res.text)
            
            if not formhash:
                print("[!] 登录页面无法获取 formhash，可能是 Cloudflare 拦截")
                return False

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
                print(f"[!] 登录失败响应: {resp.text[:100]}")
                return False
        except Exception as e:
            print(f"[!] 登录异常: {e}")
            return False

    def run_sign(self):
        # 1. 登录流程
        self.load_cookies()
        if not self.check_login_status():
            if not self.login():
                return

        print("[-] 开始执行签到流程...")
        
        # 2. 访问签到插件主页 (获取签到专用的 formhash)
        plugin_url = f"{self.url}/plugin.php?id=dsu_paulsign:sign"
        try:
            # 必须先访问这个页面，模拟真实用户浏览，并获取页面中的 Hash
            page_res = self.scraper.get(plugin_url, headers=self.headers)
            
            # 检查是否已签到
            if "您今天已经签到过了" in page_res.text or "已签到" in page_res.text:
                print("[√] 检测到今天已经签到过了")
                return

            # 提取 formhash
            formhash = self.get_formhash(page_res.text)
            if not formhash:
                print("[!] 严重错误：在签到页面无法找到 formhash。")
                print(f"[debug] 页面标题: {re.search(r'<title>(.*?)</title>', page_res.text).group(1) if '<title>' in page_res.text else '无标题'}")
                print(f"[debug] 页面前500字符: {page_res.text[:500]}")
                # 很多时候是因为没权限或者页面变了
                return

            print(f"[-] 获取到签到 Formhash: {formhash}")

            # 3. 构造签到请求
            # URL 需要包含 operation=qiandao
            sign_api = f"{self.url}/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&inajax=1"
            
            # 关键：DSU 插件通常要求的参数
            data = {
                "formhash": formhash,
                "qdxq": "kx",       # 心情：开心
                "qdmode": "1",      # 模式：自己填写
                "todaysay": "每日自动签到", # 签到语
                "fastreply": "0"
            }
            
            # 更新 Header，模拟表单提交
            post_headers = self.headers.copy()
            post_headers.update({
                "Origin": self.url,
                "Referer": plugin_url,
                "Content-Type": "application/x-www-form-urlencoded"
            })

            # 发送请求
            sign_res = self.scraper.post(sign_api, data=data, headers=post_headers)
            
            # 4. 结果判断
            if "succeed" in sign_res.text or "成功" in sign_res.text:
                print("[√] 签到成功！")
            elif "已经签到" in sign_res.text:
                print("[√] 签到成功 (服务器返回已签到)")
            else:
                print("[!] 签到请求发送了，但返回结果不明确")
                print(f"[debug] 返回内容: {sign_res.text[:300]}")

        except Exception as e:
            print(f"[!] 签到环节发生异常: {e}")

if __name__ == "__main__":
    bot = KlpbbsSign()
    bot.run_sign()
