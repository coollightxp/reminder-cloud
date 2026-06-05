🌐 Language / 语言
- [English](./README.md)
- [中文](./README.zh-CN.md)
# 📬 Remind Scheduler

A lightweight reminder system based on **SQLite + Python + GitHub Actions**.

✅ One-off & recurring reminders  
✅ Advance notice (N days before)  
✅ Result notification  
✅ Holiday skip (daily only)  
✅ Month-end & leap year safe  

### Rule Logic

| Type | advance_days |
|----|----|
| result | 0 |
| advance | ≥1 |

See `schema.sql` and `remind_engine.py`.
