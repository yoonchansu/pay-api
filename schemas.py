from pydantic import BaseModel
from typing import List, Literal

class ManualPayInput(BaseModel):
    payType: Literal["시급", "일급", "월급"]
    payAmount: int

    workHour: int
    workMinute: int
    workingDays: List[str]  # 예: ["월", "화", "수"]

    overtimeHour: int
    overtimeMinute: int

    includeWeeklyAllowance: bool
    taxOption: Literal["none", "insurance", "income"]
    nightWork: bool
