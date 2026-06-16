"""Leases: landlords create them; tenants and landlords list their own."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db
from ..enums import OccupancyStatus

router = APIRouter(prefix="/leases", tags=["leases"])


@router.post("", response_model=schemas.LeaseOut)
def create_lease(
    payload: schemas.LeaseCreate,
    user: models.User = Depends(security.require_role("landlord")),
    db: Session = Depends(get_db),
):
    landlord = services.landlord_for_user(db, user)
    if not landlord:
        raise HTTPException(status_code=400, detail="Landlord profile not found")

    prop = db.get(models.Property, payload.property_id)
    if not prop or prop.landlord_id != landlord.id:
        raise HTTPException(status_code=404, detail="Property not found in your portfolio")
    if not db.get(models.Tenant, payload.tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")

    lease = models.Lease(landlord_id=landlord.id, **payload.model_dump())
    prop.occupancy_status = OccupancyStatus.occupied.value
    db.add(lease)
    db.commit()
    db.refresh(lease)
    return lease


@router.get("/me", response_model=list[schemas.LeaseOut])
def my_leases(
    user: models.User = Depends(security.require_role("tenant")),
    db: Session = Depends(get_db),
):
    tenant = services.tenant_for_user(db, user)
    if not tenant:
        return []
    return db.query(models.Lease).filter_by(tenant_id=tenant.id).all()


@router.get("", response_model=list[schemas.LeaseOut])
def landlord_leases(
    user: models.User = Depends(security.require_role("landlord")),
    db: Session = Depends(get_db),
):
    landlord = services.landlord_for_user(db, user)
    if not landlord:
        return []
    return db.query(models.Lease).filter_by(landlord_id=landlord.id).all()
