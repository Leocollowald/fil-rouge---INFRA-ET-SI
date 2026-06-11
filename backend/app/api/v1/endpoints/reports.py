from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.analysis import reports
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole


router = APIRouter(prefix="/reports", tags=["Rapports & Statistiques"])

# Rôles autorisés à consulter les rapports (direction et IT support)
_ALLOWED_ROLES = (UserRole.direction, UserRole.it_support)


def _require_reports_access(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in _ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à la direction et au support IT",
        )
    return current_user


@router.get("/ventes")
def rapport_ventes(
    db: Session = Depends(get_db),
    _: User = Depends(_require_reports_access),
):
    """CA, volumes, répartition par agence/ville/type et évolution mensuelle."""
    return reports.rapport_ventes(db)


@router.get("/populaires")
def biens_populaires(
    limit: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(_require_reports_access),
):
    """Top biens par popularité (favoris + demandes)."""
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=422, detail="limit doit être entre 1 et 50")
    return reports.biens_populaires(db, limit)


@router.get("/prix-m2")
def prix_m2(
    db: Session = Depends(get_db),
    _: User = Depends(_require_reports_access),
):
    """Prix moyen au m² par ville pour identifier les zones de marché."""
    return reports.prix_m2_par_ville(db)


@router.get("/catalogue")
def stats_catalogue(
    db: Session = Depends(get_db),
    _: User = Depends(_require_reports_access),
):
    """Statistiques descriptives globales du catalogue (statuts, prix, types)."""
    return reports.stats_catalogue(db)


@router.get("/delai-vente")
def delai_vente(
    db: Session = Depends(get_db),
    _: User = Depends(_require_reports_access),
):
    """Délai moyen de vente par ville — indicateur prédictif de liquidité."""
    return reports.delai_vente_par_ville(db)
