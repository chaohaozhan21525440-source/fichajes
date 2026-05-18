from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel


class LateArrivalItem(BaseModel):
    date: date                # fecha local (en el tz pedido)
    worker_id: UUID
    worker_name: str
    employee_id: str
    first_entry_at: datetime  # UTC ISO, recorded_at original
    local_time: str           # HH:MM:SS en tz local
    late_minutes: int         # minutos enteros de retraso vs expected_time (sin restar grace)


class LateArrivalWorkerSummary(BaseModel):
    worker_id: UUID
    worker_name: str
    employee_id: str
    late_count: int
    total_late_minutes: int


class LateArrivalSummary(BaseModel):
    total_late_events: int
    total_late_minutes: int
    workers_affected: int


class LateArrivalsReport(BaseModel):
    expected_time: str        # eco del parámetro pedido (HH:MM)
    grace_minutes: int
    tz: str
    items: list[LateArrivalItem]
    by_worker: list[LateArrivalWorkerSummary]
    summary: LateArrivalSummary
