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
# 周期判断
# ===============================
def should_execute_periodic(row):
    wd = TODAY.weekday()
    rule = row["repeat_rule"]

    if rule == "daily":
        return True
    if rule.startswith("weekly:"):
        days = list(map(int, rule.split(":")[1].split(",")))
        return wd in days
    if rule.startswith("monthly:"):
        import calendar
        target = int(rule.split(":")[1])
        max_day = calendar.monthrange(TODAY.year, TODAY.month)[1]
        return TODAY.day == min(target, max_day)
    if rule.startswith("yearly:"):
        md = rule.split(":")[1]
        return TODAY.strftime("%m-%d") == md
    return False

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
# 主逻辑（全调试日志版）
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

        # ---- 1. 一次性任务（带完整诊断） ----
        if row["repeat_rule"] is None:
            print("\n🟢 [类型] 一次性任务")

            # ① remind_date
            try:
                target_date = date.fromisoformat(row["remind_date"])
            except Exception as e:
                print(f"❌ remind_date 解析失败: {row['remind_date']} | {e}")
                continue

            # ② advance_days
            adv = row["advance_days"]
            advance_days = int(adv) if adv not in (None, "") else 0

            # ③ 计算发送日
            send_on_date = target_date - timedelta(days=advance_days)

            print(f"   原定日期: {target_date}")
            print(f"   提前天数: {advance_days}")
            print(f"   ➜ 实际应发送日: {send_on_date}")
            print(f"   今天是: {TODAY}")

            if send_on_date != TODAY:
                print("❌ 结论：日期不匹配，跳过")
                continue

            print("✅ 结论：日期匹配")

            # ④ 时间判断
            send_time_obj = parse_time(row["send_time"])
            print(f"   发送时间: {send_time_obj}")
            print(f"   当前时间: {NOW_TIME}")

            if not send_time_obj or send_time_obj > NOW_TIME:
                print("❌ 结论：时间未到，跳过")
                continue

            print("✅ 结论：时间已过")

            # ⑤ last_done
            print(f"   last_done: {repr(row['last_done'])}")
            if row["last_done"] == TODAY.isoformat():
                print("❌ 结论：今天已发过，跳过")
                continue

            print("✅ 结论：今天尚未发送")
            can_send_today = True

        # ---- 2. 周期性任务 ----
        else:
            print("\n🟢 [类型] 周期性任务")
            if should_execute_periodic(row):
                print("✅ 结论：今天符合周期规则")
                can_send_today = True
            else:
                print("❌ 结论：今天不符合周期规则")

            if row["repeat_rule"] == "daily" and row["skip_holiday"] == 1:
                if not is_workday(TODAY):
                    print("❌ 结论：节假日，跳过")
                    can_send_today = False

        # ---- 3. 执行发送 ----
        if can_send_today:
            print("\n🚀 准备发送邮件...")
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
