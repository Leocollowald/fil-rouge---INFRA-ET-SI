from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.user import User, UserRole
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyCreate, PropertyFilters, PropertyUpdate


class PropertyService:
    def __init__(self, db: Session):
        self.repo = PropertyRepository(db)

    def create(self, data: PropertyCreate, agent: User) -> Property:
        prop = Property(
            **data.model_dump(),
            agent_id=agent.id,
        )
        if not prop.agency_id and agent.agency_id:
            prop.agency_id = agent.agency_id
        return self.repo.create(prop)

    def get_or_404(self, property_id: UUID) -> Property:
        prop = self.repo.get_by_id_with_relations(property_id)
        if not prop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bien introuvable")
        return prop

    def update(self, property_id: UUID, data: PropertyUpdate, current_user: User) -> Property:
        prop = self.get_or_404(property_id)
        self._check_write_permission(prop, current_user)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(prop, field, value)

        return self.repo.update(prop)

    def delete(self, property_id: UUID, current_user: User) -> None:
        prop = self.get_or_404(property_id)
        self._check_write_permission(prop, current_user)
        self.repo.delete(prop)

    def search(self, filters: PropertyFilters) -> tuple[list[Property], int]:
        return self.repo.search(filters)

    def toggle_favorite(self, property_id: UUID, user_id: UUID) -> bool:
        if self.repo.is_favorite(user_id, property_id):
            self.repo.remove_favorite(user_id, property_id)
            return False
        self.repo.add_favorite(user_id, property_id)
        return True

    def _check_write_permission(self, prop: Property, user: User) -> None:
        is_owner = prop.agent_id == user.id
        is_privileged = user.role in (UserRole.direction, UserRole.it_support)
        if not is_owner and not is_privileged:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
