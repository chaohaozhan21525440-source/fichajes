"""
Informes derivados de los fichajes (solo lectura).

Cálculo on-the-fly sobre CheckinRecord existente. No modifica nada en DB,
no añade tablas/migraciones — pensado para ser seguro de desplegar sin
arriesgar el flujo de fichaje en producción.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.models.admin import Admin
from app.models.checkin_record import CheckinRecord
from app.models.worker import Worker
from app.routers.settings import read_settings_dict
from app.schemas.late_arrival import (
    LateArrivalItem,
    LateArrivalSummary,
    LateArrivalWorkerSummary,
    LateArrivalsReport,
)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _parse_hhmm(s: str) -> time:
    try:
        h, m = s.split(":")
        hh, mm = int(h), int(m)
        if not (0 <= hh < 24 and 0 <= mm < 60):
            raise ValueError
        return time(hh, mm)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_expected_time", "message": f"Formato HH:MM esperado, recibido '{s}'"},
        )


@router.get("/late-arrivals", response_model=LateArrivalsReport)
def late_arrivals_report(
    from_date: date = Query(..., alias="from", description="Inicio del rango (inclusive, fecha local)"),
    to_date: date = Query(..., alias="to", description="Fin del rango (inclusive, fecha local)"),
    expected_time: Optional[str] = Query(None, description="Hora esperada HH:MM (default: app_settings.expected_entry_time)"),
    grace_minutes: Optional[int] = Query(None, ge=0, le=240, description="Tolerancia (default: app_settings.grace_minutes)"),
    worker_id: Optional[UUID] = Query(None, description="Filtrar a un solo trabajador"),
    tz: str = Query("Europe/Madrid", description="IANA timezone, por defecto Europa/Madrid"),
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
):
    """
    Devuelve, para el rango [from, to] en TZ local, los retrasos detectados:

    Algoritmo:
      1) Toma todas las `entrada` del rango (acotado por UTC con margen DST).
      2) Agrupa por (fecha local, trabajador) y se queda con la PRIMERA del día.
      3) Compara la hora local de esa primera entrada contra
         `expected_time + grace_minutes`. Si la sobrepasa → es tarde.
      4) `late_minutes` se calcula contra `expected_time` (no contra el threshold)
         para que el informe muestre el retraso real, no el retraso por encima de
         la tolerancia.

    Si un trabajador no tiene `entrada` ese día, no aparece (eso es ausencia,
    no retraso — fuera de scope del informe).
    """
    if to_date < from_date:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_range", "message": "'to' debe ser >= 'from'"},
        )

    # Si el caller no manda expected_time / grace_minutes, leer defaults persistidos
    # desde app_settings — así la página puede llamar al endpoint "limpio" y el
    # cliente lo configura una vez desde Settings.
    persisted = read_settings_dict(db)
    if expected_time is None:
        expected_time = persisted.expected_entry_time
    if grace_minutes is None:
        grace_minutes = persisted.grace_minutes

    expected = _parse_hhmm(expected_time)
    try:
        zone = ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_tz", "message": f"Timezone IANA no encontrada: '{tz}'"},
        )

    # Acoto la query SQL por UTC. Uso 00:00 local del primer día hasta 00:00 local
    # del día siguiente al último → cubre todo el rango aun con cambio horario.
    start_local = datetime.combine(from_date, time.min).replace(tzinfo=zone)
    end_local = datetime.combine(to_date + timedelta(days=1), time.min).replace(tzinfo=zone)

    q = (
        db.query(CheckinRecord, Worker)
        .join(Worker, CheckinRecord.worker_id == Worker.id)
        .filter(CheckinRecord.event_type == "entrada")
        .filter(CheckinRecord.recorded_at >= start_local)
        .filter(CheckinRecord.recorded_at < end_local)
    )
    if worker_id is not None:
        q = q.filter(CheckinRecord.worker_id == worker_id)

    rows = q.all()

    # Agrupar por (fecha local, worker_id) → quedarse con MIN(recorded_at).
    # Hago el group-by en Python en vez de SQL para no atarme al dialecto
    # (la TZ-aware aggregation cambia entre SQLite/Postgres) y mantenerlo simple.
    first_entries: dict[tuple[date, UUID], tuple[CheckinRecord, Worker]] = {}
    for record, worker in rows:
        local_dt = record.recorded_at.astimezone(zone)
        key = (local_dt.date(), worker.id)
        prev = first_entries.get(key)
        if prev is None or record.recorded_at < prev[0].recorded_at:
            first_entries[key] = (record, worker)

    items: list[LateArrivalItem] = []
    by_worker_agg: dict[UUID, dict] = {}

    for (local_date, _), (record, worker) in first_entries.items():
        local_dt = record.recorded_at.astimezone(zone)
        expected_dt = datetime.combine(local_date, expected).replace(tzinfo=zone)
        threshold_dt = expected_dt + timedelta(minutes=grace_minutes)

        if local_dt > threshold_dt:
            # Minutos reales de retraso contra expected_time (no contra threshold),
            # truncado a entero hacia abajo.
            late_min = int((local_dt - expected_dt).total_seconds() // 60)

            items.append(
                LateArrivalItem(
                    date=local_date,
                    worker_id=worker.id,
                    worker_name=worker.full_name,
                    employee_id=worker.employee_id,
                    first_entry_at=record.recorded_at,
                    local_time=local_dt.time().replace(microsecond=0).isoformat(),
                    late_minutes=late_min,
                )
            )
            agg = by_worker_agg.setdefault(
                worker.id,
                {
                    "worker_id": worker.id,
                    "worker_name": worker.full_name,
                    "employee_id": worker.employee_id,
                    "late_count": 0,
                    "total_late_minutes": 0,
                },
            )
            agg["late_count"] += 1
            agg["total_late_minutes"] += late_min

    # Items: más recientes primero (mismo criterio que /checkins)
    items.sort(key=lambda x: x.first_entry_at, reverse=True)

    by_worker = [LateArrivalWorkerSummary(**v) for v in by_worker_agg.values()]
    by_worker.sort(key=lambda w: w.total_late_minutes, reverse=True)

    summary = LateArrivalSummary(
        total_late_events=len(items),
        total_late_minutes=sum(item.late_minutes for item in items),
        workers_affected=len(by_worker_agg),
    )

    return LateArrivalsReport(
        expected_time=expected_time,
        grace_minutes=grace_minutes,
        tz=tz,
        items=items,
        by_worker=by_worker,
        summary=summary,
    )
