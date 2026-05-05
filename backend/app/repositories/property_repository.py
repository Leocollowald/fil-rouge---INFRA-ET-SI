from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.models.property import Favorite, Property, PropertyStatus
from app.repositories.base import BaseRepository
from app.schemas.property import PropertyFilters


class PropertyRepository(BaseRepository[Property]):
    def __init__(self, db: Session):
        super().__init__(Property, db)

    def get_by_id_with_relations(self, id: UUID) -> Property | None:
        return (
            self.db.query(Property)
            .options(joinedload(Property.images), joinedload(Property.agency), joinedload(Property.agent))
            .filter(Property.id == id)
            .first()
        )

    def search(self, filters: PropertyFilters) -> tuple[list[Property], int]:
        query = self.db.query(Property).options(joinedload(Property.images))

        conditions = []
        if filters.city:
            conditions.append(Property.city.ilike(f"%{filters.city}%"))
        if filters.property_type:
            conditions.append(Property.property_type == filters.property_type)
        if filters.transaction_type:
            conditions.append(Property.transaction_type == filters.transaction_type)
        if filters.min_price is not None:
            conditions.append(Property.price >= filters.min_price)
        if filters.max_price is not None:
            conditions.append(Property.price <= filters.max_price)
        if filters.min_surface is not None:
            conditions.append(Property.surface >= filters.min_surface)
        if filters.rooms is not None:
            conditions.append(Property.rooms >= filters.rooms)
        if filters.status:
            conditions.append(Property.status == filters.status)

        if conditions:
            query = query.filter(and_(*conditions))

        total = query.count()
        offset = (filters.page - 1) * filters.per_page
        items = query.order_by(Property.created_at.desc()).offset(offset).limit(filters.per_page).all()

        return items, total

    def get_by_agent(self, agent_id: UUID) -> list[Property]:
        return self.db.query(Property).filter(Property.agent_id == agent_id).all()

    def add_favorite(self, user_id: UUID, property_id: UUID) -> Favorite:
        existing = (
            self.db.query(Favorite)
            .filter(Favorite.user_id == user_id, Favorite.property_id == property_id)
            .first()
        )
        if existing:
            return existing
        favorite = Favorite(user_id=user_id, property_id=property_id)
        self.db.add(favorite)
        self.db.commit()
        return favorite

    def remove_favorite(self, user_id: UUID, property_id: UUID) -> bool:
        favorite = (
            self.db.query(Favorite)
            .filter(Favorite.user_id == user_id, Favorite.property_id == property_id)
            .first()
        )
        if not favorite:
            return False
        self.db.delete(favorite)
        self.db.commit()
        return True

    def get_favorites(self, user_id: UUID) -> list[Property]:
        return (
            self.db.query(Property)
            .join(Favorite)
            .filter(Favorite.user_id == user_id)
            .options(joinedload(Property.images))
            .all()
        )

    def is_favorite(self, user_id: UUID, property_id: UUID) -> bool:
        return (
            self.db.query(Favorite.id)
            .filter(Favorite.user_id == user_id, Favorite.property_id == property_id)
            .first()
        ) is not None

    def count_by_status(self) -> dict:
        results = self.db.query(Property.status, Property.id).all()
        counts = {}
        for status, _ in results:
            counts[status] = counts.get(status, 0) + 1
        return counts
