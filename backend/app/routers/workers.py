from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.worker import Worker
from app.models.nfc_token import NfcToken
from app.schemas.worker import WorkerCreate, WorkerUpdate, WorkerRead
from app.schemas.nfc_token import NfcTokenCreate, NfcTokenRead
from app.auth.dependencies import get_current_admin
from app.models.admin import Admin
from app.services.audit import log_audit

router = APIRouter(prefix="/api/v1/workers", tags=["workers"])


@router.get("", response_model=list[WorkerRead])
def list_workers(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
):
    return db.query(Worker).all()


@router.post("", response_model=WorkerRead, status_code=status.HTTP_201_CREATED)
def create_worker(
    body: WorkerCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    if db.query(Worker).filter(Worker.employee_id == body.employee_id).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "employee_id_duplicado", "message": "El employee_id ya existe"},
        )

    if db.query(NfcToken).filter(NfcToken.nfc_uid == body.nfc_uid, NfcToken.is_active == True).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "token_ya_asignado", "message": "El token NFC ya está asignado a otro trabajador activo"},
        )

    worker = Worker(full_name=body.full_name, employee_id=body.employee_id)
    db.add(worker)
    db.flush()

    token = NfcToken(nfc_uid=body.nfc_uid, worker_id=worker.id)
    db.add(token)

    log_audit(db, admin.id, "worker.create", "worker", worker.id, {
        "full_name": body.full_name,
        "employee_id": body.employee_id,
        "nfc_uid": body.nfc_uid,
    })
    db.commit()
    db.refresh(worker)
    return worker


@router.put("/{worker_id}", response_model=WorkerRead)
def update_worker(
    worker_id: UUID,
    body: WorkerUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "worker_no_encontrado", "message": "Trabajador no encontrado"},
        )

    changes: dict = {}
    if body.full_name is not None:
        worker.full_name = body.full_name
        changes["full_name"] = body.full_name
    if body.employee_id is not None:
        if db.query(Worker).filter(Worker.employee_id == body.employee_id, Worker.id != worker_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "employee_id_duplicado", "message": "El employee_id ya existe"},
            )
        worker.employee_id = body.employee_id
        changes["employee_id"] = body.employee_id

    log_audit(db, admin.id, "worker.update", "worker", worker.id, changes)
    db.commit()
    db.refresh(worker)
    return worker


@router.patch("/{worker_id}/deactivate", response_model=WorkerRead)
def deactivate_worker(
    worker_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "worker_no_encontrado", "message": "Trabajador no encontrado"},
        )
    if not worker.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "worker_ya_inactivo", "message": "El trabajador ya está desactivado"},
        )

    worker.is_active = False
    for t in worker.nfc_tokens:
        t.is_active = False

    log_audit(db, admin.id, "worker.deactivate", "worker", worker.id, {"full_name": worker.full_name})
    db.commit()
    db.refresh(worker)
    return worker


@router.post("/{worker_id}/nfc-tokens", response_model=NfcTokenRead, status_code=status.HTTP_201_CREATED)
def assign_nfc_token(
    worker_id: UUID,
    body: NfcTokenCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "worker_no_encontrado", "message": "Trabajador no encontrado"},
        )
    if not worker.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "worker_inactivo", "message": "No se puede asignar token a un trabajador inactivo"},
        )

    if db.query(NfcToken).filter(NfcToken.nfc_uid == body.nfc_uid, NfcToken.is_active == True).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "token_ya_asignado", "message": "El token NFC ya está asignado a otro trabajador activo"},
        )

    token = NfcToken(nfc_uid=body.nfc_uid, worker_id=worker_id)
    db.add(token)

    log_audit(db, admin.id, "worker.assign_token", "nfc_token", worker.id, {"nfc_uid": body.nfc_uid})
    db.commit()
    db.refresh(token)
    return token
