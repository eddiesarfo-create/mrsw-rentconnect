"""String enums shared across models and schemas.

Stored as plain strings in the DB (no Postgres ENUM types), so the set of
allowed values can evolve without a migration. Pydantic validates inputs.
"""
from enum import Enum


class Role(str, Enum):
    tenant = "tenant"
    landlord = "landlord"
    manager = "manager"
    admin = "admin"


class VerificationStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class Bucket(str, Enum):
    stability_reserve = "stability_reserve"
    housing_savings = "housing_savings"
    property_protection = "property_protection"
    emergency_support = "emergency_support"
    ownership_fund = "ownership_fund"


class Frequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    seasonal = "seasonal"


class TxnStatus(str, Enum):
    success = "success"
    failed = "failed"
    pending = "pending"


class RiskLevel(str, Enum):
    green = "green"
    yellow = "yellow"
    orange = "orange"
    red = "red"


class Urgency(str, Enum):
    emergency = "emergency"
    high = "high"
    medium = "medium"
    low = "low"


class MaintenanceStatus(str, Enum):
    open = "open"
    landlord_notified = "landlord_notified"
    contractor_assigned = "contractor_assigned"
    in_progress = "in_progress"
    completed = "completed"
    disputed = "disputed"


class OccupancyStatus(str, Enum):
    vacant = "vacant"
    occupied = "occupied"
    pending_verification = "pending_verification"
    inactive = "inactive"


class InspectionType(str, Enum):
    move_in = "move_in"
    move_out = "move_out"


class PaymentStatus(str, Enum):
    pending = "pending"
    collected = "collected"
    overdue = "overdue"


class DisputeStatus(str, Enum):
    open = "open"
    under_review = "under_review"
    resolved = "resolved"


class LeaseStatus(str, Enum):
    active = "active"
    ended = "ended"
    pending = "pending"


class BookingStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class PlanStatus(str, Enum):
    active = "active"
    paused = "paused"
