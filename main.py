from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from utils.calculator import calculate_custom_pay, get_entries_for_date_range
from utils.manual_calculator import calculate_manual_pay  # 🔹 수동 계산 함수 import
from schemas import ManualPayInput  # 🔹 Pydantic 모델 import

app = FastAPI()

# 🔸 CORS 설정 (모든 origin 허용 예시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 또는 ["http://localhost:3000"] 등으로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기본 루트 라우터
@app.get("/")
def root():
    return {"message": "Hello, FastAPI!"}

# 급여 계산 API (자동 계산 - GET 방식)
@app.get("/calculate")
def calculate(
    start_date: str = Query(..., description="시작 날짜 (예: 2025-05-01)"),
    end_date: str = Query(..., description="종료 날짜 (예: 2025-05-31)"),
    mode: str = Query("standard", enum=["standard", "preview"], description="계산 모드: standard 또는 preview")
):
    """
    Supabase에서 i_entry 데이터 불러와 급여 계산 후 결과 반환
    """
    entries = get_entries_for_date_range(start_date, end_date)
    result = calculate_custom_pay(entries, mode=mode)
    return result

# 급여 계산 API (수동 계산 - POST 방식)
@app.post("/manual-calculate")
def manual_calculate(input: ManualPayInput):
    """
    사용자가 직접 입력한 정보에 기반한 수동 급여 계산 API
    """
    result = calculate_manual_pay(input.dict())
    return result





