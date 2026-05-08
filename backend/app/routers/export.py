import csv
import io
from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.checkin_record import CheckinRecord
from app.models.worker import Worker
from app.auth.dependencies import get_current_admin
from app.models.admin import Admin

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("/checkins.csv")
def export_checkins_csv(
    worker_id: Optional[UUID] = Query(None),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
):
    q = (
        db.query(CheckinRecord, Worker)
        .join(Worker, CheckinRecord.worker_id == Worker.id)
    )

    if worker_id:
        q = q.filter(CheckinRecord.worker_id == worker_id)
    if from_date:
        q = q.filter(CheckinRecord.recorded_at >= from_date)
    if to_date:
        q = q.filter(CheckinRecord.recorded_at <= to_date)
    if event_type:
        q = q.filter(CheckinRecord.event_type == event_type)

    rows = q.order_by(CheckinRecord.recorded_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["worker_name", "employee_id", "event_type", "recorded_at", "device_id"])
    for record, worker in rows:
        writer.writerow([
            worker.full_name,
            worker.employee_id,
            record.event_type,
            record.recorded_at.isoformat(),
            record.device_id,
        ])

    # UTF-8 BOM para compatibilidad con Excel
    content = "﻿" + output.getvalue()

    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=checkins.csv"},
    )
