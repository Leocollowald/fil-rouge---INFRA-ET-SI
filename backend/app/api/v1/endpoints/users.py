from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_it
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse, UserUpdate


router = APIRouter(prefix="/users", tags=["Utilisateurs"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    return repo.update(current_user)


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_it),
):
    repo = UserRepository(db)
    return repo.get_all()


@router.patch("/{user_id}/role", response_model=UserResponse)
def set_role(
    user_id: str,
    role: UserRole,
    db: Session = Depends(get_db),
    _: User = Depends(require_it),
):
    from fastapi import HTTPException, status
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    user.role = role
    return repo.update(user)
