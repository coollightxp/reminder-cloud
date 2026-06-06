# ---- 2. 周期性任务（支持提前 N 天） ----
else:
    print("\n🟢 [类型] 周期性任务")
    print(f"   原始规则: {row['repeat_rule']}")
    
    target_date = None
    is_match = False

    # ① 先计算“今天是否符合周期规则”
    if row["repeat_rule"] == "daily":
        is_match = True
        print("   匹配规则: 每天")
    elif row["repeat_rule"].startswith("weekly:"):
        wd = TODAY.weekday()
        days = list(map(int, row["repeat_rule"].split(":")[1].split(",")))
        if wd in days:
            is_match = True
        print(f"   匹配规则: 每周 {days} | 今天是周 {wd}")
    elif row["repeat_rule"].startswith("monthly:"):
        import calendar
        target_day = int(row["repeat_rule"].split(":")[1])
        max_day = calendar.monthrange(TODAY.year, TODAY.month)[1]
        actual_target_day = min(target_day, max_day)
        target_date = date(TODAY.year, TODAY.month, actual_target_day)
        if TODAY.day == actual_target_day:
            is_match = True
        print(f"   匹配规则: 每月 {target_day} 号 | 今天是 {TODAY.day} 号")
    elif row["repeat_rule"].startswith("yearly:"):
        md = row["repeat_rule"].split(":")[1]
        if TODAY.strftime("%m-%d") == md:
            is_match = True
        print(f"   匹配规则: 每年 {md} | 今天是 {TODAY.strftime('%m-%d')}")

    # ② 如果是节假日，直接跳过（仅限 daily）
    if row["repeat_rule"] == "daily" and row["skip_holiday"] == 1:
        if not is_workday(TODAY):
            print("❌ 结论：节假日，跳过")
            continue

    # ③ ✅ 核心：处理提前 N 天（关键修复点）
    if is_match:
        advance_days = int(row["advance_days"]) if row["advance_days"] not in (None, "") else 0
        
        # 如果是每月/每年，我们需要基于“原定日期”往前推
        if row["repeat_rule"].startswith(("monthly:", "yearly:")):
            if target_date is None: # 兜底，一般不会发生
                target_date = TODAY
            
            send_on_date = target_date - timedelta(days=advance_days)
            print(f"   原定日期: {target_date} | 提前 {advance_days} 天")
            print(f"   ➜ 实际发送日: {send_on_date}")
            
            if send_on_date != TODAY:
                print("❌ 结论：今天不是提前提醒日，跳过")
                continue
        else:
            # 每天或每周，直接看今天
            if advance_days > 0:
                print(f"⚠️ 注意：每日/每周任务不建议设置提前天数，建议用具体时间代替")
        
        print("✅ 结论：今天符合周期规则")
        can_send_today = True
    else:
        print("❌ 结论：今天不符合周期规则")
