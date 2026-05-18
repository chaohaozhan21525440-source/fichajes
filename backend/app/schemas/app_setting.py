from typing import Optional
from pydantic import BaseModel, Field, field_validator


# Defaults usados cuando la fila no existe todavía en DB.
DEFAULT_ENTRY = "09:00"
DEFAULT_EXIT = "18:00"
DEFAULT_GRACE = 5


def _validate_hhmm(v: str) -> str:
    try:
        h, m = v.split(":")
        hh, mm = int(h), int(m)
        if not (0 <= hh < 24 and 0 <= mm < 60):
            raise ValueError
        return f"{hh:02d}:{mm:02d}"
    except (ValueError, AttributeError):
        raise ValueError(f"Formato HH:MM esperado, recibido '{v}'")


class AppSettingsRead(BaseModel):
    expected_entry_time: str = DEFAULT_ENTRY
    expected_exit_time: str = DEFAULT_EXIT
    grace_minutes: int = DEFAULT_GRACE


class AppSettingsUpdate(BaseModel):
    """PATCH parcial — solo se actualizan los campos enviados."""

    expected_entry_time: Optional[str] = None
    expected_exit_time: Optional[str] = None
    grace_minutes: Optional[int] = Field(None, ge=0, le=240)

    @field_validator("expected_entry_time", "expected_exit_time")
    @classmethod
    def _check_hhmm(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_hhmm(v)
