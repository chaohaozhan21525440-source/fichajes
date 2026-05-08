from uuid import UUID
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def log_audit(
    db: Session,
    admin_id: UUID,
    operation: str,
    entity_type: str,
    entity_id: UUID | None = None,
    details: dict | None = None,
) -> None:
    """Añade una entrada al log de auditoría en la sesión actual (sin commit)."""
    entry = AuditLog(
        admin_id=admin_id,
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
