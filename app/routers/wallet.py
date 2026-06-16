"""Tenant wallet: balances + readiness, ledger, and admin manual credit."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db
from ..enums import TxnStatus

router = APIRouter(prefix="/wallet", tags=["wallet"])


def _wallet_out(db: Session, tenant: models.Tenant) -> schemas.WalletOut:
    w = tenant.wallet
    return schemas.WalletOut(
        tenant_id=tenant.id,
        stability_reserve=w.stability_reserve or 0,
        housing_savings=w.housing_savings or 0,
        property_protection=w.property_protection or 0,
        emergency_support=w.emergency_support or 0,
        ownership_fund=w.ownership_fund or 0,
        target_amount=w.target_amount or 0,
        rent_due_date=w.rent_due_date,
        total=w.total,
        readiness=services.compute_readiness(db, tenant),
    )


@router.get("", response_model=schemas.WalletOut)
def my_wallet(
    user: models.User = Depends(security.require_role("tenant")),
    db: Session = Depends(get_db),
):
    tenant = services.tenant_for_user(db, user)
    if not tenant or not tenant.wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return _wallet_out(db, tenant)


@router.get("/transactions", response_model=list[schemas.TransactionOut])
def my_transactions(
    user: models.User = Depends(security.require_role("tenant")),
    db: Session = Depends(get_db),
):
    tenant = services.tenant_for_user(db, user)
    if not tenant or not tenant.wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return (
        db.query(models.WalletTransaction)
        .filter_by(wallet_id=tenant.wallet.id)
        .order_by(models.WalletTransaction.created_at.desc())
        .all()
    )


@router.post("/credit", response_model=schemas.WalletOut)
def credit_wallet(
    req: schemas.CreditRequest,
    admin: models.User = Depends(security.require_role("admin")),
    db: Session = Depends(get_db),
):
    """MVP payment flow: an admin records a confirmed contribution into a fund."""
    wallet = db.query(models.Wallet).filter_by(tenant_id=req.tenant_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for tenant")

    bucket = req.bucket.value
    setattr(wallet, bucket, (getattr(wallet, bucket) or 0) + req.amount)
    db.add(models.WalletTransaction(
        wallet_id=wallet.id, bucket=bucket, amount=req.amount,
        method=req.method, status=TxnStatus.success.value, reference=req.reference,
    ))
    db.add(models.AuditLog(actor_user_id=admin.id, action="wallet.credit", entity="wallet",
                           entity_id=wallet.id, detail={"bucket": bucket, "amount": req.amount}))
    db.commit()

    tenant = db.get(models.Tenant, req.tenant_id)
    return _wallet_out(db, tenant)
