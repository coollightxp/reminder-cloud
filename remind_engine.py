import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import pytz
from datetime import datetime, date, time, timedelta
import json
import urllib.request
import calendar

# ===============================
# 基础配置
# ===============================
DB_PATH = os.path.join(os.path.dirname(__file__), "db", "reminder.db")
BEIJING_TZ = pytz.timezone("Asia/Shanghai")
NOW_DT = datetime.now(BEIJING_TZ)
NOW_TIME = NOW_DT.time()
TODAY = date.today()

print(f"\n🚀 脚本启动 - 当前时间: {NOW_DT.strftime('%Y-%m-%d %H:%M:%S')}\n")

# ===============================
# 节假日 / 工作日判断
# ===============================
def is_workday(d):
    try:
        url = f"https://natescarlet.coding.net/p/holiday/d/holiday/git/raw/master/{d.year}/{d}.json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("code", 0) == 0
    except Exception as e:
        print(f"⚠️ 节假日接口失败: {e}")
        return True

# ===============================
# 时间解析（兼容 HH:MM / HH:MM:SS）
# ===============================
def parse_time(t):
    t = str(t).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(t, fmt).time()
        except ValueError:
            continue
    return None

# ===============================
# 周期判断（✅ 支持提前 N 天）
# ===============================
def should_execute_periodic(row):
    """
    判断今天是否符合周期规则
    返回: (是否匹配, 原定日期)
    """
    wd = TODAY.weekday()
    rule = row["repeat_rule"]
    target_date = TODAY

    if rule == "daily":
        return True, TODAY

    if rule.startswith("weekly:"):
        days = list(map(int, rule.split(":")[1].split(",")))
        return wd in days, TODAY

    if rule.startswith("monthly:"):
        target_day = int(rule.split(":")[1])
        max_day = calendar.monthrange(TODAY.year, TODAY.month)[1]
        actual_target_day = min(target_day, max_day)
        target_date = date(TODAY.year, TODAY.month, actual_target_day)
        return TODAY.day == actual_target_day, target_date

    if rule.startswith("yearly:"):
        md = rule.split(":")[1]
        target_date = datetime.strptime(f"{TODAY.year}-{md}", "%Y-%m-%d").date()
        return TODAY.strftime("%m-%d") == md, target_date

    return False, None

# ===============================
# 邮件发送
# ===============================
def send_mail(to_email, member_name, title, content):
    user = os.environ["EMAIL_USER"]
    pwd = os.environ["EMAIL_PASS"]

    msg = MIMEText(content, "plain", "utf-8")
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = Header(title, "utf-8")

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(user, pwd)
        server.sendmail(user, [to_email], msg.as_string())
        server.quit()
        print(f"✅ 邮件发送成功 -> {to_email}")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

# ===============================
# 主逻辑
# ===============================
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM reminders")
    rows = cur.fetchall()

    print(f"📊 共加载 {len(rows)} 条提醒\n")

    for row in rows:
        print("==============================================")
        print(f"检查任务 ID: {row['id']} | 标题: {row['title']}")
        can_send_today = False

        # ---- 1. 一次性任务 ----
        if row["repeat_rule"] is None:
            print("\n🟢 [类型] 一次性任务")

            try:
                target_date = date.fromisoformat(row["remind_date"])
            except Exception as e:
                print(f"❌ remind_date 解析失败: {e}")
                continue

            advance_days = int(row["advance_days"]) if row["advance_days"] not in (None, "") else 0
            send_on_date = target_date - timedelta(days=advance_days)

            print(f"   原定日期: {target_date} | 提前: {advance_days}天")
            print(f"   ➜ 应发送日: {send_on_date} | 今天: {TODAY}")

            if send_on_date != TODAY:
                print("❌ 结论：日期不匹配，跳过")
                continue

            can_send_today = True

        # ---- 2. 周期性任务 ----
        else:
            print("\n🟢 [类型] 周期性任务")
            is_match, target_date = should_execute_periodic(row)

            if not is_match:
                print(f"❌ 结论：今天不符合周期规则 ({row['repeat_rule']})")
                continue

            print(f"✅ 结论：今天符合周期规则")

            advance_days = int(row["advance_days"]) if row["advance_days"] not in (None, "") else 0
            send_on_date = target_date - timedelta(days=advance_days)

            print(f"   原定日期: {target_date} | 提前: {advance_days}天")
            print(f"   ➜ 应发送日: {send_on_date} | 今天: {TODAY}")

            if send_on_date != TODAY:
                print("❌ 结论：不是提前提醒日，跳过")
                continue

            # 每日任务跳过节假日
            if row["repeat_rule"] == "daily" and row["skip_holiday"] == 1:
                if not is_workday(TODAY):
                    print("❌ 结论：节假日，跳过")
                    continue

            can_send_today = True

        # ---- 3. 时间宽容 + 防重发 ----
        if can_send_today:
            send_time_obj = parse_time(row["send_time"])
            print(f"   发送时间: {send_time_obj} | 当前时间: {NOW_TIME}")

            if not send_time_obj or send_time_obj > NOW_TIME:
                print("❌ 结论：时间未到，跳过")
                continue

            if row["last_done"] == TODAY.isoformat():
                print("❌ 结论：今天已发过，跳过")
                continue

            print("🚀 条件全部满足，准备发送！")
            send_mail(
                row["to_email"],
                row["member_name"],
                row["title"],
                row["content"]
            )

            if row["repeat_rule"] is None:
                cur.execute("UPDATE reminders SET is_sent=1 WHERE id=?", (row["id"],))
            else:
                cur.execute("UPDATE reminders SET last_done=? WHERE id=?", (TODAY.isoformat(), row["id"]))
            conn.commit()
        else:
            print("\n⏸️ 该任务今日不发送")

    conn.close()
    print("\n🎉 执行完成")

if __name__ == "__main__":
    main()
