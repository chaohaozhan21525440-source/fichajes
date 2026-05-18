"""Endpoints para leer/actualizar la configuración mutable del cliente
(horario esperado de entrada, salida, tolerancia). Solo admins.

Diseño key-value para evitar migraciones cuando añadamos settings nuevos.
La lectura siempre devuelve todos los settings con sus defaults aplicados.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.models.admin import Admin
from app.models.app_setting import AppSetting
from app.schemas.app_setting import (
    DEFAULT_ENTRY,
    DEFAULT_EXIT,
    DEFAULT_GRACE,
    AppSettingsRead,
    AppSettingsUpdate,
)


router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _load_all(db: Session) -> dict[str, str]:
    """Carga todas las filas de app_settings en un dict {key: value}."""
    return {row.key: row.value for row in db.query(AppSetting).all()}


def _upsert(db: Session, key: str, value: str) -> None:
    existing = db.get(AppSetting, key)
    if existing:
        existing.value = value
    else:
        db.add(AppSetting(key=key, value=value))


def read_settings_dict(db: Session) -> AppSettingsRead:
    """Helper interno reutilizable (también lo usa reports.py)."""
    raw = _load_all(db)
    try:
        grace = int(raw.get("grace_minutes", DEFAULT_GRACE))
    except (TypeError, ValueError):
        grace = DEFAULT_GRACE
    return AppSettingsRead(
        expected_entry_time=raw.get("expected_entry_time", DEFAULT_ENTRY),
        expected_exit_time=raw.get("expected_exit_time", DEFAULT_EXIT),
        grace_minutes=grace,
    )


@router.get("", response_model=AppSettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
):
    return read_settings_dict(db)


@router.patch("", response_model=AppSettingsRead)
def update_settings(
    body: AppSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
):
    if body.expected_entry_time is not None:
        _upsert(db, "expected_entry_time", body.expected_entry_time)
    if body.expected_exit_time is not None:
        _upsert(db, "expected_exit_time", body.expected_exit_time)
    if body.grace_minutes is not None:
        _upsert(db, "grace_minutes", str(body.grace_minutes))
    db.commit()
    return read_settings_dict(db)
