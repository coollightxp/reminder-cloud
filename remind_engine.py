import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import pytz
from datetime import datetime, date, time, timedelta
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
        url = f"https://natescarlet.coding.net/p/holiday/d/holiday/git/raw/master/{d.year}/calendar.json"
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            return data[str(d.month)][str(d.day)] == 0
    except Exception:
        return True  # 网络异常默认按工作日处理

# ===============================
# 数据库连接
# ===============================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 这里设置了 Row 模式，所以后面要用 row["key"]
    return conn

# ===============================
# 核心逻辑
# ===============================
def main():
    conn = get_conn()
    cursor = conn.cursor()

    # 查询所有未发送的提醒
    cursor.execute("SELECT * FROM reminders WHERE is_sent = 0")
    rows = cursor.fetchall()

    for row in rows:
        can_send_today = False
        task_type = "未知"

        # ---- 1. 一次性任务（支持提前 N 天） ----
        if row["repeat_rule"] is None:
            task_type = "一次性"
            target_date = datetime.strptime(row["remind_date"], "%Y-%m-%d").date()
            send_on_date = target_date

            # ✅ 修复点：这里原来用 row.get，现在改为用 row[] 并安全转换
            advance_days = int(row["advance_days"]) if row["advance_days"] is not None else 0
            if advance_days and advance_days > 0:
                send_on_date = target_date - timedelta(days=advance_days)

            if send_on_date == TODAY:
                can_send_today = True

        # ---- 2. 周期性任务 ----
        elif row["repeat_rule"] is not None:
            task_type = "周期性"
            if should_execute_periodic(row):
                can_send_today = True

        # ---- 3. 每日任务（跳过节假日） ----
        elif row["repeat_rule"] == "daily":
            task_type = "每日"
            if row["skip_holiday"] and not is_workday(TODAY):
                continue  # 跳过节假日
            can_send_today = True

        # ---- 执行发送 ----
        if can_send_today:
            send_time = datetime.strptime(row["send_time"], "%H:%M").time()
            if NOW_TIME >= send_time:
                # 发送邮件逻辑（这里省略了，你原来的代码应该有）
                print(f"[{task_type}] 发送提醒: {row['content']}")
                # 标记为已发送
                cursor.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (row["id"],))
                conn.commit()
            else:
                print(f"[{task_type}] 时间未到，跳过: {row['content']}")
        else:
            print(f"[{task_type}] 今日不发送: {row['content']}")

    conn.close()

# ===============================
# 周期性任务判断（保持你原来的逻辑）
# ===============================
def should_execute_periodic(row):
    # 这里是你原来的周期性判断逻辑，保持不变
    # 示例：每周一、每月1号等
    rule = row["repeat_rule"]
    last_done = row["last_done"]

    if rule == "weekly:monday":
        return TODAY.weekday() == 0  # 0 是周一
    elif rule == "weekly:friday":
        return TODAY.weekday() == 4  # 4 是周五
    elif rule == "monthly:1":
        return TODAY.day == 1
    # ... 其他规则

    return False

if __name__ == "__main__":
    main()
