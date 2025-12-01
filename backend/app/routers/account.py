"""
Account Router
Endpoints for account balance and deposit management
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, Transaction
from app.schemas import DepositRequest, DepositResponse, BalanceResponse
from app.auth import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["Account"])


def format_cents_to_dollars(cents: int) -> str:
    """Format cents as dollar string (e.g., 1050 -> '$10.50')"""
    dollars = cents / 100
    return f"${dollars:,.2f}"


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
    
    Creates a transaction record for audit trail.
    """
    # Validation already handled by Pydantic, but double-check
    if request.amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deposit amount must be positive"
        )
    
    # Record balance before
    balance_before = current_user.balance
    
    # Update balance
    current_user.balance += request.amount_cents
    balance_after = current_user.balance
    
    # Create transaction record for audit trail
    transaction = Transaction(
        account_id=current_user.id,
        transaction_type="deposit",
        amount=request.amount_cents,
        balance_before=balance_before,
        balance_after=balance_after,
        description=f"Account deposit of {format_cents_to_dollars(request.amount_cents)}",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    db.refresh(current_user)
    
    logger.info(f"Deposit: user={current_user.email}, amount={request.amount_cents}, new_balance={current_user.balance}")
    
    return DepositResponse(
        message="Deposit successful",
        new_balance_cents=current_user.balance,
        new_balance_formatted=format_cents_to_dollars(current_user.balance),
        transaction_id=transaction.id
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
    
    Creates a transaction record for audit trail.
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
    
    # Record balance before
    balance_before = current_user.balance
    
    # Update balance
    current_user.balance -= request.amount_cents
    balance_after = current_user.balance
    
    # Create transaction record for audit trail
    transaction = Transaction(
        account_id=current_user.id,
        transaction_type="withdrawal",
        amount=-request.amount_cents,  # Negative for withdrawals
        balance_before=balance_before,
        balance_after=balance_after,
        description=f"Account withdrawal of {format_cents_to_dollars(request.amount_cents)}",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    db.refresh(current_user)
    
    logger.info(f"Withdrawal: user={current_user.email}, amount={request.amount_cents}, new_balance={current_user.balance}")
    
    return DepositResponse(
        message="Withdrawal successful",
        new_balance_cents=current_user.balance,
        new_balance_formatted=format_cents_to_dollars(current_user.balance),
        transaction_id=transaction.id
    )
