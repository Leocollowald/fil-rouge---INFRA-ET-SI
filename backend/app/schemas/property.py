import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.property import PropertyStatus, PropertyType, TransactionType


class PropertyCreate(BaseModel):
    title: str
    description: str | None = None
    price: float
    surface: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    property_type: PropertyType
    transaction_type: TransactionType
    city: str
    address: str
    zip_code: str
    latitude: float | None = None
    longitude: float | None = None
    agency_id: uuid.UUID | None = None

    @field_validator("price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Le prix doit être positif")
        return v


class PropertyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    surface: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    status: PropertyStatus | None = None
    city: str | None = None
    address: str | None = None
    zip_code: str | None = None


class PropertyImageResponse(BaseModel):
    id: uuid.UUID
    url: str
    is_primary: bool

    model_config = {"from_attributes": True}


class AgencyInProperty(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    address: str
    phone: str | None
    email: str | None

    model_config = {"from_attributes": True}


class AgentInProperty(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    phone: str | None
    email: str

    model_config = {"from_attributes": True}


class PropertyResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    price: float
    surface: float | None
    rooms: int | None
    bedrooms: int | None
    bathrooms: int | None
    property_type: PropertyType
    status: PropertyStatus
    transaction_type: TransactionType
    city: str
    address: str
    zip_code: str
    latitude: float | None
    longitude: float | None
    agency_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    agency: AgencyInProperty | None = None
    agent: AgentInProperty | None = None
    images: list[PropertyImageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyFilters(BaseModel):
    city: str | None = None
    property_type: PropertyType | None = None
    transaction_type: TransactionType | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_surface: float | None = None
    rooms: int | None = None
    status: PropertyStatus | None = PropertyStatus.available
    page: int = 1
    per_page: int = 12
