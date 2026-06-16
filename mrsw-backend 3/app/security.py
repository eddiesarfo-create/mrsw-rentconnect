"""Password hashing, JWT issuance/validation, and auth dependencies."""
from __future__ import annotations

import datetime

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .database import get_db

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


# ---- passwords (bcrypt directly; 72-byte input cap) ----

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ---- tokens ----

def create_access_token(user: "models.User") -> str:
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user.id), "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> "models.User":
    if creds is None:
        raise _CREDENTIALS_EXC
    try:
        payload = jwt.decode(creds.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user_id = int(payload.get("sub"))
    except Exception:
        raise _CREDENTIALS_EXC
    user = db.get(models.User, user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    return user


def require_role(*roles: str):
    """Dependency factory enforcing one of the given roles."""
    def dependency(user: "models.User" = Depends(get_current_user)) -> "models.User":
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return dependency
