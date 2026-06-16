"""MRSW RentConnect API entrypoint."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, engine
from .routers import admin, auth, leases, maintenance, plans, properties, tenants, wallet

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.seed_on_start:
        # Populate the demo dataset on first boot so no shell command is needed.
        # seed() is idempotent — it no-ops once users exist.
        try:
            from .seed import seed
            seed()
        except Exception as exc:  # never let seeding crash startup
            print("Seed skipped:", exc)
    yield


app = FastAPI(
    title="MRSW RentConnect API",
    version="0.1.0",
    description="Micro Rent Stability Wallet — landlord & tenant rental stability platform.",
    lifespan=lifespan,
)

_origins = ["*"] if settings.cors_origins.strip() == "*" else [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["meta"])
def healthz():
    return {"service": "MRSW RentConnect API", "status": "ok", "docs": "/docs"}


for r in (auth, tenants, wallet, plans, properties, leases, maintenance, admin):
    app.include_router(r.router)

# Serve the bundled frontend (static/index.html) from the same origin, if present.
# Mounted last so it only catches paths the API routers and /docs didn't handle.
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="frontend")
