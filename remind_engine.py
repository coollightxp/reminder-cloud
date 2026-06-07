import os
import pymysql
import requests
from datetime import datetime, timedelta
import pytz

# ===============================
# 基础配置（从环境变量读取）
# ===============================
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT"))
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")

BEIJING_TZ = pytz.timezone("Asia/Shanghai")
NOW_DT = datetime.now(BEIJING_TZ)
TODAY = NOW_DT.date()
NOW_TIME = NOW_DT.time()

print(f"\n🚀 脚本启动 - 当前时间: {NOW_DT.strftime('%Y-%m-%d %H:%M:%S')}\n")

# ===============================
# 节假日判断
# ===============================
def is_workday(d):
    try:
        url = f"https://natescarlet.coding.net/p/holiday/d/holiday/git/raw/master/{d.year}/{d}.json"
        r = requests.get(url, timeout=(3, 5))
        return r.json().get("code", 0) == 0
    except Exception:
        return True

# ===============================
# 提前天数约束
# ===============================
def normalize_advance_days(rule, adv):
    try:
        adv = int(adv or 0)
    except:
        adv = 0

    if rule and rule.startswith('weekly'):
        return min(max(adv, 0), 2)
    elif rule and rule.startswith('monthly'):
        return min(max(adv, 0), 5)
    return adv

# ===============================
# 邮件发送
# ===============================
def send_mail(to_email, member_name, title, content):
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header

    user = os.environ["EMAIL_USER"]
    pwd = os.environ["EMAIL_PASS"]

    msg = MIMEText(content, "plain", "utf-8")
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = Header(title, "utf-8")

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(user, pwd)
    server.sendmail(user, [to_email], msg.as_string())
    server.quit()

    print(f"✅ 邮件发送成功 -> {to_email}")

# ===============================
# 主逻辑
# ===============================
def main():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        ssl={"ssl": {}}
    )

    cur = conn.cursor(pymysql.cursors.DictCursor)
    # 只查未完成的，或者今天可能还需要发的重要提醒
    cur.execute("SELECT * FROM reminders WHERE status IN ('pending', 'notified')")
    rows = cur.fetchall()

    print(f"📊 共加载 {len(rows)} 条提醒\n")

    for row in rows:
        print("=" * 50)
        print(f"ID:{row['id']} | {row['title']} | 类型:{row['remind_type']}")

        rule = row['repeat_rule'] or ''
        advance = normalize_advance_days(rule, row['advance_days'])
        window_start = row['event_date'] - timedelta(days=advance)

        # 还没到提前提醒的窗口期
        if TODAY < window_start:
            print("❌ 还没到提醒时间")
            continue

        # ===== weekly / monthly 精确匹配（人类版 1-7）=====
        if rule.startswith('weekly:'):
            target_weekday = int(rule.split(':')[1]) - 1  # 1-7 转 0-6
            if TODAY.weekday() != target_weekday:
                continue

        elif rule.startswith('monthly:'):
            target_day = int(rule.split(':')[1])
            if TODAY.day != target_day:
                continue

        # ===== notify (一次性通知) =====
        if row['remind_type'] == 'notify':
            if TODAY != row['event_date']:
                continue
            if row['skip_holiday'] == 1 and (TODAY.weekday() >= 5 or not is_workday(TODAY)):
                print("⏸️ 通知跳过：非工作日")
                continue
            try:
                send_mail(row['to_email'], row['member_name'], row['title'], row['content'])
                # ✅ 修正点：一次性通知发完即结束
                cur.execute("UPDATE reminders SET status='completed' WHERE id=%s", (row['id'],))
                print("✅ 状态已更新为 completed")
            except Exception as e:
                print(f"❌ 邮件失败: {e}")
            continue

        # ===== normal (普通提醒) =====
        if row['remind_type'] == 'normal':
            if TODAY != window_start:
                continue
            if row['skip_holiday'] == 1 and (TODAY.weekday() >= 5 or not is_workday(TODAY)):
                print("⏸️ 提醒跳过：非工作日")
                continue
            try:
                send_mail(row['to_email'], row['member_name'], row['title'], row['content'])
                # ✅ 修正点：普通提醒发完即结束
                cur.execute("UPDATE reminders SET status='completed' WHERE id=%s", (row['id'],))
                print("✅ 状态已更新为 completed")
            except Exception as e:
                print(f"❌ 邮件失败: {e}")
            continue

        # ===== important (重要循环提醒) =====
        if row['remind_type'] == 'important':
            if TODAY > row['expire_date']:
                cur.execute("UPDATE reminders SET status='completed' WHERE id=%s", (row['id'],))
                print("⏰ 已过期，标记为完成")
                continue
            
            # ✅ 防重发核心：今天已经发过了
            if row['last_sent_date'] == TODAY:
                print("❌ 今天已发过")
                continue
            
            if NOW_TIME < row['send_time']:
                print("❌ 时间未到")
                continue
            
            try:
                send_mail(row['to_email'], row['member_name'], row['title'], row['content'])
                # ✅ 只更新发送日期，不改状态，下周/下个月还能跑
                cur.execute("UPDATE reminders SET last_sent_date=%s WHERE id=%s", (TODAY, row['id'],))
                print("✅ 重要提醒已发送，记录今日日期")
            except Exception as e:
                print(f"❌ 邮件失败: {e}")
            continue

    conn.commit()
    conn.close()
    print("\n🎉 执行完成")

if __name__ == "__main__":
    main()
