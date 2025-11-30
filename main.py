import os
import time
import re
from DrissionPage import ChromiumPage, ChromiumOptions

def run_sign():
    username = os.environ.get("KLP_USERNAME")
    password = os.environ.get("KLP_PASSWORD")
    
    if not username or not password:
        print("[!] 错误：未设置 KLP_USERNAME 或 KLP_PASSWORD")
        return

    # --- 配置浏览器 ---
    co = ChromiumOptions()
    co.auto_port()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--window-size=1920,1080')
    # 模拟常见浏览器 User-Agent
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    print("[-] 正在启动 DrissionPage (Xvfb模式)...")
    try:
        page = ChromiumPage(co)
        # 设置全局超时时间
        page.set.timeouts(15)
    except Exception as e:
        print(f"[X] 浏览器启动失败: {e}")
        return
    
    try:
        # 1. 访问登录页
        print("[-] 1. 访问登录页面...")
        page.get("https://www.klpbbs.com/member.php?mod=logging&action=login")
        
        # --- 对抗 Cloudflare 核心逻辑 ---
        if "Just a moment" in page.title or "Cloudflare" in page.title:
            print("[!] 检测到 Cloudflare 验证，尝试自动通过...")
            time.sleep(5) 
            
            for i in range(5):
                if "Just a moment" not in page.title:
                    print("[-] Cloudflare 验证通过！")
                    break
                print(f"[-] 等待 CF 跳转... ({i+1}/5)")
                time.sleep(3)
        
        # 2. 执行登录
        print("[-] 2. 寻找登录框...")
        
        # 使用 ele 查找元素
        user_input = page.ele('name=username') 
        
        if not user_input:
            print("[!] 未找到用户名输入框，可能还在 CF 验证页或加载失败")
            page.get_screenshot(path='debug_login_fail.png')
            return

        print("[-] 输入账号信息...")
        user_input.input(username)
        page.ele('name=password').input(password)
        
        print("[-] 点击登录...")
        login_btn = page.ele('name=loginsubmit')
        if login_btn:
            login_btn.hover()
            time.sleep(0.5)
            login_btn.click()
        else:
            print("[!] 没找到登录按钮，尝试回车")
            page.ele('name=password').input('\n')
        
        time.sleep(5)
        
        # 验证是否登录成功
        html_content = page.html
        if username in html_content or "注销" in html_content:
             print("[-] 登录成功！")
        else:
             print("[!] 登录状态存疑，截图已保存")
             page.get_screenshot(path='debug_login_status.png')

        # 3. 执行签到 (API 模式)
        print("[-] 3. 获取 Formhash 并签到...")
        
        html = page.html
        match = re.search(r'formhash=([a-zA-Z0-9]+)', html)
        
        if match:
            current_formhash = match.group(1)
            print(f"[-] 提取到 Formhash: {current_formhash}")
            
            # 构造链接
            sign_url = f"https://www.klpbbs.com/plugin.php?id=k_misign:sign&operation=qiandao&format=text&formhash={current_formhash}"
            
            print(f"[-] 访问签到接口: {sign_url}")
            page.get(sign_url)
            
            content = page.ele('tag:body').text
            print(f"[-] 接口返回: {content}")
            page.get_screenshot(path='debug_sign_result.png')
            
            if "成功" in content or "succeed" in content:
                print("[√] 签到成功！")
            elif "已" in content or "来过" in content:
                print("[√] 今天已签到")
            else:
                print("[?] 返回结果未知，请查看截图")
        else:
            print("[!] 无法提取 Formhash，尝试备用方案：模拟点击...")
            page.get("https://www.klpbbs.com/plugin.php?id=k_misign:sign")
            
            try:
                sign_btn = page.ele('xpath://a[contains(@href, "operation=qiandao")]')
                if sign_btn:
                    print("[-] 找到签到按钮，点击中...")
                    sign_btn.click()
                    time.sleep(3)
                    page.get_screenshot(path='debug_sign_click.png')
                    print("[√] 已执行点击操作")
                else:
                    print("[X] 未找到签到按钮，任务失败")
            except Exception as e:
                print(f"[X] 点击备用方案失败: {e}")

    except Exception as e:
        print(f"[X] 脚本运行异常: {e}")
        try:
            page.get_screenshot(path='debug_crash.png')
        except:
            pass
    finally:
        try:
            page.quit()
        except:
            pass

if __name__ == "__main__":
    run_sign()
