# Deploy MRSW RentConnect online — no terminal, no local commands

This puts the **whole app** (API + frontend + database) on the internet using only
web browsers. Render runs every build/start command on **its** servers, so you never
open a terminal on your machine.

The app is one service: FastAPI serves the REST API **and** the bundled frontend
(`static/index.html`) from the same URL. So there's no CORS to configure and nothing
to wire the frontend to — it just talks to whatever address it's served from.

---

## Step 1 — Put the code on GitHub (drag-and-drop, no git)

1. Unzip the project I gave you (double-click — that's not a command).
2. Go to **github.com → New repository**, name it `mrsw-rentconnect`, create it.
3. On the empty repo page, click **"uploading an existing file."**
4. Drag the **contents** of the `mrsw-backend` folder into the upload box —
   `render.yaml`, `requirements.txt`, the `app/` folder, and the `static/` folder
   should all sit at the **top level** of the repo. (GitHub keeps folder structure.)
5. Click **Commit changes.**

> The repo root must contain `render.yaml` and `app/` directly — not nested inside
> another `mrsw-backend/` folder.

## Step 2 — Create a free database on Neon (browser)

1. Go to **neon.tech**, sign up (free, no card).
2. Create a project (any name, pick a region near you).
3. Copy the **connection string** it shows — looks like
   `postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`.

> Why Neon and not Render's database: Render's free Postgres **deletes itself after
> 30 days**. Neon's free tier is permanent, so your demo won't vanish. (If you don't
> care, you can add a Render database instead — see the note at the bottom.)

## Step 3 — Deploy on Render (browser)

1. Go to **dashboard.render.com**, sign up (free, no card), connect your GitHub.
2. Click **New → Blueprint**, pick the `mrsw-rentconnect` repo.
3. Render reads `render.yaml` and asks for **DATABASE_URL** — paste the Neon string
   from Step 2. (SECRET_KEY is generated for you.)
4. Click **Apply.** Render installs dependencies and starts the app on its servers.
   First build takes a few minutes; watch the logs until it says it's live.

## Step 4 — Open it

Render gives you a URL like `https://mrsw-rentconnect.onrender.com`.

- Open it → the frontend loads.
- Sign in: **ama@example.com / password123** (seeded automatically on first boot).
- You'll see live readiness, wallet, and trust — served from Postgres.

API docs are at `…/docs`, health check at `…/healthz`.

That's it. No machine of yours was involved beyond a browser.

---

## Hostel marketplace (new endpoints)

Search and booking are now in the API. **Public** (no login): `GET /listings` with
optional `?university=`, `?q=`, `?room_type=`, `?max_price=` filters, and
`GET /listings/{id}`. **Landlords**: `POST /listings` to list a hostel,
`GET /listings/mine`. **Booking** (any signed-in user): `POST /bookings`,
`GET /bookings/me`; owners use `GET /bookings/incoming` and
`PATCH /bookings/{id}/status` to confirm or cancel.

When you redeploy this version, it **auto-upgrades your existing database**: it adds
the new listing columns (`ADD COLUMN IF NOT EXISTS`) and seeds ~6 campus hostels
(UG, KNUST, UCC, UPSA) the first time it sees an empty listings table — no shell, no
DB reset. Photos are placeholder URLs for now; real photo **upload** needs object
storage (R2/S3/Supabase) and is the next infra step. Try it after deploy:
`GET /listings?university=KNUST` in `/docs`.

## Things worth knowing

- **Python version is pinned to 3.12** via the `.python-version` file in the repo
  root. Don't remove it: Render otherwise defaults to the newest Python (3.14+),
  for which `pydantic-core` has no prebuilt wheel yet — pip then tries to compile it
  from source, there's no Rust toolchain, and the build fails with
  `metadata-generation-failed → pydantic-core`. If you ever hit that, confirm
  `.python-version` exists and reads `3.12` (or set `PYTHON_VERSION=3.12.8` in the
  service's Environment tab).
- **Free web services sleep** after ~15 minutes idle. The next visit triggers a
  ~30–60s cold start, then it's fast again. Fine for demos; upgrade to a paid
  instance (currently ~$7/mo) for always-on.
- **Updating the app:** edit a file on GitHub (web UI) or upload a new version —
  Render redeploys automatically.
- **Turning off auto-seed:** once you don't want demo data re-checked on every boot,
  set `SEED_ON_START=false` in the Render service's Environment tab. (It's already
  idempotent, so it won't duplicate anything.)
- **Before this is "real" (not a demo):** set `AUTO_CREATE_TABLES=false` and use
  Alembic migrations; restrict `CORS_ORIGINS` if you ever split the frontend off;
  don't custody tenant funds without the licensing the spec calls out.

### Alternative: use Render's own Postgres instead of Neon

If you'd rather keep everything on Render (accepting the 30-day expiry), add this to
the bottom of `render.yaml` and change `DATABASE_URL` to reference it instead of
`sync: false`:

```yaml
databases:
  - name: mrsw-db
    plan: free

# and replace the DATABASE_URL env var with:
      - key: DATABASE_URL
        fromDatabase:
          name: mrsw-db
          property: connectionString
```
