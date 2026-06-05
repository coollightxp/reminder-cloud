import sqlite3
import requests
import os
import time
from datetime import date, timedelta

# ================= 配置区 =================
DB_PATH = "db/reminder.db"

CORP_ID = os.environ["WX_CORP_ID"]
AGENT_ID = int(os.environ["WX_AGENT_ID"])
SECRET = os.environ["WX_CORP_SECRET"]

TODAY = date.today().isoformat()

# Token 缓存（防止频繁请求）
_TOKEN_CACHE = {"token": None, "expire": 0}
# ==========================================


def get_access_token():
    """获取企业微信 Access Token（自动缓存）"""
    if _TOKEN_CACHE["token"] and time.time() < _TOKEN_CACHE["expire"]:
        return _TOKEN_CACHE["token"]

    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    params = {"corpid": CORP_ID, "corpsecret": SECRET}

    try:
        resp = requests.get(url, params=params, timeout=10).json()
        if resp.get("errcode") != 0:
            raise RuntimeError(f"获取 Token 失败: {resp}")

        _TOKEN_CACHE["token"] = resp["access_token"]
        # 提前 5 分钟过期，防止临界值失效
        _TOKEN_CACHE["expire"] = time.time() + resp["expires_in"] - 300
        return _TOKEN_CACHE["token"]
    except Exception as e:
        raise RuntimeError(f"请求 Token 接口异常: {e}")


def send_message(content, touser="@all"):
    """发送文本消息到企业微信"""
    token = get_access_token()
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

    payload = {
        "touser": touser,
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {"content": content},
        "safe": 0
    }

    r = requests.post(url, json=payload, timeout=10).json()
    if r.get("errcode") != 0:
        raise RuntimeError(f"发送消息失败: {r}")


# ----------------- 辅助函数 -----------------
def is_workday(d):
    """判断是否为工作日（调用 timor.tech API）"""
    try:
        r = requests.get(f"https://timor.tech/api/holiday/info/{d}", timeout=5)
        return not r.json()["holiday"]["holiday"]
    except:
        return False


def next_exec_date(last_done, days, skip):
    """计算周期任务的下一个执行日期"""
    d = date.fromisoformat(last_done)
    while True:
        d += timedelta(days=days)
        if not skip or is_workday(d.isoformat()):
            return d
        # 如果跳过节假日，且当天是假期，则继续往后推
        while not is_workday(d.isoformat()):
            d += timedelta(days=1)


# ----------------- 主逻辑 -----------------
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 处理一次性提醒
    for row in cur.execute("""
        SELECT r.title, m.at_name, COALESCE(m.open_userid, '@all') AS uid
        FROM reminders r
        JOIN wechat_members m ON r.member_id = m.id
        WHERE r.remind_date = ? AND r.is_sent = 0
    """, (TODAY,)):
        send_message(f"{row['at_name']} {row['title']}", row['uid'])
        cur.execute(
            "UPDATE reminders SET is_sent = 1 WHERE id = ?",
            (row["id"],)
        )

    # 2. 处理周期提醒
    for row in cur.execute("""
        SELECT r.id, r.title, r.interval_days, r.last_done,
               m.at_name, r.skip_weekend_holiday,
               COALESCE(m.open_userid, '@all') AS uid
        FROM periodic_tasks r
        JOIN wechat_members m ON r.member_id = m.id
    """):
        should_run = False
        if row["last_done"] is None:
            should_run = True
        else:
            next_day = next_exec_date(row["last_done"], row["interval_days"], row["skip_weekend_holiday"])
            if next_day.isoformat() == TODAY:
                should_run = True

        if should_run:
            send_message(f"{row['at_name']} {row['title']}", row['uid'])
            cur.execute(
                "UPDATE periodic_tasks SET last_done = ? WHERE id = ?",
                (TODAY, row["id"])
            )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
