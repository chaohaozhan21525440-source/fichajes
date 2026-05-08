from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class NfcTokenCreate(BaseModel):
    nfc_uid: str


class NfcTokenRead(BaseModel):
    id: UUID
    nfc_uid: str
    worker_id: UUID
    is_active: bool
    assigned_at: datetime

    model_config = {"from_attributes": True}
