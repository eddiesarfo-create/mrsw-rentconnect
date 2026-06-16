"""Bookings — prospective tenants reserve beds; owners see and manage requests."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db
from ..enums import BookingStatus

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _booking_out(db: Session, b: models.Booking) -> schemas.BookingOut:
    prop = db.get(models.Property, b.property_id)
    return schemas.BookingOut(
        id=b.id, property_id=b.property_id,
        property_name=prop.name if prop else None,
        university=prop.university if prop else None,
        beds=b.beds, move_in_date=b.move_in_date, status=b.status, created_at=b.created_at,
    )


@router.post("", response_model=schemas.BookingOut)
def create_booking(
    payload: schemas.BookingCreate,
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Any signed-in user can reserve beds at a listing. Decrements availability and
    notifies the owner. (A tenant's wallet then helps them save toward the advance.)"""
    prop = db.get(models.Property, payload.property_id)
    if not prop or not prop.listed:
        raise HTTPException(status_code=404, detail="Listing not found")

    beds = max(1, payload.beds)
    if prop.available_beds is not None and prop.available_beds < beds:
        raise HTTPException(status_code=400, detail="Not enough beds available")

    booking = models.Booking(
        property_id=prop.id, user_id=user.id, beds=beds,
        move_in_date=payload.move_in_date, note=payload.note,
        status=BookingStatus.pending.value,
    )
    if prop.available_beds is not None:
        prop.available_beds -= beds
    db.add(booking)

    owner = db.get(models.Landlord, prop.landlord_id)
    if owner:
        db.add(models.Notification(
            user_id=owner.user_id, title="New booking request",
            body=f"{user.full_name} requested {beds} bed(s) at {prop.name}.",
            notif_type="booking",
        ))
    db.commit()
    db.refresh(booking)
    return _booking_out(db, booking)


@router.get("/me", response_model=list[schemas.BookingOut])
def my_bookings(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.Booking)
        .filter_by(user_id=user.id)
        .order_by(models.Booking.created_at.desc())
        .all()
    )
    return [_booking_out(db, b) for b in rows]


@router.get("/incoming", response_model=list[schemas.BookingOut])
def incoming_bookings(
    user: models.User = Depends(security.require_role("landlord")),
    db: Session = Depends(get_db),
):
    landlord = services.landlord_for_user(db, user)
    if not landlord:
        return []
    prop_ids = [p.id for p in db.query(models.Property.id).filter_by(landlord_id=landlord.id).all()]
    rows = (
        db.query(models.Booking)
        .filter(models.Booking.property_id.in_(prop_ids or [-1]))
        .order_by(models.Booking.created_at.desc())
        .all()
    )
    return [_booking_out(db, b) for b in rows]


@router.patch("/{booking_id}/status", response_model=schemas.BookingOut)
def update_booking(
    booking_id: int,
    payload: schemas.BookingStatusUpdate,
    user: models.User = Depends(security.require_role("landlord")),
    db: Session = Depends(get_db),
):
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    prop = db.get(models.Property, booking.property_id)
    landlord = services.landlord_for_user(db, user)
    if not prop or not landlord or prop.landlord_id != landlord.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    new_status = payload.status.value
    # Returning beds to inventory when cancelling a previously-held booking.
    if new_status == BookingStatus.cancelled.value and booking.status != BookingStatus.cancelled.value:
        if prop.available_beds is not None:
            prop.available_beds += booking.beds
    booking.status = new_status
    db.commit()
    db.refresh(booking)
    return _booking_out(db, booking)
