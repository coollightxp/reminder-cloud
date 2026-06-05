import sqlite3, requests, os, datetime
from datetime import timedelta

DB_PATH = "db/reminder.db"
WEBHOOK = os.environ["WECHAT_WEBHOOK"]
TODAY = datetime.date.today().isoformat()

def is_workday(date_str):
    url = f"https://timor.tech/api/holiday/info/{date_str}"
    try:
        r = requests.get(url, timeout=5)
        return not r.json()["holiday"]["holiday"]
    except:
        return False

def next_execution_date(last_done, interval_days, skip):
    d = datetime.datetime.strptime(last_done, "%Y-%m-%d").date()
    while True:
        d += timedelta(days=interval_days)
        if not skip or is_workday(d.isoformat()):
            return d
        while not is_workday(d.isoformat()):
            d += timedelta(days=1)

def send(msg, at_all=False):
    payload = {"msgtype": "text", "text": {"content": msg}}
    if at_all:
        payload["text"]["mentioned_list"] = ["@all"]
    requests.post(WEBHOOK, json=payload)

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for title, at_name in cur.execute("""
    SELECT r.title, m.at_name
    FROM reminders r
    JOIN wechat_members m ON r.member_id = m.id
    WHERE r.remind_date=? AND r.is_sent=0
    """, (TODAY,)):
        msg = f"{at_name} {title}" if at_name != "@all" else title
        send(msg, at_all=(at_name == "@all"))
        cur.execute(
            "UPDATE reminders SET is_sent=1 WHERE title=? AND remind_date=?",
            (title, TODAY)
        )

    for title, days, last_done, mid, at_name, skip in cur.execute("""
    SELECT r.title, r.interval_days, r.last_done,
           r.member_id, m.at_name, r.skip_weekend_holiday
    FROM periodic_tasks r
    JOIN wechat_members m ON r.member_id = m.id
    """):
        if last_done is None:
            exec_date = TODAY
        else:
            exec_date = next_execution_date(last_done, days, skip)

        if exec_date == TODAY:
            msg = f"{at_name} {title}" if at_name != "@all" else title
            send(msg, at_all=(at_name == "@all"))
            cur.execute(
                "UPDATE periodic_tasks SET last_done=? WHERE id=?",
                (TODAY, mid)
            )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
