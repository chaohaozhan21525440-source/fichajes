from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: UUID
    admin_id: UUID
    operation: str
    entity_type: str
    entity_id: Optional[UUID]
    details: Optional[dict]
    performed_at: datetime

    model_config = {"from_attributes": True}
