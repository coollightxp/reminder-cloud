# Reminder Cloud（企业微信版）

基于 GitHub Actions + SQLite + 企业微信 Webhook 的提醒系统。

✅ 所有业务数据与白名单由本地生成  
✅ 云端仅负责读取数据库并发送企业微信提醒  
✅ 不创建表、不初始化数据  

## 架构说明
本地（Delphi / SQLite）负责创建数据库、写入 wechat_members（白名单）、写入 reminders / periodic_tasks，并通过 git push 推送到 GitHub 仓库。GitHub Actions 读取 db/reminder.db，并调用企业微信 Webhook 发送提醒。

## 数据库结构（本地生成）
云端不会修改数据库结构，以下仅供参考。

### wechat_members（白名单）
| 字段 | 说明 |
|----|----|
| id | 主键 |
| at_name | @昵称（如 @妈妈） |
| display_name | 显示名称 |
| is_active | 是否启用 |

### reminders（一次性提醒）
| 字段 | 说明 |
|----|----|
| id | 主键 |
| title | 提醒内容 |
| member_id | 关联 wechat_members |
| remind_date | 提醒日期 |
| is_sent | 是否已发送 |

### periodic_tasks（周期提醒）
| 字段 | 说明 |
|----|----|
| id | 主键 |
| title | 提醒内容 |
| member_id | 关联 wechat_members |
| interval_days | 周期（天） |
| last_done | 上次执行日期 |
| skip_weekend_holiday | 是否跳过周末与节假日 |

## 企业微信提醒规则
支持 @ 指定群成员，支持 @all；周期提醒可选择跳过周末与法定节假日；若遇节假日，自动顺延至最近工作日。

## 使用方式
1️⃣ 本地生成数据库：使用 Delphi 或其他 SQLite 工具生成 db/reminder.db，并确保包含白名单数据，例如：
INSERT INTO wechat_members (at_name, display_name) VALUES
('@妈妈', '妈妈'),
('@爸爸', '爸爸'),
('@张三', '我自己'),
('@all', '所有人');

2️⃣ 推送到 GitHub：
git add db/reminder.db
git commit -m "update reminder data"
git push

3️⃣ 配置 Secrets：仓库 → Settings → Secrets → Actions，添加：
Name: WECHAT_WEBHOOK
Value: 企业微信群机器人 Webhook

## 运行方式
自动：每日定时执行；手动：GitHub → Actions → Run workflow。

## 注意事项
云端不会创建或修改表；企业微信昵称必须与 wechat_members.at_name 一致；节假日判断依赖第三方 API（timor.tech）；本地生成的 DB 是唯一可信数据源。

## License
MIT
