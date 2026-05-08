from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class WorkerCreate(BaseModel):
    full_name: str
    employee_id: str
    nfc_uid: str


class WorkerUpdate(BaseModel):
    full_name: str | None = None
    employee_id: str | None = None


class WorkerRead(BaseModel):
    id: UUID
    full_name: str
    employee_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
