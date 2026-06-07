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
    if rule and rule.startswith(('weekly', 'monthly', 'yearly')):
        return min(max(adv, 0), 30)
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
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME,
        charset="utf8mb4", ssl={"ssl": {}}
    )

    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM reminders WHERE status IN ('pending', 'notified')")
    rows = cur.fetchall()

    print(f"📊 共加载 {len(rows)} 条提醒\n")

    for row in rows:
        print("=" * 50)
        print(f"ID:{row['id']} | {row['title']} | 类型:{row['remind_type']}")

        rule = row['repeat_rule'] or ''
        advance = normalize_advance_days(rule, row['advance_days'])
        window_start = row['event_date'] - timedelta(days=advance)

        # ============================================================
        # ✅ 第一步：先处理“死掉的规则”（最关键）
        # ============================================================
        if TODAY > row['expire_date']:
            cur.execute("UPDATE reminders SET status='completed' WHERE id=%s", (row['id'],))
            conn.commit()  # ✅ 立刻落库
            print("⏰ 已过期 → completed")
            continue

        # ============================================================
        # ✅ 第二步：还没到提醒窗口，直接跳过
        # ============================================================
        if TODAY < window_start:
            print("❌ 还没到提醒时间")
            continue

        # ============================================================
        # ✅ 第三步：循环规则匹配
        # ============================================================
        if rule.startswith('weekly:'):
            if TODAY.weekday() != int(rule.split(':')[1]) - 1:
                continue
        elif rule.startswith('monthly:'):
            if TODAY.day != int(rule.split(':')[1]):
                continue
        elif rule.startswith('yearly:'):
            if TODAY.strftime('%m-%d') != rule.split(':')[1]:
                continue
        elif rule == 'daily':
            pass
        else:  # 一次性提醒
            if TODAY != window_start:
                continue

        # ============================================================
        # ✅ 第四步：节假日
        # ============================================================
        if row['skip_holiday'] == 1 and (TODAY.weekday() >= 5 or not is_workday(TODAY)):
            print("⏸️ 跳过：非工作日")
            continue

        # ============================================================
        # ✅ 第五步：Notify vs Reminder 分流
        # ============================================================
        if row['remind_type'] == 'notify':
            try:
                send_mail(row['to_email'], row['member_name'], row['title'], row['content'])
                if not rule:
                    cur.execute("UPDATE reminders SET status='completed' WHERE id=%s", (row['id'],))
                    print("✅ 一次性 Notify → completed")
                else:
                    cur.execute("UPDATE reminders SET last_sent_date=%s WHERE id=%s", (TODAY, row['id'],))
                    print("✅ 循环 Notify 已发送")
                conn.commit()  # ✅ 立刻落库
            except Exception as e:
                print(f"❌ 邮件失败: {e}")
            continue

        # ============================================================
        # ✅ Reminder（Normal / Important）
        # ============================================================
        if row['remind_type'] == 'important':
            if NOW_TIME < row['send_time']:
                print("❌ 时间未到")
                continue
            if row['last_sent_date'] == TODAY:
                print("❌ 今天已发过")
                continue

        try:
            send_mail(row['to_email'], row['member_name'], row['title'], row['content'])
            print("✅ 提醒已发送")
            if row['remind_type'] == 'important':
                cur.execute("UPDATE reminders SET last_sent_date=%s WHERE id=%s", (TODAY, row['id'],))
            conn.commit()  # ✅ 立刻落库
        except Exception as e:
            print(f"❌ 邮件失败: {e}")
        continue

    conn.close()
    print("\n🎉 执行完成")

if __name__ == "__main__":
    main()
