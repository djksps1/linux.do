import os
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from playwright.sync_api import sync_playwright

# 邮件配置从环境变量获取
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.qq.com")  # QQ邮箱SMTP服务器
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))  # QQ邮箱SMTP端口
SMTP_USER = os.environ.get("SMTP_USER")  # QQ邮箱账号
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")  # QQ邮箱授权码
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")  # 接收通知的邮箱

# 用户名和密码从环境变量中获取
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

HOME_URL = "https://linux.do/"

class LinuxDoBrowser:
    def __init__(self) -> None:
        self.pw = sync_playwright().start()
        # 增加超时设置和其他浏览器选项
        self.browser = self.pw.firefox.launch(
            headless=True,
            args=['--disable-dev-shm-usage']  # 防止内存问题
        )
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        self.page = self.context.new_page()
        # 设置更长的超时时间（90秒）
        self.page.set_default_timeout(90000)
        self.page.goto(HOME_URL)

    def login(self):
        self.page.click(".login-button .d-button-label")
        time.sleep(2)
        self.page.fill("#login-account-name", USERNAME)
        time.sleep(2)
        self.page.fill("#login-account-password", PASSWORD)
        time.sleep(2)
        self.page.click("#login-button")
        time.sleep(10)
        user_ele = self.page.query_selector("#current-user")
        if not user_ele:
            print("Login failed")
            return False
        else:
            print("Check in success")
            return True

    def scroll_down(self):
        # 向下滚动以触发懒加载
        self.page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        time.sleep(2)  # 等待加载新内容

    def click_topic(self):
        max_browse_count = 500
        browsed_topics = []
        total_count = 0
        retry_count = 3  # 添加重试次数

        while total_count < max_browse_count:
            try:
                time.sleep(5)
                topics = self.page.query_selector_all("#list-area .title")

                if not topics:
                    print("未找到任何帖子，请检查选择器或页面加载情况。")
                    break

                new_topics = [t for t in topics if t not in browsed_topics]
                browsed_topics.extend(new_topics)

                if not new_topics:
                    print("没有加载出更多帖子。")
                    break

                for topic in new_topics:
                    if total_count >= max_browse_count:
                        break

                    try:
                        page = self.context.new_page()
                        page.set_default_timeout(90000)  # 为新页面也设置更长的超时时间
                        
                        for _ in range(retry_count):
                            try:
                                url = HOME_URL + topic.get_attribute("href")
                                page.goto(url)
                                break
                            except Exception as e:
                                print(f"访问帖子失败，正在重试... 错误: {str(e)}")
                                time.sleep(5)
                        
                        time.sleep(3)
                        
                        if random.random() < 0.02:
                            try:
                                self.click_like(page)
                            except Exception as e:
                                print(f"点赞失败: {str(e)}")

                        total_count += 1
                        print(f"已浏览 {total_count} 个帖子")
                        
                    except Exception as e:
                        print(f"处理帖子时出错: {str(e)}")
                    finally:
                        try:
                            page.close()
                        except:
                            pass

                self.scroll_down()

            except Exception as e:
                print(f"浏览帖子过程中出错: {str(e)}")
                time.sleep(10)  # 出错后等待一段时间再继续

        print(f"总共浏览了 {total_count} 个帖子")

    def run(self):
        if not self.login():
            return
        self.click_topic()
        self.print_connect_info()

    def click_like(self, page):
        page.locator(".discourse-reactions-reaction-button").first.click()
        print("Like success")

    def print_connect_info(self):
        page = self.context.new_page()
        page.goto("https://connect.linux.do/")
        rows = page.query_selector_all("table tr")

        info = []

        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) >= 3:
                project = cells[0].text_content().strip()
                current = cells[1].text_content().strip()
                requirement = cells[2].text_content().strip()
                info.append([project, current, requirement])

        # 使用 HTML 表格格式化数据
        html_table = "<table style='border-collapse: collapse; width: 100%; border: 1px solid black;'>"
        html_table += "<caption>在过去 100 天内：</caption>"
        html_table += "<tr><th style='border: 1px solid black; padding: 8px;'>项目</th><th style='border: 1px solid black; padding: 8px;'>当前</th><th style='border: 1px solid black; padding: 8px;'>要求</th></tr>"

        for row in info:
            html_table += "<tr>"
            for cell in row:
                html_table += f"<td style='border: 1px solid black; padding: 8px;'>{cell}</td>"
            html_table += "</tr>"

        html_table += "</table>"

        # 发送邮件
        try:
            # 创建邮件对象
            message = MIMEMultipart()
            message['From'] = Header(SMTP_USER)
            message['To'] = Header(RECIPIENT_EMAIL)
            message['Subject'] = Header('Linux.do 自动签到报告', 'utf-8')

            # 添加HTML内容
            message.attach(MIMEText(html_table, 'html', 'utf-8'))

            # 连接SMTP服务器并发送邮件
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()  # 启用TLS加密
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, RECIPIENT_EMAIL, message.as_string())
            print("邮件发送成功")
        except Exception as e:
            print(f"邮件发送失败: {str(e)}")
        
        page.close()

    def __del__(self):
        try:
            self.browser.close()
            self.pw.stop()
        except:
            pass

if __name__ == "__main__":
    required_env_vars = {
        "USERNAME": USERNAME,
        "PASSWORD": PASSWORD,
        "SMTP_USER": SMTP_USER,
        "SMTP_PASSWORD": SMTP_PASSWORD,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL
    }

    # 检查必要的环境变量
    missing_vars = [var for var, value in required_env_vars.items() if not value]
    if missing_vars:
        print(f"请设置以下环境变量: {', '.join(missing_vars)}")
        exit(1)
    
    l = LinuxDoBrowser()
    l.run()
