"""Contribution plans: upsert, fetch, and readiness projection."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas, scoring, security, services
from ..database import get_db
from ..enums import Frequency, PlanStatus

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=schemas.PlanOut)
def upsert_plan(
    payload: schemas.PlanCreate,
    user: models.User = Depends(security.require_role("tenant")),
    db: Session = Depends(get_db),
):
    tenant = services.tenant_for_user(db, user)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant profile not found")
    w = tenant.wallet

    target = payload.target_amount if payload.target_amount is not None else (w.target_amount if w else 0)
    due = payload.rent_due_date or (w.rent_due_date if w else None)

    plan = (
        db.query(models.ContributionPlan)
        .filter_by(tenant_id=tenant.id, status=PlanStatus.active.value)
        .first()
    )
    if plan is None:
        plan = models.ContributionPlan(tenant_id=tenant.id)
        db.add(plan)

    plan.amount = payload.amount
    plan.frequency = payload.frequency.value
    plan.payment_method = payload.payment_method
    plan.start_date = payload.start_date
    plan.target_amount = target or 0
    plan.rent_due_date = due
    plan.status = PlanStatus.active.value

    db.commit()
    db.refresh(plan)
    return plan


@router.get("/me", response_model=schemas.PlanOut)
def my_plan(
    user: models.User = Depends(security.require_role("tenant")),
    db: Session = Depends(get_db),
):
    tenant = services.tenant_for_user(db, user)
    plan = (
        db.query(models.ContributionPlan)
        .filter_by(tenant_id=tenant.id, status=PlanStatus.active.value)
        .first()
        if tenant else None
    )
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan")
    return plan


@router.get("/projection")
def projection(
    amount: float = Query(gt=0),
    frequency: Frequency = Frequency.weekly,
    user: models.User = Depends(security.require_role("tenant")),
    db: Session = Depends(get_db),
):
    tenant = services.tenant_for_user(db, user)
    if not tenant or not tenant.wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    w = tenant.wallet
    return scoring.projection(w.total, w.target_amount or 0, w.rent_due_date, amount, frequency.value)
