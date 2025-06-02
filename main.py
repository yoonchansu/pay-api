from fastapi import FastAPI, Query
from utils.calculator import calculate_custom_pay, get_entries_for_date_range

app = FastAPI()

# 기본 루트 라우터
@app.get("/")
def root():
    return {"message": "Hello, FastAPI!"}

# 급여 계산 API (GET 방식)
@app.get("/calculate")
def calculate(
    start_date: str = Query(..., description="시작 날짜 (예: 2025-05-01)"),
    end_date: str = Query(..., description="종료 날짜 (예: 2025-05-31)"),
    mode: str = Query("standard", enum=["standard", "preview"], description="계산 모드: standard 또는 preview")
):
    """
    Supabase에서 i_entry 데이터 불러와 급여 계산 후 결과 반환
    - start_date ~ end_date 사이의 데이터를 가져옴
    - mode:
        - "standard": 세금 포함 정식 급여
        - "preview": 세금 없이 미리보기
    """
    entries = get_entries_for_date_range(start_date, end_date)
    result = calculate_custom_pay(entries, mode=mode)
    return result



