import sqlite3
import smtplib
import os
from datetime import date, timedelta
from email.mime.text import MIMEText

DB_PATH = "db/reminder.db"
TODAY = date.today().isoformat()

EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]


# ================= 邮件发送 =================
def send_mail(to_addr, member, title):
    if not title or not to_addr:
        print("⚠️ 跳过：标题或邮箱为空")
        return

    body = f"成员：{member}\n事项：{title}\n日期：{TODAY}"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"🔔 提醒 - {TODAY}"
    msg["From"] = EMAIL_USER
    msg["To"] = to_addr

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_addr, msg.as_string())
        server.quit()
        print(f"✅ 已发送 -> {to_addr} ({member})")
    except Exception as e:
        print(f"❌ 发送失败 {to_addr}: {e}")


# ================= 工作日判断 =================
def is_workday(d):
    try:
        import requests
        return not requests.get(
            f"https://timor.tech/api/holiday/info/{d}", timeout=5
        ).json()["holiday"]["holiday"]
    except:
        return False


# ================= 计算下次执行日期 =================
def next_exec_date(last_done, days, skip):
    d = date.fromisoformat(last_done)
    while True:
        d += timedelta(days=days)
        if not skip or is_workday(d.isoformat()):
            return d
        while not is_workday(d.isoformat()):
            d += timedelta(days=1)


# ================= 主逻辑 =================
def main():
    print(f"🚀 开始运行提醒脚本，当前日期: {TODAY}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ---- 一次性提醒 ----
    cur.execute(
        """
        SELECT title, member_name, to_email
        FROM reminders
        WHERE remind_date=? AND is_sent=0
        """,
        (TODAY,)
    )

    for row in cur.fetchall():
        send_mail(row["to_email"], row["member_name"], row["title"])

        # ✅ 不用 id，用 title + member_name 标记已发送
        cur.execute(
            """
            UPDATE reminders
            SET is_sent=1
            WHERE title=? AND member_name=? AND remind_date=?
            """,
            (row["title"], row["member_name"], TODAY)
        )

    # ---- 周期提醒 ----
    cur.execute(
        """
        SELECT title, member_name, to_email, interval_days, last_done, skip_weekend_holiday
        FROM periodic_tasks
        """
    )

    for row in cur.fetchall():
        should = False

        if row["last_done"] is None:
            should = True
        else:
            nd = next_exec_date(
                row["last_done"],
                row["interval_days"],
                bool(row["skip_weekend_holiday"])
            )
            should = nd.isoformat() == TODAY

        if should:
            send_mail(row["to_email"], row["member_name"], row["title"])
            cur.execute(
                """
                UPDATE periodic_tasks
                SET last_done=?
                WHERE title=? AND member_name=?
                """,
                (TODAY, row["title"], row["member_name"])
            )

    conn.commit()
    conn.close()
    print("🎉 执行完成")


if __name__ == "__main__":
    main()
