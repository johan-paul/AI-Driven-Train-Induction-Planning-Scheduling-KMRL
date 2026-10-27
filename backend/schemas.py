# backend/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class TrainSnapshotIn(BaseModel):
    train_id: str
    cert_rolling: Optional[datetime] = None
    cert_signalling: Optional[datetime] = None
    cert_telecom: Optional[datetime] = None
    jobcard_severity: Optional[int] = 0
    pred_fail: Optional[float] = 0.0
    branding_req_hours: Optional[int] = 0
    branding_done: Optional[int] = 0
    odometer_km: Optional[int] = 0
    last_clean_days: Optional[int] = 0
    stabling_index: Optional[int] = 0
    vibration: Optional[float] = 0.0
    temp: Optional[float] = 0.0
    humidity: Optional[float] = 0.0
    manual_blocked: Optional[bool] = False

class RunInductionRequest(BaseModel):
    service_count: int = 8
    lambda_risk: float = 1.5
    use_ml: bool = True
    forced_failed_ids: Optional[List[str]] = []
    branding_hours_budget: Optional[int] = None

class InductionResponse(BaseModel):
    summary: Any
    results: List[Any]
