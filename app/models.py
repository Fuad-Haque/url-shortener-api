"""
Pydantic models for the URL Shortener API.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, description="At least 3 characters")
    email: EmailStr
    password: str = Field(..., min_length=8, description="At least 8 characters")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Link models
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class ShortenRequest(BaseModel):
    url: str = Field(..., description="Must start with http:// or https://")
    custom_alias: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=20,
        description="Optional custom short code (3–20 chars)",
    )
    expires_in_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Link TTL in days (1–365, default 30)",
    )

    @field_validator("url")
    @classmethod
    def url_must_have_scheme(cls, v: str) -> str:
        if not _URL_RE.match(v):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("custom_alias")
    @classmethod
    def alias_alphanumeric(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError(
                "custom_alias may only contain letters, digits, hyphens, or underscores"
            )
        return v


class LinkResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    clicks: int
    created_at: str
    expires_at: str
    active: bool
    owner_username: str


class LinkStats(BaseModel):
    short_code: str
    original_url: str
    clicks: int
    created_at: str
    expires_at: str
    active: bool
    recent_visits: list[str]  # ISO-8601 timestamps