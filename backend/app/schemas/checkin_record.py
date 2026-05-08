from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel


class CheckinRequest(BaseModel):
    nfc_uid: str
    device_id: str
    detected_at: datetime
    idempotency_key: UUID


class CheckinResponse(BaseModel):
    event_type: Literal["entrada", "salida"]
    worker_name: str
    recorded_at: datetime


class CheckinRead(BaseModel):
    id: UUID
    worker_id: UUID
    worker_name: str
    nfc_uid: str
    event_type: Literal["entrada", "salida"]
    recorded_at: datetime
    device_id: str
    synced_from_local: bool

    model_config = {"from_attributes": True}


class CheckinsPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[CheckinRead]


class SyncRecord(BaseModel):
    nfc_uid: str
    device_id: str
    detected_at: datetime
    idempotency_key: UUID


class SyncRequest(BaseModel):
    records: list[SyncRecord]


class SyncResponse(BaseModel):
    procesados: int
    rechazados: int
