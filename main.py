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
    co.set_argument('--mute-audio') # 静音
    # 模拟真实 User-Agent
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    print("[-] 正在启动 DrissionPage (Xvfb模式)...")
    try:
        page = ChromiumPage(co)
        # 设置全局查找元素超时时间为 5 秒 (不用太长，我们在循环里控制)
        page.set.timeouts(5)
    except Exception as e:
        print(f"[X] 浏览器启动失败: {e}")
        return
    
    try:
        # 1. 访问登录页
        login_url = "https://www.klpbbs.com/member.php?mod=logging&action=login"
        print(f"[-] 1. 访问登录页面: {login_url}")
        page.get(login_url)
        
        # ==========================================
        # 核心：Cloudflare 强力对抗逻辑
        # ==========================================
        print("[-] 进入 Cloudflare 检测/等待流程 (限时60秒)...")
        
        cf_success = False
        start_time = time.time()
        
        while time.time() - start_time < 60:
            # 1. 检查成功标志：如果能找到用户名输入框，说明 CF 过了
            if page.ele('name=username', timeout=1):
                print("[-] 成功检测到登录框，Cloudflare 已通过！")
                cf_success = True
                break
            
            # 2. 检查失败标志：Cloudflare 标题
            title = page.title
            if "Just a moment" in title or "Cloudflare" in title:
                print(f"[-] 正在处理 CF 验证... (当前标题: {title})")
                
                # 尝试点击 Turnstile 验证框
                # Cloudflare 的验证框通常在 Shadow DOM 里，DrissionPage 可以自动穿透
                try:
                    # 尝试查找并点击复选框 (通用特征)
                    # 查找 type=checkbox 的元素
                    cb = page.ele('@type=checkbox', timeout=1)
                    if cb:
                        print("[-] 发现可能的验证框，尝试点击...")
                        cb.click()
                        time.sleep(2)
                except:
                    pass
            else:
                print(f"[-] 页面加载中... 标题: {title}")
            
            time.sleep(2)
            
        if not cf_success:
            print("[!] Cloudflare 验证超时或失败！")
            page.get_screenshot(path='debug_cf_fail.png')
            # 即使超时也尝试往下走，万一只是元素没找到呢
        
        # ==========================================
        # 2. 执行登录
        # ==========================================
        print("[-] 2. 开始登录操作...")
        
        user_input = page.ele('name=username') 
        if not user_input:
            print("[!] 致命错误：找不到用户名输入框，脚本终止。")
            print(f"当前页面源码摘要: {page.html[:200]}")
            page.get_screenshot(path='debug_login_fail.png')
            return

        print("[-] 输入账号密码...")
        user_input.input(username)
        page.ele('name=password').input(password)
        
        print("[-] 点击登录按钮...")
        login_btn = page.ele('name=loginsubmit')
        if login_btn:
            # 模拟鼠标悬停
            login_btn.hover()
            time.sleep(0.5)
            login_btn.click()
        else:
            # 回车兜底
            page.ele('name=password').input('\n')
        
        # 等待登录跳转
        print("[-] 等待跳转 (10秒)...")
        time.sleep(10)
        
        # 验证是否登录成功
        if username in page.html or "注销" in page.html:
             print("[-] 登录成功！")
        else:
             print("[!] 登录可能失败 (未在页面检测到用户名)，继续尝试签到...")
             page.get_screenshot(path='debug_login_status.png')

        # ==========================================
        # 3. 执行签到 (API 模式)
        # ==========================================
        print("[-] 3. 获取 Formhash 并签到...")
        
        # 刷新页面源码
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
                print("[?] 返回结果未知，请查看截图或日志")
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
