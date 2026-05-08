import uuid
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CheckinRecord(Base):
    __tablename__ = "checkin_records"
    __table_args__ = (
        CheckConstraint("event_type IN ('entrada', 'salida')", name="ck_checkin_event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    nfc_uid: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(10), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    synced_from_local: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    worker = relationship("Worker", back_populates="checkin_records")
