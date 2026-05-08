from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class FailedAttemptRead(BaseModel):
    id: UUID
    nfc_uid: str
    device_id: str
    attempted_at: datetime

    model_config = {"from_attributes": True}
