import os
import pymysql
from datetime import datetime, timedelta
import pytz

# ===============================
# 数据库配置（从环境变量读取）
# ===============================
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT"))
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")

TZ = pytz.timezone("Asia/Shanghai")
TODAY = datetime.now(TZ).date()

print(f"🚀 提醒引擎启动，当前日期: {TODAY}")

# ===============================
# 数据库连接
# ===============================
def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        ssl={"ssl": {}}
    )

# ===============================
# 第一步：清理 completed（保留 7 天）
# ===============================
def clean_completed(conn):
    cur = conn.cursor()
    cutoff = TODAY - timedelta(days=7)

    cur.execute("""
        DELETE FROM reminders
        WHERE status = 'completed'
          AND updated_at < %s
    """, (cutoff,))

    conn.commit()
    print(f"🧹 已清理 7 天前 completed 记录（截止 {cutoff}）")

# ===============================
# 第二步：处理今天的提醒
# ===============================
def process_reminders(conn):
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT *
        FROM reminders
        WHERE status IN ('pending', 'notified')
          AND event_date <= %s
          AND expire_date >= %s
    """, (TODAY, TODAY))

    rows = cur.fetchall()
    print(f"📊 待处理提醒数量: {len(rows)}")

    for row in rows:
        print(f"🔔 处理提醒: {row['title']}")

        # TODO: 在这里调用你的 send_mail
        # send_mail(...)

        cur.execute("""
            UPDATE reminders
            SET status = 'completed'
            WHERE id = %s
        """, (row['id'],))

    conn.commit()

# ===============================
# 主入口
# ===============================
def main():
    conn = get_conn()
    try:
        clean_completed(conn)
        process_reminders(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
