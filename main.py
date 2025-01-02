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
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))  # QQ邮箱SMTP端口
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
        self.browser = self.pw.firefox.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
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
        max_browse_count = 500  # 希望浏览的帖子数
        browsed_topics = []  # 存储浏览的帖子
        total_count = 0

        while total_count < max_browse_count:
            time.sleep(5)  # 确保页面加载完成
            topics = self.page.query_selector_all("#list-area .title")

            if not topics:
                print("未找到任何帖子，请检查选择器或页面加载情况。")
                break

            # 排除已经浏览过的帖子
            new_topics = [t for t in topics if t not in browsed_topics]
            browsed_topics.extend(new_topics)

            if not new_topics:
                print("没有加载出更多帖子。")
                break

            for topic in new_topics:
                if total_count >= max_browse_count:
                    break

                page = self.context.new_page()
                page.goto(HOME_URL + topic.get_attribute("href"))
                time.sleep(3)
                
                if random.random() < 0.02:  # 保持 2% 点赞几率
                    self.click_like(page)

                total_count += 1
                time.sleep(3)
                page.close()

            print(f"已浏览 {total_count} 个帖子")

            # 滚动以加载更多内容
            self.scroll_down()

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
