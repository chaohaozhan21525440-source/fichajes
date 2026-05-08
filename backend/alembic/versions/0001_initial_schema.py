"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-25

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("employee_id", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("employee_id", name="uq_workers_employee_id"),
    )

    op.create_table(
        "nfc_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("nfc_uid", sa.String(100), nullable=False),
        sa.Column("worker_id", UUID(as_uuid=True), sa.ForeignKey("workers.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("nfc_uid", name="uq_nfc_tokens_uid"),
    )

    op.create_table(
        "checkin_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("worker_id", UUID(as_uuid=True), sa.ForeignKey("workers.id"), nullable=False),
        sa.Column("nfc_uid", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(10), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("idempotency_key", UUID(as_uuid=True), nullable=False),
        sa.Column("synced_from_local", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("idempotency_key", name="uq_checkin_idempotency_key"),
        sa.CheckConstraint("event_type IN ('entrada', 'salida')", name="ck_checkin_event_type"),
    )

    op.create_table(
        "failed_attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("nfc_uid", sa.String(100), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "admins",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("username", name="uq_admins_username"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("admins.id"), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "ip_lockouts",
        sa.Column("ip_address", sa.String(45), primary_key=True),
        sa.Column("failed_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # Índices de rendimiento
    op.create_index("idx_checkin_worker_recorded", "checkin_records", ["worker_id", sa.text("recorded_at DESC")])
    op.create_index("idx_checkin_recorded", "checkin_records", [sa.text("recorded_at DESC")])
    op.create_index("idx_checkin_event_type", "checkin_records", ["event_type"])
    op.create_index("idx_nfc_tokens_uid", "nfc_tokens", ["nfc_uid"], postgresql_where=sa.text("is_active = TRUE"))
    op.create_index("idx_audit_performed", "audit_log", [sa.text("performed_at DESC")])
    op.create_index("idx_audit_admin", "audit_log", ["admin_id", sa.text("performed_at DESC")])


def downgrade() -> None:
    op.drop_index("idx_audit_admin", table_name="audit_log")
    op.drop_index("idx_audit_performed", table_name="audit_log")
    op.drop_index("idx_nfc_tokens_uid", table_name="nfc_tokens")
    op.drop_index("idx_checkin_event_type", table_name="checkin_records")
    op.drop_index("idx_checkin_recorded", table_name="checkin_records")
    op.drop_index("idx_checkin_worker_recorded", table_name="checkin_records")

    op.drop_table("ip_lockouts")
    op.drop_table("audit_log")
    op.drop_table("admins")
    op.drop_table("failed_attempts")
    op.drop_table("checkin_records")
    op.drop_table("nfc_tokens")
    op.drop_table("workers")
