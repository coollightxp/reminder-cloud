🌐 Language / 语言
- [English](./README.md)
- [中文](./README.zh-CN.md)
# 📅 每日提醒系统

一个基于 MySQL 数据库配置的自动化邮件提醒系统。支持一次性通知、普通提醒和重要循环提醒（每日/每周/每月）。

本项目专为 **GitHub Actions** 设计。

## ✨ 功能特性

*   **数据库驱动**：所有提醒规则通过 SQL 管理。
*   **时间窗口发送**：严格遵守 `send_time` 配置，在此之前绝不发送。
*   **循环规则（人类友好格式）**：
    *   `weekly:1` (周一) 至 `weekly:7` (周日)
    *   `monthly:5` (每月 5 号)
*   **跳过节假日**：可选择在非工作日或法定节假日不发送（针对中国区）。
*   **幂等性保证**：利用 `last_sent_date` 确保每个提醒当天只发送一次。

## 🛠️ 技术栈

*   **语言**: Python 3.10
*   **数据库**: MySQL (Aiven 云服务)
*   **调度器**: GitHub Actions (每小时运行)
*   **邮件**: SMTP (以 QQ 邮箱为例)

## 🚀 部署指南

### 1. 数据库设置 (Aiven)
使用以下 SQL 创建表结构：
sql
CREATE TABLE reminders (
id INT AUTO_INCREMENT PRIMARY KEY,
title VARCHAR(255) NOT NULL COMMENT '邮件标题',
content TEXT NOT NULL COMMENT '邮件正文',
to_email VARCHAR(255) NOT NULL COMMENT '收件人',
member_name VARCHAR(100) COMMENT '成员名',
remind_type ENUM('notify', 'normal', 'important') DEFAULT 'normal' COMMENT '提醒类型',
event_date DATE NOT NULL COMMENT '事件日期',
expire_date DATE COMMENT '重要提醒截止日期',
send_time TIME DEFAULT '09:00:00' COMMENT '发送时刻',
repeat_rule VARCHAR(50) COMMENT 'weekly:1 / monthly:5',
advance_days INT DEFAULT 0 COMMENT '提前天数',
skip_holiday TINYINT DEFAULT 1 COMMENT '是否跳过节假日',
status ENUM('pending', 'notified', 'completed') DEFAULT 'pending',
last_sent_date DATE DEFAULT NULL COMMENT '最后发送日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
纯文本
### 2. GitHub Secrets 配置
进入仓库 `Settings > Secrets and variables > Actions`，添加以下密钥：

*   `DB_HOST` (Aiven 数据库地址)
*   `DB_PORT` (端口，通常为 24811)
*   `DB_USER` (用户名，通常为 avnadmin)
*   `DB_PASS` (数据库密码)
*   `DB_NAME` (数据库名，通常为 defaultdb)
*   `EMAIL_USER` (发件人邮箱，如 `123456@qq.com`)
*   `EMAIL_PASS` (**QQ 邮箱 SMTP 授权码**，非登录密码)

### 3. 运行逻辑说明
由于 GitHub Actions 的运行时间可能不稳定（有时延迟 1-3 小时），本项目采用**业务逻辑兜底**而非依赖 Cron 时间：

1.  GitHub Actions **每小时检查一次**。
2.  Python 脚本检查当前时间是否 **晚于** `send_time`。
3.  如果是，且当天未发送，则发送邮件。

✅ 这种设计确保了即使 GitHub 运行晚了，也不会错过当天的提醒。

