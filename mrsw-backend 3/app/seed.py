"""Create tables and seed a demo dataset that mirrors the prototype.

Run:  python -m app.seed
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


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            print("Database already has users — skipping seed.")
            return

        today = date.today()
        due = today + timedelta(days=120)

        def make_user(name, email, password, role, **extra):
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

        # --- users ---
        admin_u = make_user("Sahara Square", "admin@sahara.square", ADMIN_PASSWORD, Role.admin)
        db.add(models.AdminUser(user_id=admin_u.id, permissions=["all"]))

        kwame_u = make_user("Kwame Asante", "kwame@example.com", DEMO_PASSWORD, Role.landlord, phone="+233 20 111 2233")
        kwame = models.Landlord(user_id=kwame_u.id, business_name="Asante Properties")
        db.add(kwame)
        db.flush()

        make_user("Akua Boahene", "akua@example.com", DEMO_PASSWORD, Role.manager, phone="+233 27 444 5566")

        ama_u = make_user(
            "Ama Mensah", "ama@example.com", DEMO_PASSWORD, Role.tenant,
            phone="+233 24 555 0142", ghana_card="GHA-742199836",
            address="12 Palm Close, Spintex, Accra",
        )
        ama = models.Tenant(user_id=ama_u.id, housing_status="renting")
        db.add(ama)
        db.flush()

        # --- wallet (buckets total 3360 toward 8000 -> 42%) ---
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

        # --- properties ---
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

        # --- lease ---
        db.add(models.Lease(
            tenant_id=ama.id, landlord_id=kwame.id, property_id=spintex.id,
            start_date=date(2025, 9, 1), end_date=date(2026, 8, 31), rent_amount=8000,
            payment_cycle="annual_advance", deposit=1000,
        ))

        # --- maintenance ---
        db.add(models.MaintenanceRequest(
            property_id=spintex.id, tenant_id=ama.id, issue_type="Plumbing",
            description="Burst pipe under the kitchen sink", urgency=Urgency.emergency.value,
            status=MaintenanceStatus.landlord_notified.value,
        ))

        db.commit()

        # --- compute & cache scores for Ama ---
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

        print("Seed complete.")
        print(f"  Admin    : admin@sahara.square / {ADMIN_PASSWORD}")
        print(f"  Landlord : kwame@example.com   / {DEMO_PASSWORD}")
        print(f"  Manager  : akua@example.com    / {DEMO_PASSWORD}")
        print(f"  Tenant   : ama@example.com     / {DEMO_PASSWORD}")
        print(f"  Ama readiness={readiness['readiness_pct']}% ({readiness['level']}), trust={trust['score']} ({trust['band']})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
