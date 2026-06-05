import sqlite3
import smtplib
import os
from datetime import date, timedelta
from email.mime.text import MIMEText

DB_PATH = "db/reminder.db"
TODAY = date.today().isoformat()

EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]


def send_mail(body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"🔔 提醒 {TODAY}"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
    server.quit()


def is_workday(d):
    try:
        import requests
        return not requests.get(
            f"https://timor.tech/api/holiday/info/{d}", timeout=5
        ).json()["holiday"]["holiday"]
    except:
        return False


def next_exec_date(last_done, days, skip):
    d = date.fromisoformat(last_done)
    while True:
        d += timedelta(days=days)
        if not skip or is_workday(d.isoformat()):
            return d
        while not is_workday(d.isoformat()):
            d += timedelta(days=1)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 一次性提醒
    for r in cur.execute(
        "SELECT * FROM reminders WHERE remind_date=? AND is_sent=0", (TODAY,)
    ):
        send_mail(f"{r['member_name']}，{r['title']}")
        cur.execute("UPDATE reminders SET is_sent=1 WHERE id=?", (r["id"],))

    # 周期提醒
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
            send_mail(f"{r['member_name']}，{r['title']}")
            cur.execute(
                "UPDATE periodic_tasks SET last_done=? WHERE id=?",
                (TODAY, r["id"])
            )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
