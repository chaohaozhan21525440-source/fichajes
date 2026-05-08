from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogRead
from app.auth.dependencies import get_current_admin
from app.models.admin import Admin

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit(
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    admin_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
):
    q = db.query(AuditLog)

    if admin_id:
        q = q.filter(AuditLog.admin_id == admin_id)
    if from_date:
        q = q.filter(AuditLog.performed_at >= from_date)
    if to_date:
        q = q.filter(AuditLog.performed_at <= to_date)

    return q.order_by(AuditLog.performed_at.desc()).all()
