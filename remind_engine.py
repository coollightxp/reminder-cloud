import sqlite3
import requests
import os
import time
import hashlib
from datetime import timedelta

DB_PATH = "db/reminder.db"

BOT_ID = os.environ["WX_BOT_ID"]
BOT_SECRET = os.environ["WX_BOT_SECRET"]

TODAY = time.strftime("%Y-%m-%d")

# ---------------------------
# 企业微信群机器人签名
# ---------------------------
def get_sign():
    timestamp = str(int(time.time()))
    signature = hashlib.sha256((BOT_SECRET + timestamp).encode()).hexdigest()
    return timestamp, signature


def send_text(content, mentioned=None):
    """
    发送文本消息
    :param content: 消息内容
    :param mentioned: ['@张三'] 或 ['@all']
    """
    timestamp, signature = get_sign()

    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    params = {
        "key": BOT_ID,
        "timestamp": timestamp,
        "signature": signature
    }

    payload = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }

    if mentioned:
        payload["text"]["mentioned_list"] = mentioned

    r = requests.post(url, params=params, json=payload)

    if r.json().get("errcode") != 0:
        raise RuntimeError(f"企业微信发送失败: {r.text}")


# ---------------------------
# 节假日判断（timor.tech）
# ---------------------------
def is_workday(date_str):
    try:
        r = requests.get(
            f"https://timor.tech/api/holiday/info/{date_str}",
            timeout=5
        )
        return not r.json()["holiday"]["holiday"]
    except Exception:
        return False


def next_exec_date(last_done, interval_days, skip):
    d = last_done
    while True:
        d += timedelta(days=interval_days)
        if not skip or is_workday(d.isoformat()):
            return d
        while not is_workday(d.isoformat()):
            d += timedelta(days=1)


# ---------------------------
# 主逻辑
# ---------------------------
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 一次性提醒
    for title, at_name in cur.execute("""
        SELECT r.title, m.at_name
        FROM reminders r
        JOIN wechat_members m ON r.member_id = m.id
        WHERE r.remind_date = ? AND r.is_sent = 0
    """, (TODAY,)):
        mentioned = ["@all"] if at_name == "@all" else [at_name.lstrip("@")]
        send_text(f"{title}", mentioned=mentioned)

        cur.execute(
            "UPDATE reminders SET is_sent = 1 WHERE title = ? AND remind_date = ?",
            (title, TODAY)
        )

    # 周期提醒
    for title, days, last_done, mid, at_name, skip in cur.execute("""
        SELECT r.title, r.interval_days, r.last_done,
               r.member_id, m.at_name, r.skip_weekend_holiday
        FROM periodic_tasks r
        JOIN wechat_members m ON r.member_id = m.id
    """):
        if last_done is None:
            exec_date = TODAY
        else:
            exec_date = next_exec_date(
                last_done=datetime.datetime.strptime(last_done, "%Y-%m-%d").date(),
                interval_days=days,
                skip=bool(skip)
            )

        if exec_date.isoformat() == TODAY:
            mentioned = ["@all"] if at_name == "@all" else [at_name.lstrip("@")]
            send_text(f"{title}", mentioned=mentioned)

            cur.execute(
                "UPDATE periodic_tasks SET last_done = ? WHERE id = ?",
                (TODAY, mid)
            )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
