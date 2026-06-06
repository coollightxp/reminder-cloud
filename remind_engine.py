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
# 时间解析
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
# 核心算法：周期性任务自动计算发送日
# ===============================
def calc_periodic_send_date(row):
    rule = row["repeat_rule"]
    advance = int(row["advance_days"] or 0)
    today = TODAY

    if rule == "daily":
        target = today
        send = target - timedelta(days=advance)
        return today == send, target, send

    if rule.startswith("weekly:"):
        wd = today.weekday()
        days = list(map(int, rule.split(":")[1].split(",")))
        if wd not in days:
            return False, today, today
        target = today
        send = target - timedelta(days=advance)
        return today == send, target, send

    if rule.startswith("monthly:"):
        target_day = int(rule.split(":")[1])
        max_day = calendar.monthrange(today.year, today.month)[1]
        actual_target = min(target_day, max_day)
        target = date(today.year, today.month, actual_target)
        send = target - timedelta(days=advance)
        return today == send, target, send

    if rule.startswith("yearly:"):
        md = rule.split(":")[1]
        target = datetime.strptime(f"{today.year}-{md}", "%Y-%m-%d").date()
        send = target - timedelta(days=advance)
        return today == send, target, send

    return False, today, today

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
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

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

            if row["is_sent"] == 1:
                print("❌ 结论：is_sent=1，已发送或正在发送，跳过")
                continue

            try:
                target_date = date.fromisoformat(row["remind_date"])
            except Exception as e:
                print(f"❌ remind_date 解析失败: {e}")
                continue

            advance = int(row["advance_days"] or 0)
            send_on_date = target_date - timedelta(days=advance)

            print(f"   原定日期: {target_date}")
            print(f"   提前天数: {advance}")
            print(f"   ➜ 应发送日: {send_on_date} | 今天: {TODAY}")

            if send_on_date != TODAY:
                print("❌ 结论：日期不匹配，跳过")
                continue

            can_send_today = True

        # ---- 2. 周期性任务 ----
        else:
            print("\n🟢 [类型] 周期性任务")
            ok, target_date, send_on_date = calc_periodic_send_date(row)

            print(f"   规则: {row['repeat_rule']}")
            print(f"   原定日期: {target_date}")
            print(f"   提前天数: {row['advance_days']}")
            print(f"   ➜ 应发送日: {send_on_date} | 今天: {TODAY}")

            if not ok:
                print("❌ 结论：今天不是发送日")
                continue

            if row["last_done"] == TODAY.isoformat():
                print("❌ 结论：last_done 已标记，跳过")
                continue

            if row["repeat_rule"] == "daily" and row["skip_holiday"] == 1:
                if not is_workday(TODAY):
                    print("❌ 结论：节假日，跳过")
                    continue

            can_send_today = True

        # ---- 3. 时间宽容 + 防重发 + 失败回滚 ----
        if can_send_today:
            send_time_obj = parse_time(row["send_time"])
            print(f"   发送时间: {send_time_obj} | 当前时间: {NOW_TIME}")

            if not send_time_obj or send_time_obj > NOW_TIME:
                print("❌ 结论：时间未到，跳过")
                continue

            print("🚀 条件全部满足，准备锁定并发送！")

            # ==========================================
            # ✅ 第一步：先锁住（防止并发重发）
            # ==========================================
            try:
                if row["repeat_rule"] is None:
                    cur.execute("UPDATE reminders SET is_sent=1 WHERE id=?", (row["id"],))
                else:
                    cur.execute("UPDATE reminders SET last_done=? WHERE id=?", (TODAY.isoformat(), row["id"]))
                conn.commit()
                print(f"✅ 任务已锁定 (ID: {row['id']})")
            except Exception as e:
                print(f"❌ 数据库锁定失败: {e}")
                continue

            # ==========================================
            # ✅ 第二步：发邮件（带回滚机制）
            # ==========================================
            mail_result = send_mail(
                row["to_email"],
                row["member_name"],
                row["title"],
                row["content"]
            )

            # ==========================================
            # ✅ 第三步：根据结果修正状态
            # ==========================================
            if mail_result:
                # 发送成功：保持锁定状态（一次性任务 is_sent=1，周期性任务 last_done=今天）
                print("✅ 流程结束：发送成功，状态已固化")
            else:
                # 发送失败：回滚状态，允许下次重试
                print("🔄 发送失败，正在回滚状态以允许重试...")
                try:
                    if row["repeat_rule"] is None:
                        cur.execute("UPDATE reminders SET is_sent=0 WHERE id=?", (row["id"],))
                    else:
                        cur.execute("UPDATE reminders SET last_done=NULL WHERE id=?", (row["id"],))
                    conn.commit()
                    print("✅ 状态已回滚，下次运行将重试")
                except Exception as rollback_err:
                    print(f"❌ 状态回滚失败: {rollback_err}")

        else:
            print("\n⏸️ 该任务今日不发送")

    conn.close()
    print("\n🎉 执行完成")

if __name__ == "__main__":
    main()
