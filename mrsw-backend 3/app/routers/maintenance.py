"""Maintenance requests: tenants file, the system triages urgency by rules,
landlords/managers/admins update status."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db
from ..enums import MaintenanceStatus, Urgency

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

_EMERGENCY = ("burst", "leak", "flood", "fire", "gas", "sewage", "no water", "electric shock", "exposed wire")
_HIGH = ("no power", "socket", "broken lock", "security", "blocked drain", "broken window")
_LOW = ("drip", "paint", "scuff", "minor", "squeak", "light bulb")


def classify(issue_type: str | None, description: str | None) -> str:
    text = f"{issue_type or ''} {description or ''}".lower()
    if any(k in text for k in _EMERGENCY):
        return Urgency.emergency.value
    if any(k in text for k in _HIGH):
        return Urgency.high.value
    if any(k in text for k in _LOW):
        return Urgency.low.value
    return Urgency.medium.value


@router.post("", response_model=schemas.MaintenanceOut)
def create_request(
    payload: schemas.MaintenanceCreate,
    user: models.User = Depends(security.require_role("tenant")),
    db: Session = Depends(get_db),
):
    tenant = services.tenant_for_user(db, user)
    if not db.get(models.Property, payload.property_id):
        raise HTTPException(status_code=404, detail="Property not found")

    urgency = payload.urgency.value if payload.urgency else classify(payload.issue_type, payload.description)
    req = models.MaintenanceRequest(
        property_id=payload.property_id,
        tenant_id=tenant.id if tenant else None,
        issue_type=payload.issue_type,
        description=payload.description,
        media=payload.media,
        urgency=urgency,
        status=MaintenanceStatus.landlord_notified.value,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("", response_model=list[schemas.MaintenanceOut])
def list_requests(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.MaintenanceRequest)
    if user.role == "tenant":
        tenant = services.tenant_for_user(db, user)
        q = q.filter(models.MaintenanceRequest.tenant_id == (tenant.id if tenant else -1))
    elif user.role == "landlord":
        landlord = services.landlord_for_user(db, user)
        prop_ids = [p.id for p in db.query(models.Property.id).filter_by(landlord_id=landlord.id).all()] if landlord else []
        q = q.filter(models.MaintenanceRequest.property_id.in_(prop_ids or [-1]))
    # manager / admin see everything
    return q.order_by(models.MaintenanceRequest.reported_at.desc()).all()


@router.patch("/{request_id}/status", response_model=schemas.MaintenanceOut)
def update_status(
    request_id: int,
    payload: schemas.MaintenanceStatusUpdate,
    user: models.User = Depends(security.require_role("landlord", "manager", "admin")),
    db: Session = Depends(get_db),
):
    req = db.get(models.MaintenanceRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = payload.status.value
    if payload.status == MaintenanceStatus.completed:
        req.resolved_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(req)
    return req
