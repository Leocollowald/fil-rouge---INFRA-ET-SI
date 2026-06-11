from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_commercial
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User, UserRole
from app.schemas.transaction import TransactionCreate, TransactionResponse, TransactionUpdate


router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Transaction)
        .filter(
            Transaction.property_id == data.property_id,
            Transaction.buyer_id == current_user.id,
            Transaction.status == TransactionStatus.pending,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vous avez déjà une demande en cours pour ce bien",
        )

    transaction = Transaction(
        property_id=data.property_id,
        buyer_id=current_user.id,
        offered_price=data.offered_price,
        notes=data.notes,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/me", response_model=list[TransactionResponse])
def my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Transaction)
        .filter(Transaction.buyer_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )


@router.get("/agent", response_model=list[TransactionResponse])
def agent_transactions(
    current_user: User = Depends(require_commercial),
    db: Session = Depends(get_db),
):
    return (
        db.query(Transaction)
        .join(Transaction.property)
        .filter(Transaction.property.has(agent_id=current_user.id))
        .order_by(Transaction.created_at.desc())
        .all()
    )


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: UUID,
    data: TransactionUpdate,
    current_user: User = Depends(require_commercial),
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable")

    is_agent_owner = transaction.property.agent_id == current_user.id
    is_privileged = current_user.role in (UserRole.direction, UserRole.it_support)
    if not is_agent_owner and not is_privileged:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    transaction.status = data.status
    if data.notes is not None:
        transaction.notes = data.notes
    db.commit()
    db.refresh(transaction)
    return transaction
