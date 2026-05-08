from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.ip_lockout import IpLockout

MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def is_ip_locked(db: Session, ip: str) -> bool:
    record = db.get(IpLockout, ip)
    if not record or not record.locked_until:
        return False
    if datetime.now(timezone.utc) < record.locked_until.replace(tzinfo=timezone.utc):
        return True
    # Bloqueo expirado — resetear
    record.locked_until = None
    record.failed_attempts = 0
    db.commit()
    return False


def record_failed_attempt(db: Session, ip: str) -> None:
    now = datetime.now(timezone.utc)
    record = db.get(IpLockout, ip)
    if not record:
        record = IpLockout(ip_address=ip, failed_attempts=1, last_attempt_at=now)
        db.add(record)
    else:
        record.failed_attempts += 1
        record.last_attempt_at = now
        if record.failed_attempts >= MAX_ATTEMPTS:
            record.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
    db.commit()


def reset_failed_attempts(db: Session, ip: str) -> None:
    record = db.get(IpLockout, ip)
    if record:
        record.failed_attempts = 0
        record.locked_until = None
        db.commit()
