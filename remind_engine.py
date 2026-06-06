import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import pytz
from datetime import datetime, date, time  # ✅ 确保 time 被引入
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
            return data.get("code", 0) == 0
    except Exception as e:
        print(f"⚠️ 获取节假日接口失败: {e}")
        return True

# ===============================
# 周期判断（按天锁定）
# ===============================
def should_execute_periodic(row):
    weekday = TODAY.weekday()

    if row["repeat_rule"] == "daily":
        return True

    if row["repeat_rule"].startswith("weekly:"):
        try:
            days = list(map(int, row["repeat_rule"].split(":")[1].split(",")))
            return weekday in days
        except:
            return False

    if row["repeat_rule"].startswith("monthly:"):
        import calendar
        try:
            target = int(row["repeat_rule"].split(":")[1])
            max_day = calendar.monthrange(TODAY.year, TODAY.month)[1]
            return TODAY.day == min(target, max_day)
        except:
            return False

    if row["repeat_rule"].startswith("yearly:"):
        try:
            md = row["repeat_rule"].split(":")[1]
            return TODAY.strftime("%m-%d") == md
        except:
            return False

    return False

# ===============================
# 邮件发送
# ===============================
def send_mail(to_addr, member_name, subject, content):
    user = os.environ["EMAIL_USER"]
    pwd = os.environ["EMAIL_PASS"]

    msg = MIMEText(content, "plain", "utf-8")
    msg["From"] = user
    msg["To"] = to_addr
    msg["Subject"] = Header(subject, "utf-8")

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(user, pwd)
        server.sendmail(user, [to_addr], msg.as_string())
        server.quit()
        print(f"✅ 邮件发送成功 -> {to_addr}")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

# ===============================
# 获取目标日期
# ===============================
def get_send_date(row):
    if row["remind_date"]:
        return date.fromisoformat(row["remind_date"])
    return TODAY

# ===============================
# 主逻辑（修复时间比较错误）
# ===============================
def main():
    print(f"🚀 开始执行 - 当前时间: {NOW_DT}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM reminders")
    rows = cur.fetchall()

    for row in rows:
        can_send_today = False

        # ---- 1. 日期/周期锁定 ----
        if row["repeat_rule"] is None:
            if get_send_date(row) == TODAY:
                can_send_today = True
        else:
            if should_execute_periodic(row):
                can_send_today = True
            if row["repeat_rule"] == "daily" and row["skip_holiday"] == 1:
                if not is_workday(TODAY):
                    can_send_today = False

        # ---- 2. 时间宽容 + 防重发 ----
        if can_send_today:
            # ✅ 关键修复：把字符串转成 time 对象再比较
            send_time_obj = datetime.strptime(row["send_time"], "%H:%M:%S").time()

            if (
                send_time_obj <= NOW_TIME
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
