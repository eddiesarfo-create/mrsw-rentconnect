"""Rules-first scoring logic. Pure functions, no DB access — easy to unit test
and to later swap for an ML model behind the same interface.
"""
from __future__ import annotations

from datetime import date
from math import ceil, floor

# ---- Rent readiness engine -------------------------------------------------

FREQUENCY_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30, "seasonal": 90}


def readiness(balance: float, target: float, due: date | None,
              consistency: float = 1.0, failed: int = 0) -> dict:
    """Green / Yellow / Orange / Red plus the readiness percentage.

    Thresholds mirror the product UI; failed deductions and a tight runway can
    push a tenant down a band.
    """
    pct = 0.0 if target <= 0 else min(100.0, balance / target * 100.0)
    days = (due - date.today()).days if due else None

    if pct >= 70 and failed <= 1:
        level = "green"
    elif pct >= 40:
        level = "yellow"
    elif pct >= 20:
        level = "orange"
    else:
        level = "red"

    # Time pressure: low balance with little runway is worse than the % implies.
    if days is not None and days < 30 and pct < 60 and level in ("green", "yellow"):
        level = "orange"
    if failed >= 3 and level in ("green", "yellow"):
        level = "orange"

    return {
        "readiness_pct": round(pct, 1),
        "level": level,
        "days_remaining": days,
        "shortfall": round(max(0.0, target - balance), 2),
    }


def projection(balance: float, target: float, due: date | None,
               amount: float, frequency: str) -> dict:
    """What a tenant reaches by the due date at a given contribution cadence."""
    period_days = FREQUENCY_DAYS.get(frequency, 7)
    days = (due - date.today()).days if due else 0
    periods = max(0, floor(days / period_days)) if days > 0 else 0
    projected = balance + amount * periods
    projected_pct = 0.0 if target <= 0 else min(100.0, projected / target * 100.0)
    shortfall = max(0.0, target - projected)
    recommended = ceil((target - balance) / periods) if periods > 0 and target > balance else 0
    return {
        "periods_remaining": periods,
        "projected_balance": round(projected, 2),
        "projected_readiness_pct": round(projected_pct, 1),
        "shortfall": round(shortfall, 2),
        "recommended_contribution": recommended,
        "days_remaining": days,
    }


# ---- Housing trust score ---------------------------------------------------

TRUST_WEIGHTS = {
    "contribution_consistency": 0.20,
    "rent_payment_history": 0.18,
    "failed_deductions": 0.12,        # value is already "higher = fewer failures"
    "wallet_growth": 0.12,
    "maintenance_behavior": 0.10,
    "landlord_review": 0.12,
    "dispute_history": 0.08,
    "guarantor_strength": 0.08,
}


def trust(factors: dict) -> dict:
    """Weighted 0-100 score from factor sub-scores (each 0-100)."""
    score = 0.0
    used = {}
    for key, weight in TRUST_WEIGHTS.items():
        value = float(factors.get(key, 0))
        used[key] = round(value, 1)
        score += weight * value
    score = round(score)
    if score >= 80:
        band = "Strong"
    elif score >= 65:
        band = "Fair"
    elif score >= 50:
        band = "Building"
    else:
        band = "Weak"
    return {"score": score, "band": band, "factors": used}


# ---- Property health score -------------------------------------------------

HEALTH_WEIGHTS = {
    "response_time": 0.30,        # higher = faster responses
    "unresolved_complaints": 0.25,  # higher = fewer unresolved
    "inspection_results": 0.20,
    "tenant_satisfaction": 0.15,
    "safety": 0.10,
}


def property_health(factors: dict) -> dict:
    score = sum(HEALTH_WEIGHTS[k] * float(factors.get(k, 0)) for k in HEALTH_WEIGHTS)
    return {"score": round(score)}
