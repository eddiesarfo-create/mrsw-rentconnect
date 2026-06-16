# MRSW RentConnect — Backend (FastAPI + PostgreSQL)

The API foundation for the Micro Rent Stability Wallet: tenant savings wallet,
rent-readiness + housing-trust scoring, properties, leases, maintenance, and an
admin layer. Rules-first scoring (swap for ML later behind the same interface).

## Stack

- **FastAPI** (REST, OpenAPI docs at `/docs`)
- **PostgreSQL** via **SQLAlchemy 2.0** (sync)
- **JWT** bearer auth (`PyJWT`) with `bcrypt` password hashing
- Role-based access: `tenant`, `landlord`, `manager`, `admin`

## Quick start

```bash
# 1. Postgres (Docker)
docker compose up -d            # starts postgres on :5432

# 2. Python env
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Config
cp .env.example .env            # adjust SECRET_KEY etc.

# 4. Create tables + demo data
python -m app.seed

# 5. Run
uvicorn app.main:app --reload
```

Then open **http://localhost:8000** — the backend serves the bundled frontend
(`static/index.html`) at the root, with API docs at `/docs`. Sign in with the seeded
tenant below. (No separate frontend server needed; the page calls the same origin.)

No Docker? Point `DATABASE_URL` at any Postgres instance and run steps 2–5.

### Put it online (no terminal)

See **DEPLOY.md** — upload to GitHub and click Apply on a Render Blueprint
(`render.yaml`). One free service serves the API and frontend together; a free Neon
Postgres holds the data; it seeds itself on first boot.

## Seeded logins

| Role     | Email                | Password      |
|----------|----------------------|---------------|
| Admin    | admin@sahara.square  | `admin123`    |
| Landlord | kwame@example.com    | `password123` |
| Manager  | akua@example.com     | `password123` |
| Tenant   | ama@example.com      | `password123` |

Ama is seeded ~42% rent-ready (GHS 3,360 of 8,000) with a housing-trust score in
the "Fair" band — the same story as the prototype.

## Auth flow

1. `POST /auth/login` with `{ "email", "password" }` → `{ access_token }`
2. Send `Authorization: Bearer <token>` on every protected call
   (in Swagger: **Authorize** → paste the token).

## API map

**Auth** — `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
**Tenant** — `GET /tenants/me` (profile + live trust + readiness)
**Wallet** — `GET /wallet`, `GET /wallet/transactions`, `POST /wallet/credit` *(admin)*
**Plans** — `POST /plans`, `GET /plans/me`, `GET /plans/projection?amount=&frequency=`
**Properties** — `POST /properties` *(landlord)*, `GET /properties`, `GET /properties/{id}`
**Leases** — `POST /leases` *(landlord)*, `GET /leases/me` *(tenant)*, `GET /leases` *(landlord)*
**Maintenance** — `POST /maintenance` *(tenant, auto-triaged)*, `GET /maintenance`, `PATCH /maintenance/{id}/status`
**Admin** — `GET /admin/overview`, `GET /admin/risk`, `GET /admin/approvals`, `POST /admin/users/{id}/approve`

### Try it

```bash
TOKEN=$(curl -s localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"ama@example.com","password":"password123"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s localhost:8000/wallet -H "Authorization: Bearer $TOKEN"
curl -s "localhost:8000/plans/projection?amount=273&frequency=weekly" -H "Authorization: Bearer $TOKEN"
```

## Scoring (app/scoring.py)

- **Readiness** → `green / yellow / orange / red` + percentage, factoring balance
  vs target, runway, and failed deductions.
- **Trust (0–100)** → weighted across 8 factors (consistency, payment history,
  failed deductions, wallet growth, maintenance behaviour, landlord review,
  disputes, guarantor strength).
- **Property health (0–100)** → response time, unresolved complaints, inspection
  results, satisfaction, safety.

## Data model

All 19 spec tables exist in `app/models.py`: users, tenants, landlords,
properties, leases, wallets, wallet_transactions, contribution_plans,
rent_payments, risk_scores, trust_scores, maintenance_requests, inspections,
damage_reports, disputes, guarantors, notifications, admin_users, audit_logs.

## What's wired vs. next

**Wired:** auth + roles, tenant wallet + ledger, contribution plans + projection,
readiness + trust scoring, properties, leases, maintenance (with rules-based
triage), admin overview / risk / approvals, audit logging on sensitive actions,
seed data.

**Modelled, endpoints still to add:** inspections + damage→Property-Protection
deduction, disputes, rent_payments collection lifecycle, notifications,
guarantor management, e-sign artifacts.

**Production hardening (deliberately deferred):**
- **Migrations** — this uses `create_all` for speed; add **Alembic** before prod.
- **Payments** — MoMo / bank / PSP integration (MVP credits wallets via admin).
  Per the spec, Sahara Square should not hold customer funds without a licence —
  keep balances with a licensed partner.
- Refresh tokens / token rotation, rate limiting, request validation hardening.
- Async SQLAlchemy + connection pooling tuning if/when throughput demands it.

## Deploy notes

- Set a strong `SECRET_KEY` and a locked-down `CORS_ORIGINS`.
- Set `AUTO_CREATE_TABLES=false` and run Alembic migrations instead.
- Run under a process manager: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
  (or `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`).
- Works on any Postgres host (AWS RDS, Cloud SQL, Neon, Supabase, etc.).
