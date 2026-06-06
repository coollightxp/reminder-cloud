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
# 节假日判断
# ===============================
def is_workday(d):
    try:
        url = f"https://natescarlet.coding.net/p/holiday/d/holiday/git/raw/master/{d.year}/{d}.json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("code", 0) == 0
    except Exception as e:
        print(f"⚠️ 节假日接口失败: {e}")
        return True

# ===============================
# 时间解析（兼容 HH:MM / HH:MM:SS）
# ===============================
def parse_time(t):
    t = str(t).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(t, fmt).time()
        except ValueError:
            continue
    return None

# ===============================
# 周期判断（你之前的逻辑）
# ===============================
def should_execute_periodic(row):
    wd = TODAY.weekday()

    if row["repeat_rule"] == "daily":
        return True

    if row["repeat_rule"].startswith("weekly:"):
        days = list(map(int, row["repeat_rule"].split(":")[1].split(",")))
        return wd in days

    if row["repeat_rule"].startswith("monthly:"):
        import calendar
        target = int(row["repeat_rule"].split(":")[1])
        max_day = calendar.monthrange(TODAY.year, TODAY.month)[1]
        return TODAY.day == min(target, max_day)

    if row["repeat_rule"].startswith("yearly:"):
        md = row["repeat_rule"].split(":")[1]
        return TODAY.strftime("%m-%d") == md

    return False

# ===============================
# 发送邮件
# ===============================
def send_mail(to_email, member_name, title, content):
    user = os.environ["EMAIL_USER"]
    pwd = os.environ["EMAIL_PASS"]

    msg = MIMEText(content, "plain", "utf-8")
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = Header(title, "utf-8")

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(user, pwd)
        server.sendmail(user, [to_email], msg.as_string())
        server.quit()
        print(f"✅ 邮件发送成功 -> {to_email}")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

# ===============================
# 主逻辑（✅ 使用 reminders 表）
# ===============================
def main():
    print(f"🚀 开始执行 - 当前时间: {NOW_DT}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ✅ 关键：表名是 reminders
    cur.execute("SELECT * FROM reminders")
    rows = cur.fetchall()

    for row in rows:
        can_send_today = False

        # ---- 一次性 ----
        if row["repeat_rule"] is None:
            if row["remind_date"] == TODAY.isoformat():
                can_send_today = True

        # ---- 周期性 ----
        else:
            if should_execute_periodic(row):
                can_send_today = True
            if row["repeat_rule"] == "daily" and row["skip_holiday"] == 1:
                if not is_workday(TODAY):
                    can_send_today = False

        # ---- 时间宽容 + 防重发 ----
        if can_send_today:
            send_time_obj = parse_time(row["send_time"])
            if (
                send_time_obj
                and send_time_obj <= NOW_TIME
                and row["last_done"] != TODAY.isoformat()
            ):
                send_mail(
                    row["to_email"],
                    row["member_name"],
                    row["title"],
                    row["content"]
                )

                if row["repeat_rule"] is None:
                    cur.execute("UPDATE reminders SET is_sent=1 WHERE id=?", (row["id"],))
                else:
                    cur.execute("UPDATE reminders SET last_done=? WHERE id=?", (TODAY.isoformat(), row["id"]))

    conn.commit()
    conn.close()
    print("🎉 执行完成")

if __name__ == "__main__":
    main()
