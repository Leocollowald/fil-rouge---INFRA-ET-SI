import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class AgencyResponse(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    address: str
    zip_code: str
    phone: str | None
    email: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
