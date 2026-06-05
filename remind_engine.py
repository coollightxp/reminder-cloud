import sqlite3
import smtplib
import os
import requests
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText

DB_PATH = "db/reminder.db"
TODAY = date.today()
NOW_TIME = datetime.now().strftime("%H:%M")

EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]


# ===============================
# 邮件
# ===============================
def send_mail(to_addr, member, title):
    if not title or not to_addr:
        return

    body = f"Member: {member}\nTitle: {title}\nDate: {TODAY}"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"🔔 Reminder - {TODAY}"
    msg["From"] = EMAIL_USER
    msg["To"] = to_addr

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, to_addr, msg.as_string())
    server.quit()
    print(f"✅ Sent -> {to_addr}")


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
# 实际应发送日期
# ===============================
def get_send_date(row):
    if row["repeat_rule"] is None:
        target = date.fromisoformat(row["remind_date"])
    else:
        target = TODAY

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
        days = map(int, row["repeat_rule"].split(":")[1].split(","))
        return today.weekday() in days

    if row["repeat_rule"].startswith("monthly:"):
        import calendar
        target = int(row["repeat_rule"].split(":")[1])
        max_day = calendar.monthrange(today.year, today.month)[1]
        return today.day == min(target, max_day)

    if row["repeat_rule"].startswith("yearly:"):
        return today.strftime("%m-%d") == row["repeat_rule"].split(":")[1]

    return False


# ===============================
# 主逻辑（✅ 防漏发）
# ===============================
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM reminders WHERE is_sent=0 OR is_sent IS NULL")
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

        # ✅ 防漏发核心逻辑
        if (
            should
            and row["send_time"] <= NOW_TIME
            and row["last_done"] != TODAY.isoformat()
        ):
            send_mail(row["to_email"], row["member_name"], row["title"])

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
    print("🎉 Done")


if __name__ == "__main__":
    main()
