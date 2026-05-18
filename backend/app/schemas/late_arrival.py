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


class AbsenceItem(BaseModel):
    """Día pasado en el que un trabajador activo NO tiene ninguna entrada."""
    date: date
    worker_id: UUID
    worker_name: str
    employee_id: str


class AbsenceWorkerSummary(BaseModel):
    worker_id: UUID
    worker_name: str
    employee_id: str
    absence_count: int


class PendingTodayItem(BaseModel):
    """Trabajador activo que hoy aún no ha fichado (no es falta — solo pendiente)."""
    worker_id: UUID
    worker_name: str
    employee_id: str


class LateArrivalSummary(BaseModel):
    total_late_events: int
    total_late_minutes: int
    workers_affected: int
    total_absences: int
    pending_today_count: int


class LateArrivalsReport(BaseModel):
    expected_time: str        # eco del parámetro pedido (HH:MM)
    grace_minutes: int
    tz: str
    items: list[LateArrivalItem]
    by_worker: list[LateArrivalWorkerSummary]
    # Faltas: días pasados sin entrada (active workers solamente)
    absences: list[AbsenceItem]
    absences_by_worker: list[AbsenceWorkerSummary]
    # Pendientes hoy: aún pueden fichar
    pending_today: list[PendingTodayItem]
    summary: LateArrivalSummary
