import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 也就是你扒出来的那个签到插件链接，去掉具体的 formhash，只保留前缀
SIGN_URL_BASE = "https://www.klpbbs.com/plugin.php?id=k_misign:sign&operation=qiandao&format=text"

def run_bot():
    username = os.environ.get("KLP_USERNAME")
    password = os.environ.get("KLP_PASSWORD")

    if not username or not password:
        print("错误：未设置环境变量 KLP_USERNAME 或 KLP_PASSWORD")
        return

    # --- 配置 Chrome 浏览器 ---
    chrome_options = Options()
    chrome_options.add_argument("--headless") # 无头模式，无界面运行
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # 模拟真实 User-Agent，防止被轻易拦截
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("[-] 1. 打开论坛首页...")
        driver.get("https://www.klpbbs.com/member.php?mod=logging&action=login")
        
        # 等待用户名输入框加载
        wait = WebDriverWait(driver, 15)
        user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        
        print("[-] 2. 输入账号密码...")
        user_input.send_keys(username)
        pass_input = driver.find_element(By.NAME, "password")
        pass_input.send_keys(password)
        
        # 点击登录按钮
        submit_btn = driver.find_element(By.NAME, "loginsubmit")
        # 有时候按钮需要用 JS 点击才稳
        driver.execute_script("arguments[0].click();", submit_btn)
        
        print("[-] 3. 等待登录跳转...")
        time.sleep(5) # 强制等待页面刷新
        
        # 截图验证登录状态 (调试用)
        driver.save_screenshot("debug_login.png")

        # 检查是否登录成功 (查看页面有没有用户名)
        if username not in driver.page_source and "注销" not in driver.page_source:
            print("[!] 登录可能失败，请查看 debug_login.png")
            # 这里不退出，尝试强行访问签到链接试试
        else:
            print("[-] 登录成功！")

        # --- 获取 Formhash (Selenium 会自动处理) ---
        # 只要登录了，浏览器会自动携带 Cookie，我们直接访问签到 API 即可
        # 这一步我们先访问首页，让浏览器解析出 formhash
        formhash = "unknown"
        try:
            # 从页面源码提取 formhash，selenium 不需要复杂的正则，直接执行 JS 也可以
            # 但最简单的方法是直接访问签到页，浏览器会自动把 session 带过去
            pass 
        except:
            pass

        print("[-] 4. 访问签到接口...")
        # 我们这里做一个骚操作：直接访问签到插件的界面，找到签到按钮（或者直接请求API）
        # 由于我们不知道实时的 formhash，我们通过访问插件主页来签到
        driver.get("https://www.klpbbs.com/plugin.php?id=k_misign:sign")
        time.sleep(3)
        driver.save_screenshot("debug_sign_page.png")
        
        # 尝试点击签到按钮 (通常 id 是 JD_sign 或类似的，或者查找链接)
        # 这里使用最通用的方法：查找页面上包含 "签到" 的链接或按钮
        try:
            # 寻找 href 中包含 operation=qiandao 的链接
            sign_link = driver.find_element(By.XPATH, "//a[contains(@href, 'operation=qiandao')]")
            print(f"[-] 找到签到按钮链接: {sign_link.get_attribute('href')}")
            sign_link.click()
            print("[-] 点击了签到按钮")
            time.sleep(3)
            driver.save_screenshot("debug_sign_result.png")
            print("[√] 签到流程执行完毕，请查看截图确认结果")
        except Exception as e:
            print(f"[!] 未找到显式签到按钮，尝试直接访问 API (尝试自动提取 formhash)")
            # 备选方案：正则从当前页面源代码里找 formhash
            import re
            match = re.search(r'formhash=([a-zA-Z0-9]+)', driver.page_source)
            if match:
                current_formhash = match.group(1)
                print(f"[-] 提取到的 formhash: {current_formhash}")
                final_url = f"{SIGN_URL_BASE}&formhash={current_formhash}"
                driver.get(final_url)
                time.sleep(2)
                print(f"[-] API 返回内容: {driver.find_element(By.TAG_NAME, 'body').text}")
            else:
                print("[X] 无法提取 Formhash，签到失败")

    except Exception as e:
        print(f"[X] 发生异常: {e}")
        driver.save_screenshot("debug_error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_bot()
