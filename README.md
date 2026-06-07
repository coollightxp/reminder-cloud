🌐 Language / 语言
- [English](./README.md)
- [中文](./README.zh-CN.md)
# ==================================================
# 📄 README.md (English Version)
# ==================================================
# 📅 Daily Reminder System

An automated reminder system that sends emails based on configurations stored in a MySQL database. It supports one-time notifications, general reminders, and recurring important reminders (daily/weekly/monthly).

This project is designed to run on **GitHub Actions**.

## ✨ Features

*   **Database-Driven**: All reminder rules are managed via SQL.
*   **Time-Window Sending**: Emails are sent only after the configured `send_time`.
*   **Recurring Rules**:
    *   `weekly:1` (Monday) to `weekly:7` (Sunday)
    *   `monthly:5` (5th day of the month)
*   **Holiday Skip**: Option to skip sending on weekends or public holidays (China).
*   **Idempotent**: Guarantees that each reminder is sent only once per day.

## 🛠️ Tech Stack

*   **Language**: Python 3.10
*   **Database**: MySQL (Aiven Cloud)
*   **Scheduler**: GitHub Actions
*   **Email**: SMTP (QQ Mail Example)

## 🚀 Setup Guide

### 1. Database Setup (Aiven)
Create a MySQL table using the following SQL:
没问题，为了方便你复制，我把英文版和中文版的 README 内容合并到一个代码块里了。
你只需要：
把 英文部分​ 复制保存到 README.md
把 中文部分​ 复制保存到 README.zh-CN.md
# ==================================================
# 📄 README.md (English Version)
# ==================================================

<div align="right">
  <a href="./README.zh-CN.md">🇨🇳 切换到中文文档</a>
</div>

<br>

# 📅 Daily Reminder System

An automated reminder system that sends emails based on configurations stored in a MySQL database. It supports one-time notifications, general reminders, and recurring important reminders (daily/weekly/monthly).

This project is designed to run on **GitHub Actions**.

## ✨ Features

*   **Database-Driven**: All reminder rules are managed via SQL.
*   **Time-Window Sending**: Emails are sent only after the configured `send_time`.
*   **Recurring Rules**:
    *   `weekly:1` (Monday) to `weekly:7` (Sunday)
    *   `monthly:5` (5th day of the month)
*   **Holiday Skip**: Option to skip sending on weekends or public holidays (China).
*   **Idempotent**: Guarantees that each reminder is sent only once per day.

## 🛠️ Tech Stack

*   **Language**: Python 3.10
*   **Database**: MySQL (Aiven Cloud)
*   **Scheduler**: GitHub Actions
*   **Email**: SMTP (QQ Mail Example)

## 🚀 Setup Guide

### 1. Database Setup (Aiven)
Create a MySQL table using the following SQL:
sql
CREATE TABLE reminders (
id INT AUTO_INCREMENT PRIMARY KEY,
title VARCHAR(255) NOT NULL,
content TEXT NOT NULL,
to_email VARCHAR(255) NOT NULL,
member_name VARCHAR(100),
remind_type ENUM('notify', 'normal', 'important') DEFAULT 'normal',
event_date DATE NOT NULL,
expire_date DATE,
send_time TIME DEFAULT '09:00:00',
repeat_rule VARCHAR(50), -- e.g., 'weekly:1' or 'monthly:5'
advance_days INT DEFAULT 0,
skip_holiday TINYINT DEFAULT 1,
status ENUM('pending', 'notified', 'completed') DEFAULT 'pending',
last_sent_date DATE DEFAULT NULL
);
### 2. GitHub Secrets Configuration
Go to `Settings > Secrets and variables > Actions` and add the following:

*   `DB_HOST`
*   `DB_PORT`
*   `DB_USER`
*   `DB_PASS`
*   `DB_NAME`
*   `EMAIL_USER`
*   `EMAIL_PASS` (QQ Mail Authorization Code)

### 3. Local Testing
You can test locally by setting environment variables first:
bash
export DB_HOST=your_host
export DB_PORT=your_port
... (fill all secrets)
python remind_engine.py
