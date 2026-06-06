import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import pytz
from datetime import datetime, date, time
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
            return data.get("code", 0) == 1  # 1 表示工作日
    except Exception as e:
        print(f"⚠️ 节假日接口异常，默认按工作日处理: {e}")
        return True  # 异常时默认放行

# ===============================
# 工具函数：安全转换时间字符串为 time 对象
# ===============================
def parse_time_str(time_str):
    """
    兼容多种时间格式：
    - "11:30:00" -> %H:%M:%S
    - "11:30"     -> %H:%M
    """
    if not time_str:
        return None
    time_str = str(time_str).strip()
    formats = ["%H:%M:%S", "%H:%M"]
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    print(f"❌ 无法解析的时间格式: {time_str}")
    return None

# ===============================
# 主逻辑
# ===============================
def main():
    print(f"🚀 开始执行 - 当前时间: {NOW_DT.strftime('%Y-%m-%d %H:%M:%S')}")

    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM reminders")
    rows = cur.fetchall()
    print(f"📊 共读取到 {len(rows)} 条提醒记录")

    for row in rows:
        # 初始化标记
        should_send = False
        reason = ""

        # ===============================
        # 第一层：判断今天是否该发？
        # ===============================
        if row["repeat_rule"] is None:
            # 一次性：日期必须是今天
            if get_send_date(row) == TODAY:
                should_send = True
                reason = "一次性任务，今天是发送日"
            else:
                continue  # 不是今天，跳过

        else:
            # 周期性任务：判断是否今天符合
            if should_execute_periodic(row):
                should_send = True
                reason = "周期性任务，今天是执行日"
            else:
                continue  # 不是今天，跳过

        # ===============================
        # 第二层：判断时间是否过了？（宽容点）
        # ===============================
        send_time_str = row["send_time"]
        send_time_obj = parse_time_str(send_time_str)
        if not send_time_obj:
            print(f"⚠️ 跳过记录 ID {row['id']}：时间格式无效")
            continue

        if send_time_obj <= NOW_TIME:
            reason += "，且当前时间已过发送时间"
            should_send = True
        else:
            reason += "，但当前时间未到发送时间"
            should_send = False  # 时间没到，不发

        # ===============================
        # 第三层：判断是否已发送过？
        # ===============================
        if row["last_sent_date"] == str(TODAY):
            print(f"⏭️ 跳过记录 ID {row['id']}：今天已发送过")
            continue

        # ===============================
        # 第四层：节假日判断（仅对每日任务）
        # ===============================
        if row["repeat_rule"] == "daily":
            if not is_workday(TODAY):
                print(f"📅 跳过记录 ID {row['id']}：今天是节假日/周末")
                continue

        # ===============================
        # 最终发送
        # ===============================
        if should_send:
            print(f"✅ 准备发送提醒 ID {row['id']}：{reason}")
            # 这里写你的发送逻辑（邮件/钉钉/企业微信等）
            # send_notification(row)
            # 示例：打印内容
            print(f"📧 发送内容：{row['content']}")
            print(f"📅 发送时间：{send_time_obj.strftime('%H:%M:%S')}")

            # 更新 last_sent_date
            cur.execute(
                "UPDATE reminders SET last_sent_date = ? WHERE id = ?",
                (str(TODAY), row["id"])
            )
            conn.commit()
        else:
            print(f"⏳ 记录 ID {row['id']} 暂不发送：{reason}")

    conn.close()
    print("✅ 执行完毕")

# ===============================
# 辅助函数：获取一次性任务的发送日期
# ===============================
def get_send_date(row):
    if row["repeat_rule"] is None:
        return datetime.strptime(row["send_date"], "%Y-%m-%d").date()
    return None

# ===============================
# 辅助函数：判断周期性任务今天是否执行
# ===============================
def should_execute_periodic(row):
    rule = row["repeat_rule"]
    if rule == "daily":
        return True
    elif rule == "weekly":
        # 每周几：0=周一，6=周日（Python 标准）
        # 数据库存的是 1=周一，7=周日，需要转换
        weekday = TODAY.weekday()  # 0-6
        db_weekday = int(row["repeat_value"])  # 1-7
        return weekday == db_weekday - 1
    elif rule == "monthly":
        # 每月几号
        day = TODAY.day
        db_day = int(row["repeat_value"])
        return day == db_day
    elif rule == "yearly":
        # 每年几月几号
        today_str = TODAY.strftime("%m-%d")
        db_str = row["repeat_value"]  # 格式应为 "MM-DD"
        return today_str == db_str
    return False

# ===============================
# 入口
# ===============================
if __name__ == "__main__":
    main()
