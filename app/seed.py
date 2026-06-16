"""Create tables and seed a demo dataset that mirrors the prototype, plus a set of
campus hostel listings for the marketplace.

Run:  python -m app.seed

Idempotent in two independent parts:
- core data (users, Ama's wallet, Kwame's properties) seeds only if there are no users.
- hostel listings seed only if there are no listed properties — so a redeploy adds the
  marketplace data even to a database that already has the core demo data.
"""
from datetime import date, timedelta

from .database import Base, SessionLocal, engine
from .enums import (
    Frequency, MaintenanceStatus, OccupancyStatus, PlanStatus, Role,
    TxnStatus, Urgency, VerificationStatus,
)
from . import models, scoring, security, services

DEMO_PASSWORD = "password123"
ADMIN_PASSWORD = "admin123"

# Placeholder photos (always render). Owners replace these with real uploads later.
def _photos(seed):
    return [f"https://picsum.photos/seed/{seed}{n}/800/600" for n in (1, 2, 3)]


def _make_user(db, name, email, password, role, **extra):
    u = models.User(
        full_name=name, email=email, phone=extra.get("phone"),
        password_hash=security.hash_password(password), role=role.value,
        city=extra.get("city", "Accra"), country="Ghana",
        ghana_card=extra.get("ghana_card"), address=extra.get("address"),
        verification_status=VerificationStatus.verified.value,
    )
    db.add(u)
    db.flush()
    return u


def _seed_core(db):
    today = date.today()
    due = today + timedelta(days=120)

    admin_u = _make_user(db, "Sahara Square", "admin@sahara.square", ADMIN_PASSWORD, Role.admin)
    db.add(models.AdminUser(user_id=admin_u.id, permissions=["all"]))

    kwame_u = _make_user(db, "Kwame Asante", "kwame@example.com", DEMO_PASSWORD, Role.landlord, phone="+233 20 111 2233")
    kwame = models.Landlord(user_id=kwame_u.id, business_name="Asante Properties")
    db.add(kwame)
    db.flush()

    _make_user(db, "Akua Boahene", "akua@example.com", DEMO_PASSWORD, Role.manager, phone="+233 27 444 5566")

    ama_u = _make_user(
        db, "Ama Mensah", "ama@example.com", DEMO_PASSWORD, Role.tenant,
        phone="+233 24 555 0142", ghana_card="GHA-742199836",
        address="12 Palm Close, Spintex, Accra",
    )
    ama = models.Tenant(user_id=ama_u.id, housing_status="renting")
    db.add(ama)
    db.flush()

    wallet = models.Wallet(
        tenant_id=ama.id, stability_reserve=1200, housing_savings=1560,
        property_protection=300, emergency_support=200, ownership_fund=100,
        target_amount=8000, rent_due_date=due,
    )
    db.add(wallet)
    db.flush()

    ledger = [
        ("housing_savings", 200, "MTN MoMo", TxnStatus.success),
        ("stability_reserve", 150, "MTN MoMo", TxnStatus.success),
        ("emergency_support", 200, "Bank transfer", TxnStatus.success),
        ("housing_savings", 200, "MTN MoMo", TxnStatus.success),
        ("property_protection", 100, "Auto-deduct", TxnStatus.success),
        ("housing_savings", 200, "MTN MoMo", TxnStatus.failed),
    ]
    for bucket, amount, method, st in ledger:
        db.add(models.WalletTransaction(
            wallet_id=wallet.id, bucket=bucket, amount=amount, method=method, status=st.value,
        ))

    db.add(models.ContributionPlan(
        tenant_id=ama.id, amount=200, frequency=Frequency.weekly.value,
        payment_method="MTN MoMo", start_date=today, target_amount=8000,
        rent_due_date=due, status=PlanStatus.active.value,
    ))
    db.add(models.Guarantor(
        tenant_id=ama.id, name="Yaw Mensah", phone="+233 24 000 1111",
        relationship_to_tenant="Brother", id_number="GHA-100200300", strength=70,
    ))

    spintex = models.Property(
        landlord_id=kwame.id, name="Spintex 2-Bedroom Apartment", address="12 Palm Close, Spintex",
        city="Accra", property_type="Apartment", monthly_rent=8000, advance_rent=8000,
        amenities=["Water tank", "Parking", "Security"], occupancy_status=OccupancyStatus.occupied.value,
        health_score=88,
    )
    east_legon = models.Property(
        landlord_id=kwame.id, name="East Legon Townhouse", city="Accra", property_type="Townhouse",
        monthly_rent=24000, advance_rent=24000, occupancy_status=OccupancyStatus.occupied.value, health_score=72,
    )
    osu = models.Property(
        landlord_id=kwame.id, name="Osu Studio", city="Accra", property_type="Studio",
        monthly_rent=6000, advance_rent=6000,
        occupancy_status=OccupancyStatus.pending_verification.value, health_score=95,
    )
    db.add_all([spintex, east_legon, osu])
    db.flush()

    db.add(models.Lease(
        tenant_id=ama.id, landlord_id=kwame.id, property_id=spintex.id,
        start_date=date(2025, 9, 1), end_date=date(2026, 8, 31), rent_amount=8000,
        payment_cycle="annual_advance", deposit=1000,
    ))
    db.add(models.MaintenanceRequest(
        property_id=spintex.id, tenant_id=ama.id, issue_type="Plumbing",
        description="Burst pipe under the kitchen sink", urgency=Urgency.emergency.value,
        status=MaintenanceStatus.landlord_notified.value,
    ))
    db.commit()

    db.refresh(ama)
    trust = services.compute_trust(db, ama)
    readiness = services.compute_readiness(db, ama)
    ama.trust_score = trust["score"]
    db.add(models.TrustScore(tenant_id=ama.id, score=trust["score"], band=trust["band"], factors=trust["factors"]))
    db.add(models.RiskScore(
        tenant_id=ama.id, level=readiness["level"], readiness_pct=readiness["readiness_pct"],
        wallet_balance=wallet.total, rent_due=wallet.target_amount,
        days_remaining=readiness["days_remaining"], failed_payments=1,
    ))
    db.commit()
    print("Core seed complete.")
    print(f"  Admin    : admin@sahara.square / {ADMIN_PASSWORD}")
    print(f"  Landlord : kwame@example.com   / {DEMO_PASSWORD}")
    print(f"  Manager  : akua@example.com    / {DEMO_PASSWORD}")
    print(f"  Tenant   : ama@example.com     / {DEMO_PASSWORD}")


def _owner(db, name, email):
    """Find-or-create a verified landlord to own hostel listings."""
    existing = db.query(models.User).filter_by(email=email).first()
    if existing:
        ll = db.query(models.Landlord).filter_by(user_id=existing.id).first()
        if ll:
            return ll
        ll = models.Landlord(user_id=existing.id, business_name=name)
        db.add(ll)
        db.flush()
        return ll
    u = _make_user(db, name, email, DEMO_PASSWORD, Role.landlord)
    ll = models.Landlord(user_id=u.id, business_name=name)
    db.add(ll)
    db.flush()
    return ll


def _seed_hostels(db):
    o1 = _owner(db, "Campus Living Ghana", "campus.living@example.com")
    o2 = _owner(db, "Unity Hostels", "unity.hostels@example.com")

    A = ["WiFi", "24/7 Water", "Security", "Study room", "Backup power"]
    hostels = [
        dict(o=o1, name="Pearl Court Hostel", uni="University of Ghana", city="Accra", area="Legon / East Legon",
             room="4-in-1", price=3500, total=48, avail=14, ph="pearl",
             desc="Walking distance to the UG main gate. Tiled rooms, shared kitchenette, and a quiet study lounge."),
        dict(o=o1, name="Unity Heights", uni="University of Ghana", city="Accra", area="Madina",
             room="2-in-1", price=7000, total=30, avail=6, ph="unity",
             desc="Spacious 2-in-1 rooms with private balconies. Shuttle to campus during peak hours."),
        dict(o=o2, name="Royal Gate Residence", uni="KNUST", city="Kumasi", area="Ayeduase (Tech)",
             room="1-in-1", price=9500, total=20, avail=4, ph="royal",
             desc="Self-contained single rooms with en-suite bath. Premium option steps from the Tech junction."),
        dict(o=o2, name="Crystal Lodge", uni="KNUST", city="Kumasi", area="Kotei",
             room="4-in-1", price=3200, total=60, avail=22, ph="crystal",
             desc="Affordable shared rooms popular with first-years. Large compound, on-site provisions shop."),
        dict(o=o1, name="Cape Coast Lodge", uni="University of Cape Coast", city="Cape Coast", area="Amamoma",
             room="2-in-1", price=5500, total=24, avail=9, ph="capelodge",
             desc="Breezy rooms a short walk from UCC's Science campus. Reliable water and tatched study deck."),
        dict(o=o2, name="Hilltop Hostel", uni="University of Professional Studies (UPSA)", city="Accra", area="Madina",
             room="3-in-1", price=4500, total=36, avail=15, ph="hilltop",
             desc="Modern 3-in-1 rooms with fibre WiFi. Close to UPSA and the Madina market."),
    ]
    for h in hostels:
        db.add(models.Property(
            landlord_id=h["o"].id, listed=True, property_type="Hostel",
            occupancy_status=OccupancyStatus.occupied.value, name=h["name"], university=h["uni"],
            city=h["city"], address=h["area"], room_type=h["room"], price_per_bed=h["price"],
            total_beds=h["total"], available_beds=h["avail"], amenities=A, photos=_photos(h["ph"]),
            description=h["desc"],
        ))
    db.commit()
    print(f"Seeded {len(hostels)} hostel listings across {len({h['o'].id for h in hostels})} owners.")
    print(f"  Hostel owners: campus.living@example.com / unity.hostels@example.com  (pw {DEMO_PASSWORD})")


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            _seed_core(db)
        else:
            print("Core data already present — skipping core seed.")

        if db.query(models.Property).filter(models.Property.listed.is_(True)).count() == 0:
            _seed_hostels(db)
        else:
            print("Hostel listings already present — skipping.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
