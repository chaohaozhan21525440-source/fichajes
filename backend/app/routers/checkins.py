from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.nfc_token import NfcToken
from app.models.worker import Worker
from app.models.checkin_record import CheckinRecord
from app.models.failed_attempt import FailedAttempt
from app.schemas.checkin_record import (
    CheckinRequest, CheckinResponse,
    CheckinRead, CheckinsPage,
    SyncRequest, SyncResponse,
)
from app.auth.device import get_device
from app.auth.dependencies import get_current_admin
from app.models.admin import Admin

router = APIRouter(prefix="/api/v1/checkins", tags=["checkins"])


def _last_event_type(db: Session, worker_id: UUID) -> str:
    last = (
        db.query(CheckinRecord)
        .filter(CheckinRecord.worker_id == worker_id)
        .order_by(CheckinRecord.recorded_at.desc())
        .first()
    )
    if last and last.event_type == "entrada":
        return "salida"
    return "entrada"


@router.post("", response_model=CheckinResponse)
def register_checkin(
    body: CheckinRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_device),
):
    # Idempotencia: si ya existe devolver el registro existente
    existing = db.query(CheckinRecord).filter(
        CheckinRecord.idempotency_key == body.idempotency_key
    ).first()
    if existing:
        worker = db.get(Worker, existing.worker_id)
        return CheckinResponse(
            event_type=existing.event_type,
            worker_name=worker.full_name,
            recorded_at=existing.recorded_at,
        )

    # Buscar token NFC activo
    token = db.query(NfcToken).filter(
        NfcToken.nfc_uid == body.nfc_uid,
        NfcToken.is_active == True,
    ).first()

    if not token:
        db.add(FailedAttempt(nfc_uid=body.nfc_uid, device_id=body.device_id))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "token_desconocido", "nfc_uid": body.nfc_uid},
        )

    worker = db.get(Worker, token.worker_id)
    if not worker or not worker.is_active:
        db.add(FailedAttempt(nfc_uid=body.nfc_uid, device_id=body.device_id))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "worker_inactivo", "message": "El trabajador está desactivado"},
        )

    event_type = _last_event_type(db, worker.id)

    record = CheckinRecord(
        worker_id=worker.id,
        nfc_uid=body.nfc_uid,
        event_type=event_type,
        recorded_at=body.detected_at,
        device_id=body.device_id,
        idempotency_key=body.idempotency_key,
        synced_from_local=False,
    )
    db.add(record)
    db.commit()

    return CheckinResponse(
        event_type=event_type,
        worker_name=worker.full_name,
        recorded_at=record.recorded_at,
    )


@router.post("/sync", response_model=SyncResponse)
def sync_checkins(
    body: SyncRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_device),
):
    procesados = 0
    rechazados = 0

    # Ordenar por detected_at para respetar la secuencia de fichajes
    records_sorted = sorted(body.records, key=lambda r: r.detected_at)

    for rec in records_sorted:
        # Idempotencia: saltar duplicados
        if db.query(CheckinRecord).filter(
            CheckinRecord.idempotency_key == rec.idempotency_key
        ).first():
            rechazados += 1
            continue

        token = db.query(NfcToken).filter(
            NfcToken.nfc_uid == rec.nfc_uid,
            NfcToken.is_active == True,
        ).first()

        if not token:
            db.add(FailedAttempt(nfc_uid=rec.nfc_uid, device_id=rec.device_id))
            rechazados += 1
            continue

        worker = db.get(Worker, token.worker_id)
        if not worker or not worker.is_active:
            rechazados += 1
            continue

        event_type = _last_event_type(db, worker.id)

        db.add(CheckinRecord(
            worker_id=worker.id,
            nfc_uid=rec.nfc_uid,
            event_type=event_type,
            recorded_at=rec.detected_at,
            device_id=rec.device_id,
            idempotency_key=rec.idempotency_key,
            synced_from_local=True,
        ))
        procesados += 1

    db.commit()
    return SyncResponse(procesados=procesados, rechazados=rechazados)


@router.get("", response_model=CheckinsPage)
def list_checkins(
    worker_id: Optional[UUID] = Query(None),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    event_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
):
    q = db.query(CheckinRecord).options(joinedload(CheckinRecord.worker))

    if worker_id:
        q = q.filter(CheckinRecord.worker_id == worker_id)
    if from_date:
        q = q.filter(CheckinRecord.recorded_at >= from_date)
    if to_date:
        q = q.filter(CheckinRecord.recorded_at <= to_date)
    if event_type:
        q = q.filter(CheckinRecord.event_type == event_type)

    total = q.count()
    records = q.order_by(CheckinRecord.recorded_at.desc()).offset((page - 1) * size).limit(size).all()

    return CheckinsPage(
        total=total,
        page=page,
        size=size,
        items=[
            CheckinRead(
                id=r.id,
                worker_id=r.worker_id,
                worker_name=r.worker.full_name,
                nfc_uid=r.nfc_uid,
                event_type=r.event_type,
                recorded_at=r.recorded_at,
                device_id=r.device_id,
                synced_from_local=r.synced_from_local,
            )
            for r in records
        ],
    )
