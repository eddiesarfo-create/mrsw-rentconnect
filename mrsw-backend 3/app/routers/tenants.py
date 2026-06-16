"""Tenant self-service: profile with live trust + readiness."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/me", response_model=schemas.TenantMeOut)
def my_profile(
    user: models.User = Depends(security.require_role("tenant")),
    db: Session = Depends(get_db),
):
    tenant = services.tenant_for_user(db, user)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant profile not found")
    trust = services.compute_trust(db, tenant)
    readiness = services.compute_readiness(db, tenant)
    return schemas.TenantMeOut(
        user=schemas.UserOut.model_validate(user),
        tenant_id=tenant.id,
        trust=schemas.TrustOut(tenant_id=tenant.id, **trust),
        readiness=readiness,
    )
