import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.transaction import TransactionStatus


class TransactionCreate(BaseModel):
    property_id: uuid.UUID
    offered_price: float
    notes: str | None = None

    @field_validator("offered_price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Le prix proposé doit être positif")
        return v


class TransactionUpdate(BaseModel):
    status: TransactionStatus
    notes: str | None = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    buyer_id: uuid.UUID
    agent_id: uuid.UUID | None
    offered_price: float
    status: TransactionStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
