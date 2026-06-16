"""Helpers shared across routers: tenant lookup and derived scoring."""
from sqlalchemy.orm import Session

from . import models, scoring
from .enums import TxnStatus


def tenant_for_user(db: Session, user: "models.User"):
    return db.query(models.Tenant).filter(models.Tenant.user_id == user.id).first()


def landlord_for_user(db: Session, user: "models.User"):
    return db.query(models.Landlord).filter(models.Landlord.user_id == user.id).first()


def wallet_signals(db: Session, wallet: "models.Wallet"):
    """(consistency 0-1, failed_count) derived from the transaction ledger."""
    txns = db.query(models.WalletTransaction).filter_by(wallet_id=wallet.id).all()
    attempts = len(txns)
    failed = sum(1 for t in txns if t.status == TxnStatus.failed.value)
    success = attempts - failed
    consistency = (success / attempts) if attempts else 1.0
    return consistency, failed


def compute_readiness(db: Session, tenant: "models.Tenant") -> dict:
    w = tenant.wallet
    if not w:
        return scoring.readiness(0, 0, None)
    consistency, failed = wallet_signals(db, w)
    return scoring.readiness(w.total, w.target_amount or 0, w.rent_due_date, consistency, failed)


def derive_trust_factors(db: Session, tenant: "models.Tenant") -> dict:
    w = tenant.wallet
    consistency, failed = wallet_signals(db, w) if w else (1.0, 0)
    disputes = (
        db.query(models.Dispute)
        .filter((models.Dispute.raised_by == tenant.user_id) | (models.Dispute.against_user == tenant.user_id))
        .count()
    )
    guarantor = db.query(models.Guarantor).filter_by(tenant_id=tenant.id).first()
    return {
        "contribution_consistency": round(consistency * 100),
        "rent_payment_history": 80,
        "failed_deductions": max(0, 100 - failed * 30),
        "wallet_growth": 70,
        "maintenance_behavior": 82,
        "landlord_review": 78,
        "dispute_history": 100 if disputes == 0 else max(40, 100 - disputes * 20),
        "guarantor_strength": (guarantor.strength or 70) if guarantor else 40,
    }


def compute_trust(db: Session, tenant: "models.Tenant") -> dict:
    return scoring.trust(derive_trust_factors(db, tenant))
