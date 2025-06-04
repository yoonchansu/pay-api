def calculate_manual_pay(data: dict) -> dict:
    # 1. 근무일 수 계산
    num_days = len(data["workingDays"])

    # 2. 총 근무시간 계산 (기본 근무)
    total_work_hours = num_days * (data["workHour"] + data["workMinute"] / 60)

    # 3. 연장근무 시간 계산
    total_overtime_hours = num_days * (data["overtimeHour"] + data["overtimeMinute"] / 60)

    # 4. 야간근무 시간 (하루 4시간 기준이라고 내가 임의로 가정. 수정가능함)
    total_night_hours = num_days * 4 if data["nightWork"] else 0

    # 5. 기본급 계산
    pay_type = data["payType"]
    amount = data["payAmount"]

    if pay_type == "시급":
        base_pay = total_work_hours * amount
    elif pay_type == "일급":
        base_pay = num_days * amount
    elif pay_type == "월급":
        base_pay = amount  # 월급은 그대로 사용
    else:
        base_pay = 0  # 예외 방지용

    # 6. 연장수당 (시급 × 1.5)
    overtime_pay = total_overtime_hours * amount * 1.5 if pay_type == "시급" else 0

    # 7. 야간수당 (시급 × 0.5)
    night_pay = total_night_hours * amount * 0.5 if pay_type == "시급" else 0

    # 8. 주휴수당 (시급 × 8시간, 주 15시간 이상 근무 시)
    weekly_allowance = 0
    if data["includeWeeklyAllowance"] and pay_type == "시급" and total_work_hours >= 15:
        weekly_allowance = num_days // 7 * amount * 8  # 1주마다 하루치 추가

    # 9. 총 세전 급여
    gross_pay = base_pay + overtime_pay + night_pay + weekly_allowance

    # 10. 세금 계산
    tax_rate = 0.0
    if data["taxOption"] == "insurance":
        tax_rate = 0.0879
    elif data["taxOption"] == "income":
        tax_rate = 0.033

    tax = gross_pay * tax_rate
    net_pay = gross_pay - tax

    return {
        "grossPay": int(gross_pay),
        "weeklyAllowance": int(weekly_allowance),
        "overtimePay": int(overtime_pay),
        "nightPay": int(night_pay),
        "tax": int(tax),
        "netPay": int(net_pay)
    }

