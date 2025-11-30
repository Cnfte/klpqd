import os
import time
from DrissionPage import ChromiumPage, ChromiumOptions

def run_sign():
    username = os.environ.get("KLP_USERNAME")
    password = os.environ.get("KLP_PASSWORD")
    
    if not username or not password:
        print("[!] 缺账号密码")
        return

    # --- 配置浏览器 ---
    co = ChromiumOptions()
    # 关键：不使用 headless 模式！我们要用 xvfb 伪造有头模式
    # co.headless(True)  <-- 绝对不要开这个
    
    # 自动下载/查找浏览器路径
    co.auto_port()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--window-size=1920,1080')
    # 尽可能模拟真实用户
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    print("[-] 正在启动 DrissionPage...")
    page = ChromiumPage(co)
    
    try:
        # 1. 访问登录页
        print("[-] 1. 访问登录页面...")
        page.get("https://www.klpbbs.com/member.php?mod=logging&action=login")
        
        # --- 对抗 Cloudflare 核心逻辑 ---
        # Cloudflare 验证通常是一个 iframe，或者页面标题包含 "Just a moment"
        if "Just a moment" in page.title or "Cloudflare" in page.title:
            print("[!] 检测到 Cloudflare 验证，开始尝试绕过...")
            time.sleep(5) # 给它一点时间加载 Turnstile 里的 checkbox
            
            # 尝试寻找 CF 的 checkbox 并点击
            # Cloudflare 的结构经常变，DrissionPage 甚至不需要显式点击，
            # 只要它是"有头"运行的，CF 经常会自动放行。
            
            # 循环检测是否通过
            for i in range(10):
                if "Just a moment" not in page.title:
                    print("[-] Cloudflare 验证通过！")
                    break
                print(f"[-] 等待 CF 验证跳转... ({i+1}/10)")
                
                # 尝试点击可能存在的验证框 (这是 CF Turnstile 的常见特征)
                # 查找 shadow-root 里的 checkbox
                try:
                    # 这是一个比较暴力的查找，尝试点击所有可能的验证框
                    ele = page.ele('@type=checkbox')
                    if ele: ele.click()
                except:
                    pass
                
                time.sleep(3)
        
        # 2. 执行登录
        print("[-] 2. 输入账号信息...")
        # 等待用户名框出现
        page.wait.ele('name=username', timeout=15)
        
        page.ele('name=username').input(username)
        page.ele('name=password').input(password)
        
        print("[-] 点击登录...")
        # 为了更像人，先移动鼠标再点击
        login_btn = page.ele('name=loginsubmit')
        login_btn.hover() 
        time.sleep(0.5)
        login_btn.click()
        
        # 等待跳转
        time.sleep(5)
        
        # 截图看状态
        page.get_screenshot(path='debug_login.png', full_page=True)
        
        if username in page.html or "注销" in page.html:
             print("[-] 登录成功！")
        else:
             print("[!] 登录可能失败，请查看截图")
             # 继续尝试签到，万一其实登录上了呢

        # 3. 执行签到 (使用之前发现的 API)
        print("[-] 3. 访问签到接口...")
        # 先去首页晃一下确保 Cookie 没问题
        page.get("https://www.klpbbs.com/forum.php")
        
        # 获取 formhash (DrissionPage 获取极其简单)
        # 尝试从页面源码直接提取
        import re
        html = page.html
        match = re.search(r'formhash=([a-zA-Z0-9]+)', html)
        if match:
            current_formhash = match.group(1)
            print(f"[-] 提取到 Formhash: {current_formhash}")
            
            # 构造链接
            sign_url = f"https://www.klpbbs.com/plugin.php?id=k_misign:sign&operation=qiandao&format=text&formhash={current_formhash}"
            page.get(sign_url)
            
            # 获取结果
            content = page.ele('tag:body').text
            print(f"[-] 签到结果: {content}")
            page.get_screenshot(path='debug_result.png')
            
            if "成功" in content or "succeed" in content or "已" in content:
                print("[√] 任务完成")
            else:
                print("[?] 结果未知")
        else:
            print("[!] 无法在首页提取 formhash，尝试直接点击签到页面")
            # 备选方案：去界面点击
            page.get("https://www.klpbbs.com/plugin.php?id=k_misign:sign")
            # 查找那个签到按钮
            try:
                btn = page.ele('xpath://a[contains(@href, "operation=qiandao")]')
                if btn:
                    btn.click()
                    print("[-] 已点击界面签到按钮")
                else:
                    print("[X] 没找到签到按钮")
            except:
                pass
                
    except Exception as e:
        print(f"[X] 运行出错: {e}")
        page.get_screenshot(path='debug_error.png')
    finally:
        page.quit()

if __name__ == "__main__":
    run_sign()
