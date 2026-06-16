"""Properties: landlords create/list their portfolio; managers/admin see all."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=schemas.PropertyOut)
def create_property(
    payload: schemas.PropertyCreate,
    user: models.User = Depends(security.require_role("landlord")),
    db: Session = Depends(get_db),
):
    landlord = services.landlord_for_user(db, user)
    if not landlord:
        raise HTTPException(status_code=400, detail="Landlord profile not found")
    data = payload.model_dump()
    data["occupancy_status"] = payload.occupancy_status.value
    prop = models.Property(landlord_id=landlord.id, **data)
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("", response_model=list[schemas.PropertyOut])
def list_properties(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.Property)
    if user.role == "landlord":
        landlord = services.landlord_for_user(db, user)
        q = q.filter(models.Property.landlord_id == (landlord.id if landlord else -1))
    elif user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return q.order_by(models.Property.id).all()


@router.get("/{property_id}", response_model=schemas.PropertyOut)
def get_property(property_id: int, db: Session = Depends(get_db),
                 user: models.User = Depends(security.get_current_user)):
    prop = db.get(models.Property, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop
