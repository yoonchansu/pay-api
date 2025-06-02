



#step1. 근무시간 계산 

"""코드 요약:
calculate_work_hours(start, end)
#→ 문자열로 주어진 startTime, endTime을 받아 근무 시간을 시간단위(float)로 계산해 주는 함수
자정 넘긴 야간근무도 고려해서 end < start일 경우 하루를 더해 계산"""

from datetime import datetime, timedelta

from supabase import create_client
import os
from dotenv import load_dotenv

# .env 파일을 불러와서 환경변수 등록
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabase 클라이언트 생성
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def calculate_work_hours(start: str, end: str) -> float:
    """
    문자열 startTime, endTime 기준으로 총 근무 시간을 시간 단위(float)로 반환
    """
    if not start or not end:
        return 0.0
    
    fmt = "%H:%M"
    start_dt = datetime.strptime(start, fmt)
    end_dt = datetime.strptime(end, fmt)

    # 자정 넘긴 경우 처리
    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    diff = end_dt - start_dt
    return round(diff.total_seconds() / 3600, 2)



#step2 기본급여 계산

"""코드 요약:
calculate_base_pay_from_row(row)
→ 한 개의 근무 row(dict)를 입력 받아, startTime, endTime, payInfo.hourPrice를 기반으로 기본 시급 × 근무 시간을 계산해서 기본급(int)을 반환하는 함수

payInfo가 문자열(json)일 수도 있어서 파싱 처리도 포함.
기본 시급은 없을 경우 DEFAULT_MINIMUM_WAGE = 10030으로 대체."""

DEFAULT_MINIMUM_WAGE = 10030  # 2025년 기준

import json

def calculate_base_pay_from_row(row: dict) -> int:
    start = row.get("startTime")
    end = row.get("endTime")

    pay_info_raw = row.get("payInfo", {})

    # payInfo가 문자열일 경우 dict로 변환
    if isinstance(pay_info_raw, str):
        try:
            pay_info = json.loads(pay_info_raw)
        except json.JSONDecodeError:
            pay_info = {}
    else:
        pay_info = pay_info_raw

    wage = pay_info.get("hourPrice", DEFAULT_MINIMUM_WAGE)

    worked_hours = calculate_work_hours(start, end)
    return int(worked_hours * wage)



#step3-1. 야간수당 계산

"""코드 요약:
이 코드는 야간수당 계산 로직

parse_payinfo(row)
→ Supabase의 payInfo 필드가 문자열일 수도 있으니 안전하게 dict로 파싱해주는 함수

calculate_night_pay(row)
→ 근무 시간이 22:00~06:00 사이에 걸쳐 있을 경우,
(야간 근무 시간 × 시급 × 0.5) 로 야간 수당 계산

payInfo.night가 True일 때만 계산
자정 넘김 및 겹치는 구간 계산 로직 포함"""

import json

def parse_payinfo(row: dict) -> dict:
    """
    Supabase에서 가져온 row의 payInfo 필드를 안전하게 dict로 변환.
    - 문자열(JSON str)인 경우: json.loads() 처리
    - dict인 경우: 그대로 반환
    - 실패 시: 빈 dict 반환
    """
    pay_info_raw = row.get("payInfo", {})
    if isinstance(pay_info_raw, str):
        try:
            return json.loads(pay_info_raw)
        except json.JSONDecodeError:
            return {}
    return pay_info_raw

def calculate_night_pay(row: dict) -> int:
    pay_info = parse_payinfo(row)
    if not pay_info.get("night"):
        return 0

    start = row.get("startTime")
    end = row.get("endTime")
    wage = pay_info.get("hourPrice", DEFAULT_MINIMUM_WAGE)

    if not start or not end:
        return 0

    fmt = "%H:%M"
    start_dt = datetime.strptime(start, fmt)
    end_dt = datetime.strptime(end, fmt)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    # 야간시간 범위 (22:00 ~ 06:00 다음날)
    night_start = datetime.combine(start_dt.date(), datetime.strptime("22:00", fmt).time())
    night_end = night_start + timedelta(hours=8)

    # 근무시간과 야간시간 겹치는 구간 계산
    overlap_start = max(start_dt, night_start)
    overlap_end = min(end_dt, night_end)

    if overlap_start >= overlap_end:
        night_hours = 0
    else:
        night_hours = (overlap_end - overlap_start).seconds / 3600

    return int(night_hours * wage * 0.5)


#step3-2. 연장근무수당 계산

"""코드 요약:
이 코드는 연장근무 수당 계산 로직

parse_payinfo(row)로 안전하게 시급 정보 로딩
payInfo.overtime가 True일 때만 연장수당 계산

하루 근무시간이 8시간을 초과하면, 초과 시간 × 시급 × 0.5로 연장근무 수당 계산
→ 근무시간이 8시간 이하면 0원 반환"""

def calculate_overtime_pay(row: dict) -> int:
    pay_info = parse_payinfo(row)  

    if not pay_info.get("overtime"):
        return 0

    start = row.get("startTime")
    end = row.get("endTime")
    wage = pay_info.get("hourPrice", DEFAULT_MINIMUM_WAGE)

    total_hours = calculate_work_hours(start, end)
    overtime_hours = max(0, total_hours - 8)

    return int(overtime_hours * wage * 0.5)





#step3-3. 주휴수당 계산

"""코드 요약:
이 코드는 주휴수당 계산 로직 

입력: 한 주 단위의 rows 리스트 (여러 근무 기록)
조건:
payInfo.wHoliday가 True인 경우에만 적용
총 근무 시간이 15시간 이상이어야 지급 가능
지급액: 시급 × 8시간 = 하루치 시급
(주 15시간 이상 근무자에게 유급휴일 1일 부여하는 기준 적용)"""

import json

def calculate_weekly_allowance(rows: list[dict]) -> int:
    if not rows:
        return 0

    total_hours = 0
    wage = DEFAULT_MINIMUM_WAGE
    apply = False

    for row in rows:
        pay_info_raw = row.get("payInfo", {})

        # pay_info가 문자열일 경우 dict로 변환
        if isinstance(pay_info_raw, str):
            try:
                pay_info = json.loads(pay_info_raw)
            except json.JSONDecodeError:
                pay_info = {}
        else:
            pay_info = pay_info_raw

        if pay_info.get("wHoliday"):
            apply = True
            wage = pay_info.get("hourPrice", wage)

        total_hours += calculate_work_hours(row.get("startTime"), row.get("endTime"))

    if apply and total_hours >= 15:
        return int(wage * 8)  # 주휴수당: 하루 시급
    return 0




#step3-4. 공휴일 수당 계산

"""코드 요약:
이 코드는 공휴일 수당 계산 로직

payInfo["Holiday"] == True일 때만 계산
공휴일에 일한 시간 × 시급 × 0.5로 추가 수당 지급

기본급에는 공휴일 근무 시간도 포함되므로, 여기선 추가분(0.5배)만 더하는 방식
→ 즉, 실제 총 지급은 1.5배가 됨"""

def calculate_holiday_pay(row: dict) -> int:
    """
    공휴일 수당 계산
    - 공휴일에 일한 시간 × 시급 × 0.5
    - payInfo["Holiday"]가 True인 경우에만 계산
    """
    pay_info = parse_payinfo(row)  # ✅ 안전하게 dict 변환

    if not pay_info.get("Holiday"):
        return 0

    start = row.get("startTime")
    end = row.get("endTime")
    wage = pay_info.get("hourPrice", DEFAULT_MINIMUM_WAGE)

    worked_hours = calculate_work_hours(start, end)
    return int(worked_hours * wage * 0.5)





#step4. 한 주간 총 근무시간 계산

"""코드 요약:
이 함수 get_weekly_hours(rows)는
주어진 rows 리스트(한 주의 근무 기록들)에서 총 근무 시간을 합산해서 float형으로 반환

내부적으로 calculate_work_hours() 사용
각 row마다 startTime, endTime 기준으로 시간 계산 후 모두 더함
주휴수당 판단이나 총 근무 통계 등에 활용 가능"""

def get_weekly_hours(rows: list[dict]) -> float:
    return sum(calculate_work_hours(r.get("startTime"), r.get("endTime")) for r in rows)







#step5. 세금공제 계산

"""코드 요약:
이건 세금 공제 계산 함수 

총 급여(total_pay)와 한 주 근무 기록(weekly_rows)을 기반으로,
근무 시간이 15시간 이상인지 여부에 따라 공제 비율 결정
주 15시간 이상 -> 4대보험 : 9% 공제
주 15시간 미만 -> 삼쩜삼 : 3.3% 공제 """


def calculate_tax_deduction(total_pay: int, weekly_rows: list[dict]) -> int:
    """
    총 급여와 주간 근무 내역을 기반으로 세금 공제 금액을 계산
    """
    total_hours = get_weekly_hours(weekly_rows)
    
    if total_hours >= 15:
        # 4대보험 공제: 9%
        return int(total_pay * 0.09)
    else:
        # 삼쩜삼 공제: 3.3%
        return int(total_pay * 0.033)
    



#step6. 총 급여 계산

"""코드 요약:
총 급여 계산 함수 (calculate_final_pay)
개별 근무 row 하나와 해당 주 전체 근무 리스트를 받아서:

기본급, 야간수당, 연장수당, 공휴일수당 → 전부 합산 (gross)
calculate_tax_deduction()으로 세금 계산
실지급액 (net) = 총합 - 세금
모든 항목을 dict 형태로 반환"""

def calculate_final_pay(row: dict, weekly_rows: list[dict]) -> dict:
    base = calculate_base_pay_from_row(row)
    night = calculate_night_pay(row)
    overtime = calculate_overtime_pay(row)
    holiday = calculate_holiday_pay(row)  # 👈 이 줄 추가

    gross = base + night + overtime + holiday
    tax = calculate_tax_deduction(gross, weekly_rows)
    net = gross - tax

    return {
        "base": base,
        "night": night,
        "overtime": overtime,
        "holiday": holiday,  
        "gross": gross,
        "tax": tax,
        "net": net
    }



#step6. 총 급여 계산 테스트

"""코드 요약:
calculate_final_pay() 함수의 종합 테스트 코드
테스트 대상은 야간 + 연장 + 주휴 조건을 모두 만족하는 예제"""

row = {
    "startTime": "20:00",
    "endTime": "04:00",
    "payInfo": {
        "hourPrice": 11000,
        "night": True,
        "overtime": True,
        "wHoliday": True
    }
}

weekly_rows = [row] * 3  # 주 24시간 근무로 가정

result = calculate_final_pay(row, weekly_rows)
print(result)








#step7. import

"""코드 요약:
다음 스텝을 위한 라이브러리 임포트 준비 코드

defaultdict → 항목별 자동 초기화된 dict 만들 때 유용 (ex. 사용자별 급여 누적)
calendar → 해당 월의 날짜 수 구할 때 필요 (예: 말일 계산, 주차 계산 등)"""

from collections import defaultdict
import calendar


#step 8. 유틸 함수

"""코드 요약:
이건 급여 계산을 위한 주 단위 그룹화 유틸 함수

group_entries_by_week(entries)
→ 각 entry의 "date" 값을 기준으로 YYYY-WW 형식(연도-주차)으로 그룹화
→ 결과는 딕셔너리 형태"""

def group_entries_by_week(entries: list[dict]) -> dict:
    """
    entries를 'YYYY-WW' 형식으로 주 단위로 그룹화
    """
    weekly = defaultdict(list)
    for entry in entries:
        date_str = entry.get("date")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year_week = date_obj.strftime("%Y-%W")  # ISO 주차: 연도-주차
        weekly[year_week].append(entry)
    return dict(weekly)




#step9. 최종 함수(본계산)

"""코드 요약:
급여 시스템의 마지막 마스터 함수 calculate_monthly_pay(entries)
→ 한 달치 entries를 받아서:

주 단위로 그룹화 (group_entries_by_week)
각 주별로:
주휴수당 먼저 계산해서 누적
하루 단위 총 급여 계산 (기본급 + 수당들 + 세금공제)
마지막에 전체 누적 결과를 정리해서 dict로 반환"""

def calculate_monthly_pay(entries: list[dict]) -> dict:
    """
    한 달치 entries를 받아서
    - 일별 급여 계산
    - 주단위 주휴수당 계산
    - 총합 계산
    """
    total_base = 0
    total_night = 0
    total_overtime = 0
    total_holiday = 0
    total_tax = 0
    total_net = 0
    total_weekly_allowance = 0

    weekly_groups = group_entries_by_week(entries)

    for week_id, weekly_rows in weekly_groups.items():
        # 주휴수당 먼저 계산
        weekly_allowance = calculate_weekly_allowance(weekly_rows)
        total_weekly_allowance += weekly_allowance

        for row in weekly_rows:
            result = calculate_final_pay(row, weekly_rows)  # 하루치 + 세금
            total_base += result["base"]
            total_night += result["night"]
            total_overtime += result["overtime"]
            total_holiday += result["holiday"]
            total_tax += result["tax"]
            total_net += result["net"]

    return {
        "total_base": total_base,
        "total_night": total_night,
        "total_overtime": total_overtime,
        "total_holiday": total_holiday,
        "total_weekly_allowance": total_weekly_allowance,
        "total_tax": total_tax,
        "gross_with_allowance": total_base + total_night + total_overtime + total_holiday + total_weekly_allowance,
        "net_with_allowance": total_net + total_weekly_allowance
    }




#step9. 예시

"""코드 요약:
calculate_monthly_pay() 함수의 실전 적용 예시
Supabase에서 받아온 i_Schedule.entries 데이터를 바탕으로 월급을 실제로 계산하는 흐름

entries: 개인 근무 데이터 (더미로 가정)
각 row에는 "date", "startTime", "endTime", "payInfo" 포함"""

from supabase import create_client

# supabase에서 개인 i_Schedule.entries 가져왔다고 가정
#우선은 entries 더미 데이터
entries = [
    {
        "date": "2025-05-06",
        "startTime": "09:00",
        "endTime": "17:00",
        "payInfo": {
            "hourPrice": 11000,
            "wHoliday": True,
            "Holiday": False,
            "overtime": True,
            "night": False,
            "duty": "4대보험"
        }
    },
    {
        "date": "2025-05-07",
        "startTime": "10:00",
        "endTime": "14:00",
        "payInfo": {
            "hourPrice": 11000,
            "wHoliday": True,
            "Holiday": False,
            "overtime": False,
            "night": False,
            "duty": "4대보험"
        }
    },
    # 원하는 만큼 추가 가능
]
  # i_Entry dict 리스트

monthly_result = calculate_monthly_pay(entries)
print("월 실수령액:", monthly_result["net_with_allowance"])




#step10. 세금 없이 하루치 급여를 계산하는 함수(프리뷰)

"""코드 요약:
이 함수 calculate_final_pay_preview(row)는
세금 없이, 하루치 급여만 미리보기용으로 계산하는 함수"""

def calculate_final_pay_preview(row: dict) -> dict:
    base = calculate_base_pay_from_row(row)
    night = calculate_night_pay(row)
    overtime = calculate_overtime_pay(row)
    holiday = calculate_holiday_pay(row)
    net = base + night + overtime + holiday

    return {
        "base": base,
        "night": night,
        "overtime": overtime,
        "holiday": holiday,
        "net": net
    }


#step10. 사용 예시

"""코드 요약:
이건 calculate_final_pay_preview(row) 함수의 사용 예시
하루치 row 데이터를 기반으로, 세금 없이 수당까지 합산된 실지급 예상액(net)을 출력"""

preview = calculate_final_pay_preview(row)
print(preview["net"])  # 미리보기용 실수령액




#step11. 날짜 범위로 i_entry 불러오는 함수 정의

"""코드 요약:
이 함수 get_entries_for_date_range(start_date, end_date)는
Supabase에서 특정 날짜 범위(start_date ~ end_date)에 해당하는 i_entry 테이블 데이터를 불러오는 함수"""

def get_entries_for_date_range(start_date: str, end_date: str) -> list[dict]:
    """
    Supabase에서 특정 날짜 범위(start_date ~ end_date)의 i_entry 데이터를 가져옴
    payInfo는 JSON 형태로 포함되어 있다고 가정함
    """
    response = (
        supabase.table("i_entry")
        .select("*")  # payInfo는 별도 join이 아니라 내부 JSON
        .gte("date", start_date)
        .lte("date", end_date)
        .execute()
    )
    return response.data




#step13. 선택한 날짜들의 급여를 모두 계산하는 함수
#→ 모드에 따라 정식 월급 계산(standard) 또는 미리보기(preview)로 나뉨

"""코드 요약:
이 함수 calculate_custom_pay(entries, mode="standard")는
사용자가 선택한 여러 날짜의 i_entry들을 받아서:

주 단위로 그룹화한 뒤
mode에 따라:
"standard"면: 세금, 주휴수당 포함 정식 급여 계산
"preview"면: 세금 없이 미리보기 계산
항목별 합산 후 최종 dict로 반환"""

def calculate_custom_pay(entries: list[dict], mode: str = "standard") -> dict:
    grouped = group_entries_by_week(entries)
    total_base = total_night = total_overtime = total_holiday = total_tax = total_net = 0
    total_weekly_allowance = 0

    for week_id, weekly_rows in grouped.items():
        if mode == "standard":
            weekly_allowance = calculate_weekly_allowance(weekly_rows)
            total_weekly_allowance += weekly_allowance
        else:
            weekly_allowance = 0

        for row in weekly_rows:
            if mode == "standard":
                result = calculate_final_pay(row, weekly_rows)
            elif mode == "preview":
                result = calculate_final_pay_preview(row)
            else:
                raise ValueError("Invalid mode")

            total_base += result["base"]
            total_night += result["night"]
            total_overtime += result["overtime"]
            total_holiday += result["holiday"]
            total_tax += result.get("tax", 0)
            total_net += result["net"]

    return {
        "base": total_base,
        "night": total_night,
        "overtime": total_overtime,
        "holiday": total_holiday,
        "weekly_allowance": total_weekly_allowance,
        "tax": total_tax,
        "gross_with_allowance": total_base + total_night + total_overtime + total_holiday + total_weekly_allowance,
        "net_with_allowance": total_net + total_weekly_allowance
    }



#step12. 급여 계산 함수 (우리가 만든 것 사용)

"""코드 요약:
이건 우리가 만든 급여 시스템을 실제로 호출하는 최종 통합 사용 예시"""

# 이미 정의한 함수라고 가정
result = calculate_custom_pay(
    get_entries_for_date_range("2025-05-01", "2025-05-31"),
    mode="standard"
)
print("💰 5월 실수령액:", result["net_with_allowance"])



#step13. 사용 예시

"""사용 예시 요약 (완전체 테스트)

이 예시는 우리가 만든 calculate_custom_pay() 함수를 두 가지 시나리오에서 실전처럼 테스트"""

# 1. 세금 포함된 5월 월급 계산
# Supabase에서 2025년 5월 근무한 i_entry 데이터 전부 가져옴
entries = get_entries_for_date_range("2025-05-01", "2025-05-31")

# "standard" 모드로 급여 계산 (세금·주휴수당 모두 포함)
result = calculate_custom_pay(entries, mode="standard")

# 결과 출력
print("🪙 5월 실수령액:", result["net_with_allowance"])
print(result)  # 전체 세부 급여 breakdown 확인용

# 2. 사용자가 날짜 3개만 선택했을 때 미리보기 (세금 X)
# Supabase에서 전체 데이터를 가져온 후, 앞에서 3개만 선택해 예시 테스트
# 실제 프론트에서는 사용자가 선택한 날만 추려서 넘겨줄 수 있음
selected_entries = entries[:3]  # 혹은 사용자가 고른 날짜에 해당하는 entry만 추출

# "preview" 모드로 계산 (세금 미포함, 주휴수당은 포함)
preview_result = calculate_custom_pay(selected_entries, mode="preview")

# 미리보기 결과 출력
print("👀 미리보기 결과 (3일치):", preview_result["net_with_allowance"])
print(preview_result)



