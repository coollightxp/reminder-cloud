import sqlite3
import smtplib
import os
import requests
import pytz                     # ✅ 新增：时区库
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText

# ===============================
# ✅ 强制使用北京时间
# ===============================
BEIJING_TZ = pytz.timezone("Asia/Shanghai")
NOW_DT = datetime.now(BEIJING_TZ)
TODAY = NOW_DT.date()
NOW_TIME = NOW_DT.strftime("%H:%M")

DB_PATH = "db/reminder.db"

EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
print("=== DEBUG START ===")
print(f"NOW_TIME = {NOW_TIME}")
print(f"TODAY = {TODAY}")

# ===============================
# 邮件
# ===============================
def send_mail(to_addr, member, title, content):
    if not title or not to_addr:
        return

    body = f"""
成员：{member}
事项：{title}

{content}

发送时间：{TODAY} {NOW_TIME}
""".strip()

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"🔔 提醒 - {TODAY}"
    msg["From"] = EMAIL_USER
    msg["To"] = to_addr

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, to_addr, msg.as_string())
    server.quit()
    print(f"✅ 已发送 -> {to_addr}")


# ===============================
# 节假日 API（仅 daily）
# ===============================
def is_workday(d):
    try:
        return not requests.get(
            f"https://timor.tech/api/holiday/info/{d}",
            timeout=5
        ).json()["holiday"]["holiday"]
    except:
        return True


# ===============================
# 获取实际发送日期（基于基准日）
# ===============================
def get_send_date(row):
    target = date.fromisoformat(row["remind_date"])

    if row["remind_type"] == "advance":
        target -= timedelta(days=row["advance_days"])

    return target


# ===============================
# 周期判断
# ===============================
def should_execute_periodic(row):
    today = TODAY

    if row["repeat_rule"] == "daily":
        return True

    if row["repeat_rule"].startswith("weekly:"):
        days = list(map(int, row["repeat_rule"].split(":")[1].split(",")))
        for i in range(7):
            d = today - timedelta(days=i)
            if d.weekday() in days:
                return True

    if row["repeat_rule"].startswith("monthly:"):
        import calendar
        target = int(row["repeat_rule"].split(":")[1])
        max_day = calendar.monthrange(today.year, today.month)[1]
        return today.day == min(target, max_day)

    if row["repeat_rule"].startswith("yearly:"):
        md = row["repeat_rule"].split(":")[1]
        return today.strftime("%m-%d") == md

    return False


# ===============================
# 主逻辑（防漏发）
# ===============================
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM reminders")
    rows = cur.fetchall()

    for row in rows:
        should = False

        # ---- 一次性 ----
        if row["repeat_rule"] is None:
            should = get_send_date(row) == TODAY

        # ---- 周期 ----
        else:
            should = should_execute_periodic(row)
            if should and row["repeat_rule"] == "daily":
                if row["skip_holiday"] == 1:
                    should = is_workday(TODAY)

        # ✅ 核心：只要过了时间且今天没发过，就发
        if (
            should
            and row["send_time"] <= NOW_TIME
            and row["last_done"] != TODAY.isoformat()
        ):
            send_mail(
                row["to_email"],
                row["member_name"],
                row["title"],
                row["content"]
            )

            if row["repeat_rule"] is None:
                cur.execute(
                    "UPDATE reminders SET is_sent=1 WHERE id=?",
                    (row["id"],)
                )
            else:
                cur.execute(
                    "UPDATE reminders SET last_done=? WHERE id=?",
                    (TODAY.isoformat(), row["id"])
                )

    conn.commit()
    conn.close()
    print("🎉 执行完成")


if __name__ == "__main__":
    main()
