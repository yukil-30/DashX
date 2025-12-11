"""
Account Router
Endpoints for account balance and deposit management
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, Transaction
from app.schemas import (
    DepositRequest, DepositResponse, BalanceResponse,
    TransactionResponse, TransactionListResponse
)
from app.auth import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["Account"])


def format_cents_to_dollars(cents: int) -> str:
    """Format cents as dollar string (e.g., 1050 -> '$10.50')"""
    dollars = cents / 100
    return f"${dollars:,.2f}"


def create_transaction(
    db: Session,
    account: Account,
    amount_cents: int,
    transaction_type: str,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    description: Optional[str] = None
) -> Transaction:
    """Create an audit log entry for a balance change"""
    balance_before = account.balance
    balance_after = account.balance + amount_cents
    
    transaction = Transaction(
        accountID=account.ID,
        amount_cents=amount_cents,
        balance_before=balance_before,
        balance_after=balance_after,
        transaction_type=transaction_type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    db.add(transaction)
    return transaction


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: Account = Depends(get_current_user)
):
    """
    Get the current user's account balance.
    
    Returns balance in cents and formatted string.
    """
    return BalanceResponse(
        balance_cents=current_user.balance,
        balance_formatted=format_cents_to_dollars(current_user.balance)
    )


@router.post("/deposit", response_model=DepositResponse)
async def deposit(
    request: DepositRequest,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deposit funds into the current user's account.
    
    Amount must be positive (in cents).
    Maximum single deposit: $1,000,000.00 (100,000,000 cents)
    """
    # Validation already handled by Pydantic, but double-check
    if request.amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deposit amount must be positive"
        )
    
    # Create audit log transaction
    create_transaction(
        db=db,
        account=current_user,
        amount_cents=request.amount_cents,
        transaction_type="deposit",
        reference_type="deposit",
        description=f"Deposit of {format_cents_to_dollars(request.amount_cents)}"
    )
    
    # Update balance
    current_user.balance += request.amount_cents
    
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"Deposit: user={current_user.email}, amount={request.amount_cents}, new_balance={current_user.balance}")
    
    return DepositResponse(
        message="Deposit successful",
        new_balance_cents=current_user.balance,
        new_balance_formatted=format_cents_to_dollars(current_user.balance)
    )


@router.post("/withdraw", response_model=DepositResponse)
async def withdraw(
    request: DepositRequest,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Withdraw funds from the current user's account.
    
    Amount must be positive (in cents).
    Cannot withdraw more than current balance.
    """
    if request.amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Withdrawal amount must be positive"
        )
    
    if current_user.balance < request.amount_cents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Current balance: {format_cents_to_dollars(current_user.balance)}"
        )
    
    # Create audit log transaction
    create_transaction(
        db=db,
        account=current_user,
        amount_cents=-request.amount_cents,
        transaction_type="withdrawal",
        reference_type="withdrawal",
        description=f"Withdrawal of {format_cents_to_dollars(request.amount_cents)}"
    )
    
    # Update balance
    current_user.balance -= request.amount_cents
    
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"Withdrawal: user={current_user.email}, amount={request.amount_cents}, new_balance={current_user.balance}")
    
    return DepositResponse(
        message="Withdrawal successful",
        new_balance_cents=current_user.balance,
        new_balance_formatted=format_cents_to_dollars(current_user.balance)
    )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    limit: int = Query(20, ge=1, le=100, description="Max transactions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    transaction_type: Optional[str] = Query(None, description="Filter by type"),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get transaction history for the current user.
    
    Returns list of balance changes with audit details.
    """
    query = db.query(Transaction).filter(Transaction.accountID == current_user.ID)
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    total = query.count()
    transactions = query.order_by(Transaction.id.desc()).offset(offset).limit(limit).all()
    
    return TransactionListResponse(
        transactions=[
            TransactionResponse(
                id=t.id,
                accountID=t.accountID,
                amount_cents=t.amount_cents,
                balance_before=t.balance_before,
                balance_after=t.balance_after,
                transaction_type=t.transaction_type,
                reference_type=t.reference_type,
                reference_id=t.reference_id,
                description=t.description,
                created_at=t.created_at.isoformat() if hasattr(t.created_at, 'isoformat') else str(t.created_at)
            )
            for t in transactions
        ],
        total=total
    )
