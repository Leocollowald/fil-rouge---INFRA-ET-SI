from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.agency import Agency
from app.schemas.agency import AgencyResponse


router = APIRouter(prefix="/agencies", tags=["Agences"])


@router.get("/", response_model=list[AgencyResponse])
def list_agencies(db: Session = Depends(get_db)):
    return db.query(Agency).order_by(Agency.name).all()


@router.get("/{agency_id}", response_model=AgencyResponse)
def get_agency(agency_id: UUID, db: Session = Depends(get_db)):
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    if not agency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agence introuvable")
    return agency
