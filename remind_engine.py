import sqlite3
import smtplib
import os
from datetime import date, timedelta
from email.mime.text import MIMEText

# ========== 基础配置 ==========
DB_PATH = "db/reminder.db"
TODAY = date.today().isoformat()

EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]


# ========== 邮件发送 ==========
def send_mail(body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"🔔 提醒 {TODAY}"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
    server.quit()


# ========== 工作日判断 ==========
def is_workday(d):
    try:
        import requests
        resp = requests.get(
            f"https://timor.tech/api/holiday/info/{d}",
            timeout=5
        )
        return not resp.json()["holiday"]["holiday"]
    except:
        return False


# ========== 计算下次执行日期 ==========
def next_exec_date(last_done, days, skip):
    d = date.fromisoformat(last_done)
    while True:
        d += timedelta(days=days)
        if not skip or is_workday(d.isoformat()):
            return d
        while not is_workday(d.isoformat()):
            d += timedelta(days=1)


# ========== 主逻辑 ==========
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ---- 一次性提醒 ----
    for r in cur.execute(
        "SELECT * FROM reminders WHERE remind_date=? AND is_sent=0",
        (TODAY,)
    ):
        # ✅ 兼容 content / title 两种字段名
        title = r["title"] if "title" in r.keys() else r["content"]
        send_mail(f"{r['member_name']}，{title}")
        cur.execute(
            "UPDATE reminders SET is_sent=1 WHERE id=?",
            (r["id"],)
        )

    # ---- 周期提醒 ----
    for r in cur.execute("SELECT * FROM periodic_tasks"):
        should = False

        if r["last_done"] is None:
            should = True
        else:
            nd = next_exec_date(
                r["last_done"],
                r["interval_days"],
                bool(r["skip_weekend_holiday"])
            )
            should = nd.isoformat() == TODAY

        if should:
            title = r["title"] if "title" in r.keys() else r["content"]
            send_mail(f"{r['member_name']}，{title}")
            cur.execute(
                "UPDATE periodic_tasks SET last_done=? WHERE id=?",
                (TODAY, r["id"])
            )

    conn.commit()
    conn.close()


# ========== 入口 ==========
if __name__ == "__main__":
    main()
