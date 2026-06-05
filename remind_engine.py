import sqlite3
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText

# ================= 配置区 =================
# 数据库路径（GitHub Actions 里通常是仓库根目录，不用改）
DB_PATH = "db/reminder.db" 
TODAY = date.today().isoformat()

# 从 GitHub Secrets 读取邮箱配置
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]

# ================= 核心函数 =================

def send_mail(member, title):
    """
    发送邮件
    :param member: 收件人/成员名 (str)
    :param title: 提醒标题 (str)
    """
    if not title:
        print("⚠️ 跳过：标题为空")
        return

    # 构建邮件内容
    subject = f"🔔 提醒 - {TODAY}"
    body = f"成员：{member}\n事项：{title}\n日期：{TODAY}"
    
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER  # 发给自己的 QQ 邮箱

    try:
        # 连接 QQ 邮箱 SMTP
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        server.quit()
        print(f"✅ 邮件发送成功: {member} - {title}")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

def main():
    print(f"🚀 开始运行提醒脚本，当前日期: {TODAY}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. 查询今天需要提醒的一次性任务
        # 根据你截图里的表结构：title, member_name, remind_date, is_sent
        query = """
            SELECT title, member_name 
            FROM reminders 
            WHERE remind_date = ? AND is_sent = 0
        """
        cursor.execute(query, (TODAY,))
        results = cursor.fetchall()

        if not results:
            print("ℹ️ 今天没有需要提醒的任务。")
        else:
            print(f"📧 找到 {len(results)} 个任务，准备发送...")
            for row in results:
                # 解包数据：row[0] 是 title, row[1] 是 member_name
                send_mail(member=row[1], title=row[0])
                
                # 标记为已发送 (可选，建议加上)
                update_sql = "UPDATE reminders SET is_sent = 1 WHERE title = ? AND member_name = ?"
                cursor.execute(update_sql, (row[0], row[1]))
        
        conn.commit() # 提交更改
        conn.close()
        
    except Exception as e:
        print(f"🔥 发生严重错误: {e}")

if __name__ == "__main__":
    main()
