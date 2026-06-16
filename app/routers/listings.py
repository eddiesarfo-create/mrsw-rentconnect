"""Hostel marketplace — public search/detail (no auth) and owner listing management."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db
from ..enums import OccupancyStatus

router = APIRouter(prefix="/listings", tags=["listings"])


def _listing_out(db: Session, p: models.Property) -> schemas.ListingOut:
    owner = db.get(models.Landlord, p.landlord_id)
    owner_name = None
    if owner:
        owner_name = owner.business_name
        if not owner_name:
            u = db.get(models.User, owner.user_id)
            owner_name = u.full_name if u else None
    return schemas.ListingOut(
        id=p.id, name=p.name, owner=owner_name, university=p.university, city=p.city,
        area=p.address, room_type=p.room_type, price_per_bed=p.price_per_bed,
        total_beds=p.total_beds, available_beds=p.available_beds,
        amenities=p.amenities or [], photos=p.photos or [], description=p.description,
    )


@router.get("", response_model=list[schemas.ListingOut])
def search(
    university: Optional[str] = None,
    q: Optional[str] = None,
    room_type: Optional[str] = None,
    max_price: Optional[float] = None,
    available_only: bool = True,
    db: Session = Depends(get_db),
):
    """Public hostel search. No auth — prospective tenants browse before signing up."""
    query = db.query(models.Property).filter(models.Property.listed.is_(True))
    if available_only:
        query = query.filter(models.Property.available_beds > 0)
    if university:
        query = query.filter(models.Property.university.ilike(f"%{university}%"))
    if room_type:
        query = query.filter(models.Property.room_type == room_type)
    if max_price is not None:
        query = query.filter(models.Property.price_per_bed <= max_price)
    if q:
        like = f"%{q}%"
        query = query.filter(
            models.Property.name.ilike(like)
            | models.Property.description.ilike(like)
            | models.Property.university.ilike(like)
            | models.Property.city.ilike(like)
        )
    props = query.order_by(models.Property.price_per_bed).all()
    return [_listing_out(db, p) for p in props]


@router.get("/mine", response_model=list[schemas.ListingOut])
def my_listings(
    user: models.User = Depends(security.require_role("landlord")),
    db: Session = Depends(get_db),
):
    landlord = services.landlord_for_user(db, user)
    if not landlord:
        return []
    props = db.query(models.Property).filter_by(landlord_id=landlord.id, listed=True).all()
    return [_listing_out(db, p) for p in props]


@router.post("", response_model=schemas.ListingOut)
def create_listing(
    payload: schemas.ListingCreate,
    user: models.User = Depends(security.require_role("landlord")),
    db: Session = Depends(get_db),
):
    landlord = services.landlord_for_user(db, user)
    if not landlord:
        raise HTTPException(status_code=400, detail="Landlord profile not found")

    available = payload.available_beds if payload.available_beds is not None else payload.total_beds
    prop = models.Property(
        landlord_id=landlord.id, listed=True, name=payload.name, university=payload.university,
        city=payload.city, address=payload.area, property_type="Hostel", room_type=payload.room_type,
        price_per_bed=payload.price_per_bed, total_beds=payload.total_beds, available_beds=available,
        amenities=payload.amenities, photos=payload.photos, description=payload.description,
        occupancy_status=OccupancyStatus.occupied.value,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return _listing_out(db, prop)


@router.get("/{listing_id}", response_model=schemas.ListingOut)
def listing_detail(listing_id: int, db: Session = Depends(get_db)):
    prop = db.get(models.Property, listing_id)
    if not prop or not prop.listed:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_out(db, prop)
