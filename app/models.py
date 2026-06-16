"""SQLAlchemy ORM models — the 19 core MRSW tables.

Design notes:
- A central `users` table holds identity, auth and KYC. Role-specific extra
  data lives in `tenants` / `landlords` / `admin_users`. The `manager` role is
  carried on `users` (a manager is a user assigned to landlords/properties).
- The five-fund wallet is modelled as five balance columns on `wallets` (the
  fund set is fixed); the running ledger lives in `wallet_transactions`.
- Subjective/structured blobs (checklists, factor breakdowns, media lists) use
  JSON columns to stay flexible during the MVP.
"""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base
from .enums import (
    BookingStatus, DisputeStatus, Frequency, InspectionType, LeaseStatus, MaintenanceStatus,
    OccupancyStatus, PaymentStatus, PlanStatus, RiskLevel, Role, TxnStatus,
    Urgency, VerificationStatus,
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(160), nullable=False)
    email = Column(String(160), unique=True, index=True, nullable=False)
    phone = Column(String(40), index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=Role.tenant.value, index=True)
    country = Column(String(80), default="Ghana")
    city = Column(String(80))
    ghana_card = Column(String(40))
    address = Column(String(255))
    photo_url = Column(String(255))
    verification_status = Column(String(20), default=VerificationStatus.pending.value, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    trust_score = Column(Integer, default=0)
    housing_status = Column(String(40), default="renting")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    wallet = relationship("Wallet", back_populates="tenant", uselist=False, cascade="all, delete-orphan")


class Landlord(Base):
    __tablename__ = "landlords"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_name = Column(String(160))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    landlord_id = Column(Integer, ForeignKey("landlords.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    address = Column(String(255))
    city = Column(String(80))
    country = Column(String(80), default="Ghana")
    property_type = Column(String(60))
    monthly_rent = Column(Float, default=0)
    advance_rent = Column(Float, default=0)
    amenities = Column(JSON, default=list)
    maintenance_rules = Column(Text)
    occupancy_status = Column(String(30), default=OccupancyStatus.vacant.value)
    health_score = Column(Integer, default=100)
    # --- marketplace / hostel listing fields ---
    listed = Column(Boolean, default=False, index=True)
    photos = Column(JSON, default=list)
    university = Column(String(160), index=True)
    room_type = Column(String(60))        # e.g. "1-in-1", "2-in-1", "4-in-1"
    price_per_bed = Column(Float)         # GHS per bed per academic year
    total_beds = Column(Integer)
    available_beds = Column(Integer)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Lease(Base):
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    landlord_id = Column(Integer, ForeignKey("landlords.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date)
    end_date = Column(Date)
    rent_amount = Column(Float, default=0)
    payment_cycle = Column(String(40), default="annual_advance")
    deposit = Column(Float, default=0)
    maintenance_terms = Column(Text)
    renewal_terms = Column(Text)
    agreement_url = Column(String(255))
    status = Column(String(20), default=LeaseStatus.active.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    stability_reserve = Column(Float, default=0)
    housing_savings = Column(Float, default=0)
    property_protection = Column(Float, default=0)
    emergency_support = Column(Float, default=0)
    ownership_fund = Column(Float, default=0)
    target_amount = Column(Float, default=0)
    rent_due_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")

    BUCKETS = (
        "stability_reserve", "housing_savings", "property_protection",
        "emergency_support", "ownership_fund",
    )

    @property
    def total(self) -> float:
        return round(sum(getattr(self, b) or 0 for b in self.BUCKETS), 2)


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    bucket = Column(String(40), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(60))
    status = Column(String(20), default=TxnStatus.success.value)
    reference = Column(String(120))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    wallet = relationship("Wallet", back_populates="transactions")


class ContributionPlan(Base):
    __tablename__ = "contribution_plans"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    frequency = Column(String(20), default=Frequency.weekly.value)
    payment_method = Column(String(60))
    start_date = Column(Date)
    target_amount = Column(Float, default=0)
    rent_due_date = Column(Date)
    status = Column(String(20), default=PlanStatus.active.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RentPayment(Base):
    __tablename__ = "rent_payments"

    id = Column(Integer, primary_key=True)
    lease_id = Column(Integer, ForeignKey("leases.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    due_date = Column(Date)
    paid_date = Column(Date)
    method = Column(String(60))
    status = Column(String(20), default=PaymentStatus.pending.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(String(10), default=RiskLevel.green.value)
    readiness_pct = Column(Float, default=0)
    wallet_balance = Column(Float, default=0)
    rent_due = Column(Float, default=0)
    days_remaining = Column(Integer)
    consistency = Column(Float, default=0)
    failed_payments = Column(Integer, default=0)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())


class TrustScore(Base):
    __tablename__ = "trust_scores"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Integer, default=0)
    band = Column(String(20))
    factors = Column(JSON, default=dict)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="SET NULL"), index=True)
    issue_type = Column(String(60))
    description = Column(Text)
    media = Column(JSON, default=list)
    urgency = Column(String(20), default=Urgency.medium.value)
    status = Column(String(30), default=MaintenanceStatus.open.value)
    reported_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    lease_id = Column(Integer, ForeignKey("leases.id", ondelete="SET NULL"), index=True)
    inspection_type = Column(String(20), default=InspectionType.move_in.value)
    checklist = Column(JSON, default=list)
    meter_readings = Column(JSON, default=dict)
    photos = Column(JSON, default=list)
    condition_report = Column(Text)
    inspector = Column(String(120))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DamageReport(Base):
    __tablename__ = "damage_reports"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    items = Column(JSON, default=list)
    total_cost = Column(Float, default=0)
    deducted_from_protection = Column(Boolean, default=False)
    status = Column(String(30), default="assessed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True)
    raised_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    against_user = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    lease_id = Column(Integer, ForeignKey("leases.id", ondelete="SET NULL"), index=True)
    dispute_type = Column(String(80))
    description = Column(Text)
    amount = Column(Float, default=0)
    status = Column(String(20), default=DisputeStatus.open.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Guarantor(Base):
    __tablename__ = "guarantors"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160))
    phone = Column(String(40))
    relationship_to_tenant = Column(String(80))
    id_number = Column(String(40))
    strength = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160))
    body = Column(Text)
    notif_type = Column(String(60))
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String(120))
    entity = Column(String(80))
    entity_id = Column(Integer)
    detail = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    beds = Column(Integer, default=1)
    move_in_date = Column(Date)
    note = Column(Text)
    status = Column(String(20), default=BookingStatus.pending.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
