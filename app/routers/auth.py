"""Authentication: register (with role profile), login, current user."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..enums import Role

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=security.hash_password(payload.password),
        role=payload.role.value,
        city=payload.city,
        country=payload.country,
        ghana_card=payload.ghana_card,
        address=payload.address,
    )
    db.add(user)
    db.flush()  # assign user.id

    # Create the role-specific profile (and a wallet for tenants).
    if user.role == Role.tenant.value:
        tenant = models.Tenant(user_id=user.id)
        db.add(tenant)
        db.flush()
        db.add(models.Wallet(tenant_id=tenant.id))
    elif user.role == Role.landlord.value:
        db.add(models.Landlord(user_id=user.id))
    elif user.role == Role.admin.value:
        db.add(models.AdminUser(user_id=user.id))

    db.commit()
    db.refresh(user)
    return schemas.TokenResponse(
        access_token=security.create_access_token(user),
        user=schemas.UserOut.model_validate(user),
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return schemas.TokenResponse(
        access_token=security.create_access_token(user),
        user=schemas.UserOut.model_validate(user),
    )


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(security.get_current_user)):
    return user
