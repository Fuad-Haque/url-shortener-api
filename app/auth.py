"""
Authentication utilities: password hashing, JWT creation/verification,
and the FastAPI dependency that guards protected endpoints.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Configuration — pulled from environment with safe development fallbacks
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.getenv(
    "SECRET_KEY",
    "dev-secret-key-change-in-production-please-use-a-long-random-string",
)
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

# ---------------------------------------------------------------------------
# Passlib context
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# OAuth2 scheme
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    """Return **True** if *plain* matches *hashed*."""
    return pwd_context.verify(plain[:72], hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(data: dict[str, Any]) -> str:
    """
    Encode *data* into a signed JWT.

    A copy of *data* is made so the caller's dict is never mutated.
    The ``exp`` claim is set to *now + ACCESS_TOKEN_EXPIRE_MINUTES*.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    Decode the Bearer JWT and return the stored user dict.

    Raises **HTTP 401** when the token is missing, malformed, expired,
    or references a user that no longer exists.
    """
    # Import here to avoid a circular dependency between auth ↔ storage
    from app.storage import get_user_by_username  # noqa: PLC0415

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception

    return user