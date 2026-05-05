from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_commercial
from app.models.property import PropertyStatus, PropertyType, TransactionType
from app.models.user import User
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyCreate, PropertyFilters, PropertyResponse, PropertyUpdate
from app.services.property_service import PropertyService


router = APIRouter(prefix="/properties", tags=["Biens immobiliers"])


@router.get("/", response_model=dict)
def list_properties(
    city: str | None = Query(None),
    property_type: PropertyType | None = Query(None),
    transaction_type: TransactionType | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_surface: float | None = Query(None, ge=0),
    rooms: int | None = Query(None, ge=1),
    status: PropertyStatus | None = Query(PropertyStatus.available),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    filters = PropertyFilters(
        city=city,
        property_type=property_type,
        transaction_type=transaction_type,
        min_price=min_price,
        max_price=max_price,
        min_surface=min_surface,
        rooms=rooms,
        status=status,
        page=page,
        per_page=per_page,
    )
    service = PropertyService(db)
    items, total = service.search(filters)
    return {
        "items": [PropertyResponse.model_validate(p) for p in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": -(-total // per_page),
    }


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(property_id: UUID, db: Session = Depends(get_db)):
    service = PropertyService(db)
    return service.get_or_404(property_id)


@router.post("/", response_model=PropertyResponse, status_code=201)
def create_property(
    data: PropertyCreate,
    current_user: User = Depends(require_commercial),
    db: Session = Depends(get_db),
):
    service = PropertyService(db)
    return service.create(data, current_user)


@router.patch("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: UUID,
    data: PropertyUpdate,
    current_user: User = Depends(require_commercial),
    db: Session = Depends(get_db),
):
    service = PropertyService(db)
    return service.update(property_id, data, current_user)


@router.delete("/{property_id}", status_code=204)
def delete_property(
    property_id: UUID,
    current_user: User = Depends(require_commercial),
    db: Session = Depends(get_db),
):
    service = PropertyService(db)
    service.delete(property_id, current_user)


@router.post("/{property_id}/favorite", response_model=dict)
def toggle_favorite(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PropertyService(db)
    is_now_favorite = service.toggle_favorite(property_id, current_user.id)
    return {"is_favorite": is_now_favorite}


@router.get("/me/favorites", response_model=list[PropertyResponse])
def my_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = PropertyRepository(db)
    return repo.get_favorites(current_user.id)
