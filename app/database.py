"""SQLAlchemy engine, session factory and the FastAPI DB dependency."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()


def _normalize(url: str) -> str:
    """Hosts like Render/Neon/Heroku hand out `postgres://` (and bare `postgresql://`);
    SQLAlchemy 2.0 needs an explicit driver. Pin psycopg2 either way."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


engine = create_engine(_normalize(settings.database_url), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """Yield a request-scoped session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
