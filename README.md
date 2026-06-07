🌐 Language / 语言
- [English](./README.md)
- [中文](./README.zh-CN.md)
# 📅 Daily Reminder System

An automated reminder system that sends emails based on configurations stored in a MySQL database. It supports one-time notifications, general reminders, and recurring important reminders (daily/weekly/monthly).

This project is designed to run on **GitHub Actions**.

## ✨ Features

- **Database-Driven**: All reminder rules are managed via SQL.
- **Time-Window Sending**: Emails are sent only after the configured `send_time`.
- **Human-Friendly Recurring Rules**:
  - `weekly:1` (Monday) to `weekly:7` (Sunday)
  - `monthly:5` (5th day of the month)
- **Holiday Skip**: Option to skip sending on weekends or public holidays (China).
- **Idempotent**: Guarantees that each reminder is sent only once per day.

## 🛠️ Tech Stack

- **Language**: Python 3.10
- **Database**: MySQL (Aiven Cloud)
- **Scheduler**: GitHub Actions (Hourly)
- **Email**: SMTP (QQ Mail Example)

## 🚀 Setup Guide

### 1. Database Setup (Aiven)

Create a MySQL table using the following SQL:
sql
CREATE TABLE reminders (
id INT AUTO_INCREMENT PRIMARY KEY,
title VARCHAR(255) NOT NULL COMMENT 'Email Title',
content TEXT NOT NULL COMMENT 'Email Content',
to_email VARCHAR(255) NOT NULL COMMENT 'Recipient',
member_name VARCHAR(100) COMMENT 'Member Name',
remind_type ENUM('notify', 'normal', 'important') DEFAULT 'normal' COMMENT 'Reminder Type',
event_date DATE NOT NULL COMMENT 'Event Date',
expire_date DATE COMMENT 'Expiration Date for Important Reminders',
send_time TIME DEFAULT '09:00:00' COMMENT 'Send Time',
repeat_rule VARCHAR(50) COMMENT 'weekly:1 / monthly:5',
advance_days INT DEFAULT 0 COMMENT 'Advance Days',
skip_holiday TINYINT DEFAULT 1 COMMENT 'Skip Holidays',
status ENUM('pending', 'notified', 'completed') DEFAULT 'pending',
last_sent_date DATE DEFAULT NULL COMMENT 'Last Sent Date'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
纯文本
### 2. GitHub Secrets Configuration

Go to `Settings > Secrets and variables > Actions` and add the following:

| Secret Name | Description |
| :--- | :--- |
| `DB_HOST` | Aiven Database Host |
| `DB_PORT` | Database Port (usually 24811) |
| `DB_USER` | Database User (usually avnadmin) |
| `DB_PASS` | Database Password |
| `DB_NAME` | Database Name (usually defaultdb) |
| `EMAIL_USER` | Sender Email (e.g., 123456@qq.com) |
| `EMAIL_PASS` | **QQ Mail SMTP Authorization Code** (Not login password) |

### 3. Execution Logic

Due to potential instability in GitHub Actions scheduling (sometimes delayed by 1–3 hours), this project relies on **business logic fallback** rather than strict Cron timing:

1.  GitHub Actions runs **once per hour**.
2.  The Python script checks if the current time is **later than or equal to** `send_time`.
3.  If yes, and the reminder has not been sent today, it sends the email immediately.

✅ This design ensures that even if GitHub runs late, the daily reminder will not be missed.

---

> 📄 中文文档请见：[README.zh-CN.md](./README.zh-CN.md)
