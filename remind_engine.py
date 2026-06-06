import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import pytz
from datetime import datetime, date, time
import json
import urllib.request

# ===============================
# 基础配置
# ===============================
DB_PATH = os.path.join(os.path.dirname(__file__), "db", "reminder.db")
BEIJING_TZ = pytz.timezone("Asia/Shanghai")
NOW_DT = datetime.now(BEIJING_TZ)
NOW_TIME = NOW_DT.time()
TODAY = date.today()

# ===============================
# 节假日 / 工作日判断
# ===============================
def is_workday(d):
    try:
        url = f"https://natescarlet.coding.net/p/holiday/d/holiday/git/raw/master/{d.year}/{d}.json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("code", 0) == 1  # 1表示工作日
    except Exception as e:
        print(f"⚠️ 节假日接口请求失败，默认按工作日处理: {e}")
        return True

# ===============================
# 核心逻辑
# ===============================

def get_send_date(row):
    """
    安全获取发送日期
    """
    # ✅ 防御性编程：如果字典里没有这个 key，返回 1970-01-01，让它自然被过滤掉
    if "send_date" not in row:
        print(f"⚠️ 记录缺少 send_date 字段，跳过: {row}")
        return date(1970, 1, 1)

    send_date_str = row["send_date"]
    if not send_date_str:  # 如果是空字符串或 None
        return date(1970, 1, 1)

    try:
        # 尝试解析 "YYYY-MM-DD" 格式
        return datetime.strptime(send_date_str, "%Y-%m-%d").date()
    except ValueError:
        # 如果失败，可能是 "YYYY-MM-DD HH:MM:SS" 格式，尝试截取日期部分
        try:
            return datetime.strptime(send_date_str.split(" ")[0], "%Y-%m-%d").date()
        except Exception:
            print(f"⚠️ 日期格式无法解析: {send_date_str}，跳过")
            return date(1970, 1, 1)

def get_send_time(row):
    """
    安全获取发送时间
    """
    if "send_time" not in row:
        return time(23, 59, 59)  # 默认晚上11点59分

    send_time_str = row["send_time"]
    if not send_time_str:
        return time(23, 59, 59)

    try:
        # 优先尝试解析 "HH:MM:SS"
        return datetime.strptime(send_time_str, "%H:%M:%S").time()
    except ValueError:
        try:
            # 尝试解析 "HH:MM"
            return datetime.strptime(send_time_str, "%H:%M").time()
        except Exception:
            print(f"⚠️ 时间格式无法解析: {send_time_str}，使用默认时间")
            return time(23, 59, 59)

def should_execute_periodic(row):
    """
    判断是否应该执行周期性任务
    """
    repeat_rule = row.get("repeat_rule")
    if not repeat_rule:
        return False

    rule_type = repeat_rule.get("type")
    if rule_type == "weekly":
        # 每周几
        target_weekday = repeat_rule.get("day")  # 0-6
        today_weekday = TODAY.weekday()  # 0-6
        return target_weekday == today_weekday

    elif rule_type == "monthly":
        # 每月几号
        target_day = repeat_rule.get("day")  # 1-31
        today_day = TODAY.day
        return target_day == today_day

    elif rule_type == "yearly":
        # 每年几月几号
        target_month = repeat_rule.get("month")
        target_day = repeat_rule.get("day")
        today_month = TODAY.month
        today_day = TODAY.day
        return target_month == today_month and target_day == today_day

    return False

def send_email(to_email, subject, body):
    """
    发送邮件（这里需要根据你的 SMTP 配置修改）
    """
    # 示例配置，请替换成你自己的
    smtp_server = "smtp.example.com"
    smtp_port = 587
    smtp_user = "your_email@example.com"
    smtp_password = "your_password"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = smtp_user
    msg["To"] = to_email

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        print(f"✅ 邮件发送成功: {to_email}")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

def main():
    print(f"🚀 开始执行 - 当前时间: {NOW_DT.strftime('%Y-%m-%d %H:%M:%S')}")

    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 查询所有未发送的提醒
    cursor.execute("SELECT * FROM reminder WHERE is_sent = 0")
    rows = cursor.fetchall()

    print(f"📊 共读取到 {len(rows)} 条提醒记录")

    for row in rows:
        row_dict = dict(row)
        print(f"🔍 检查记录: {row_dict}")

        # 1. 判断是否是周期性任务
        if row_dict.get("repeat_rule"):
            if not should_execute_periodic(row_dict):
                print(f"⏭️ 周期性任务未到执行时间，跳过: {row_dict}")
                continue
            else:
                print(f"✅ 周期性任务执行日，继续处理: {row_dict}")
        else:
            # 2. 一次性任务，判断日期是否匹配
            send_date = get_send_date(row_dict)
            if send_date != TODAY:
                print(f"⏭️ 一次性任务日期不匹配，跳过: {send_date} != {TODAY}")
                continue
            else:
                print(f"✅ 一次性任务日期匹配，继续处理: {send_date}")

        # 3. 判断时间是否匹配（或已过）
        send_time = get_send_time(row_dict)
        if send_time > NOW_TIME:
            print(f"⏭️ 时间未到，跳过: {send_time} > {NOW_TIME}")
            continue
        else:
            print(f"✅ 时间已过（或正好），准备发送: {send_time}")

        # 4. 执行发送
        try:
            # 假设表里有 title, content, email 字段
            subject = row_dict.get("title", "提醒")
            body = row_dict.get("content", "您有一条新提醒")
            to_email = row_dict.get("email", "default@example.com")

            send_email(to_email, subject, body)

            # 标记为已发送
            cursor.execute("UPDATE reminder SET is_sent = 1 WHERE id = ?", (row_dict.get("id"),))
            conn.commit()
            print(f"✅ 记录 {row_dict.get('id')} 已标记为已发送")

        except Exception as e:
            print(f"❌ 处理记录 {row_dict.get('id')} 时出错: {e}")

    conn.close()
    print("🎉 执行结束")

if __name__ == "__main__":
    main()
