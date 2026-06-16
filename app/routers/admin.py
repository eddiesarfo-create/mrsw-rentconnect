"""Platform admin: metrics, the risk watchlist, and KYC approvals."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db
from ..enums import LeaseStatus, VerificationStatus

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = security.require_role("admin")


@router.get("/overview", response_model=schemas.AdminOverviewOut)
def overview(admin: models.User = Depends(admin_only), db: Session = Depends(get_db)):
    tenants = db.query(models.Tenant).all()
    reserves = round(sum((t.wallet.total if t.wallet else 0) for t in tenants), 2)

    at_risk = 0
    for t in tenants:
        if services.compute_readiness(db, t)["level"] in ("orange", "red"):
            at_risk += 1

    return schemas.AdminOverviewOut(
        users=db.query(models.User).count(),
        tenants=len(tenants),
        landlords=db.query(models.Landlord).count(),
        active_leases=db.query(models.Lease).filter_by(status=LeaseStatus.active.value).count(),
        properties=db.query(models.Property).count(),
        wallet_reserves_total=reserves,
        pending_approvals=db.query(models.User).filter_by(verification_status=VerificationStatus.pending.value).count(),
        at_risk_tenants=at_risk,
    )


@router.get("/risk", response_model=list[schemas.RiskItemOut])
def risk_watchlist(admin: models.User = Depends(admin_only), db: Session = Depends(get_db)):
    out: list[schemas.RiskItemOut] = []
    for t in db.query(models.Tenant).all():
        readiness = services.compute_readiness(db, t)
        if readiness["level"] in ("orange", "red") or readiness["readiness_pct"] < 50:
            trust = services.compute_trust(db, t)
            out.append(schemas.RiskItemOut(
                tenant_id=t.id,
                name=t.user.full_name if t.user else f"Tenant {t.id}",
                level=readiness["level"],
                readiness_pct=readiness["readiness_pct"],
                trust_score=trust["score"],
            ))
    out.sort(key=lambda r: r.readiness_pct)
    return out


@router.get("/approvals", response_model=list[schemas.UserOut])
def pending_approvals(admin: models.User = Depends(admin_only), db: Session = Depends(get_db)):
    return db.query(models.User).filter_by(verification_status=VerificationStatus.pending.value).all()


@router.post("/users/{user_id}/approve", response_model=schemas.UserOut)
def approve_user(user_id: int, admin: models.User = Depends(admin_only), db: Session = Depends(get_db)):
    target = db.get(models.User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.verification_status = VerificationStatus.verified.value
    db.add(models.AuditLog(actor_user_id=admin.id, action="user.approve", entity="user", entity_id=user_id))
    db.commit()
    db.refresh(target)
    return target
