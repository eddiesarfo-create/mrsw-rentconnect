"""Pydantic v2 request/response schemas."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .enums import (
    BookingStatus, Bucket, Frequency, MaintenanceStatus, OccupancyStatus, Role, Urgency,
    VerificationStatus,
)

ORM = ConfigDict(from_attributes=True)


# ---- auth / users ----

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=6)
    phone: Optional[str] = None
    role: Role = Role.tenant
    city: Optional[str] = None
    country: str = "Ghana"
    ghana_card: Optional[str] = None
    address: Optional[str] = None


class UserOut(BaseModel):
    model_config = ORM
    id: int
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    city: Optional[str] = None
    country: Optional[str] = None
    verification_status: str
    created_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- wallet ----

class WalletOut(BaseModel):
    tenant_id: int
    stability_reserve: float
    housing_savings: float
    property_protection: float
    emergency_support: float
    ownership_fund: float
    target_amount: float
    rent_due_date: Optional[date] = None
    total: float
    readiness: dict


class TransactionOut(BaseModel):
    model_config = ORM
    id: int
    bucket: str
    amount: float
    method: Optional[str] = None
    status: str
    reference: Optional[str] = None
    created_at: Optional[datetime] = None


class CreditRequest(BaseModel):
    """Admin manual wallet credit (MVP payment flow)."""
    tenant_id: int
    bucket: Bucket
    amount: float = Field(gt=0)
    method: str = "manual"
    reference: Optional[str] = None


# ---- contribution plans ----

class PlanCreate(BaseModel):
    amount: float = Field(gt=0)
    frequency: Frequency = Frequency.weekly
    payment_method: Optional[str] = None
    start_date: Optional[date] = None
    target_amount: Optional[float] = None
    rent_due_date: Optional[date] = None


class PlanOut(BaseModel):
    model_config = ORM
    id: int
    tenant_id: int
    amount: float
    frequency: str
    payment_method: Optional[str] = None
    target_amount: float
    rent_due_date: Optional[date] = None
    status: str


# ---- properties ----

class PropertyCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Ghana"
    property_type: Optional[str] = None
    monthly_rent: float = 0
    advance_rent: float = 0
    amenities: list[str] = []
    maintenance_rules: Optional[str] = None
    occupancy_status: OccupancyStatus = OccupancyStatus.vacant


class PropertyOut(BaseModel):
    model_config = ORM
    id: int
    landlord_id: int
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    property_type: Optional[str] = None
    monthly_rent: float
    advance_rent: float
    occupancy_status: str
    health_score: int


# ---- leases ----

class LeaseCreate(BaseModel):
    tenant_id: int
    property_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_amount: float = 0
    payment_cycle: str = "annual_advance"
    deposit: float = 0
    maintenance_terms: Optional[str] = None
    renewal_terms: Optional[str] = None


class LeaseOut(BaseModel):
    model_config = ORM
    id: int
    tenant_id: int
    landlord_id: int
    property_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_amount: float
    payment_cycle: str
    deposit: float
    status: str


# ---- maintenance ----

class MaintenanceCreate(BaseModel):
    property_id: int
    issue_type: Optional[str] = None
    description: Optional[str] = None
    media: list[str] = []
    urgency: Optional[Urgency] = None  # auto-classified if omitted


class MaintenanceStatusUpdate(BaseModel):
    status: MaintenanceStatus


class MaintenanceOut(BaseModel):
    model_config = ORM
    id: int
    property_id: int
    tenant_id: Optional[int] = None
    issue_type: Optional[str] = None
    description: Optional[str] = None
    urgency: str
    status: str
    reported_at: Optional[datetime] = None


# ---- scoring views ----

class TrustOut(BaseModel):
    tenant_id: int
    score: int
    band: str
    factors: dict


class TenantMeOut(BaseModel):
    user: UserOut
    tenant_id: int
    trust: TrustOut
    readiness: dict


class AdminOverviewOut(BaseModel):
    users: int
    tenants: int
    landlords: int
    active_leases: int
    properties: int
    wallet_reserves_total: float
    pending_approvals: int
    at_risk_tenants: int


class RiskItemOut(BaseModel):
    tenant_id: int
    name: str
    level: str
    readiness_pct: float
    trust_score: int


# ---- marketplace: hostel listings ----

class ListingCreate(BaseModel):
    name: str
    university: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    room_type: Optional[str] = None
    price_per_bed: float = Field(ge=0)
    total_beds: int = Field(ge=1)
    available_beds: Optional[int] = None
    amenities: list[str] = []
    photos: list[str] = []
    description: Optional[str] = None


class ListingOut(BaseModel):
    id: int
    name: str
    owner: Optional[str] = None
    university: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    room_type: Optional[str] = None
    price_per_bed: Optional[float] = None
    total_beds: Optional[int] = None
    available_beds: Optional[int] = None
    amenities: list[str] = []
    photos: list[str] = []
    description: Optional[str] = None


# ---- marketplace: bookings ----

class BookingCreate(BaseModel):
    property_id: int
    beds: int = Field(default=1, ge=1)
    move_in_date: Optional[date] = None
    note: Optional[str] = None


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingOut(BaseModel):
    id: int
    property_id: int
    property_name: Optional[str] = None
    university: Optional[str] = None
    beds: int
    move_in_date: Optional[date] = None
    status: str
    created_at: Optional[datetime] = None
