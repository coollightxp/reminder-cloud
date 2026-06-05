# 📬 Remind Scheduler（提醒调度系统）

基于 **SQLite + Python + GitHub Actions** 的轻量提醒系统。

✅ 一次性 / 周期提醒  
✅ 提前 N 天提醒  
✅ 结果通知  
✅ 节假日跳过（仅 daily）  
✅ 月末 / 闰年自动适配  

### 提醒类型

| remind_type | advance_days | 说明 |
|------------|--------------|------|
| result | 0 | 当天结果通知 |
| advance | ≥1 | 提前提醒 |

详见 `schema.sql` 与 `remind_engine.py`。
