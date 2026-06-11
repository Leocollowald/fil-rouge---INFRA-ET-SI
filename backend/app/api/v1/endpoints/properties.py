import io
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_commercial
from app.models.property import PropertyImage, PropertyStatus, PropertyType, TransactionType
from app.models.user import User, UserRole
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyCreate, PropertyFilters, PropertyImageResponse, PropertyResponse, PropertyUpdate
from app.services.property_service import PropertyService


router = APIRouter(prefix="/properties", tags=["Biens immobiliers"])


@router.get("/me", response_model=list[PropertyResponse])
def my_properties(
    current_user: User = Depends(require_commercial),
    db: Session = Depends(get_db),
):
    repo = PropertyRepository(db)
    return repo.get_by_agent(current_user.id)


@router.get("/me/favorites", response_model=list[PropertyResponse])
def my_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = PropertyRepository(db)
    return repo.get_favorites(current_user.id)


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


def _check_image_permission(prop, user: User) -> None:
    """Vérifie que l'utilisateur peut modifier les images de ce bien."""
    is_owner = prop.agent_id == user.id
    is_privileged = user.role in (UserRole.direction, UserRole.it_support)
    if not is_owner and not is_privileged:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


def _validate_image(file: UploadFile, content: bytes) -> None:
    """Valide le type MIME déclaré et le contenu réel (Pillow)."""
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Type non autorisé : {file.content_type}. Formats acceptés : jpeg, png, webp",
        )
    if len(content) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop lourd (max 5 Mo)",
        )
    # Validation du contenu réel avec Pillow — le content_type client est spoofable
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier image invalide ou corrompu")


@router.post("/{property_id}/images", response_model=list[PropertyImageResponse], status_code=201)
def upload_images(
    property_id: UUID,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PropertyService(db)
    prop = service.get_or_404(property_id)
    _check_image_permission(prop, current_user)

    dest_dir = settings.UPLOAD_DIR / "properties" / str(property_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # La première image devient primaire si aucune n'existe encore
    has_primary = any(img.is_primary for img in prop.images)
    created: list[PropertyImage] = []

    for idx, file in enumerate(files):
        content = file.file.read()
        _validate_image(file, content)

        ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        file_path = dest_dir / filename
        file_path.write_bytes(content)

        is_primary = not has_primary and idx == 0
        img_record = PropertyImage(
            property_id=property_id,
            url=f"/uploads/properties/{property_id}/{filename}",
            is_primary=is_primary,
        )
        db.add(img_record)
        created.append(img_record)

    db.commit()
    for img in created:
        db.refresh(img)

    return created


@router.delete("/{property_id}/images/{image_id}", status_code=204)
def delete_image(
    property_id: UUID,
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PropertyService(db)
    prop = service.get_or_404(property_id)
    _check_image_permission(prop, current_user)

    img = db.query(PropertyImage).filter(
        PropertyImage.id == image_id,
        PropertyImage.property_id == property_id,
    ).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image introuvable")

    # Suppression du fichier sur disque
    file_path = settings.UPLOAD_DIR / img.url.lstrip("/uploads/")
    if file_path.exists():
        file_path.unlink()

    db.delete(img)
    db.commit()
