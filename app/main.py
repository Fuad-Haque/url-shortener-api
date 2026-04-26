"""
URL Shortener — FastAPI application.

Endpoints
---------
POST   /auth/register        Register a new account
POST   /auth/token           Obtain a JWT (OAuth2 password flow)
GET    /auth/me              Get current user info
POST   /shorten              Create a short link          [auth required]
GET    /{short_code}         Redirect to original URL
GET    /stats/{short_code}   Link statistics              [auth required, owner only]
GET    /my-links             All links for current user   [auth required]
DELETE /links/{short_code}   Delete a link                [auth required, owner only]
GET    /health               Service health check
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models import (
    LinkResponse,
    LinkStats,
    ShortenRequest,
    Token,
    UserCreate,
    UserResponse,
)
from app.storage import (
    get_link_by_code,
    get_next_user_id,
    get_user_by_email,
    get_user_by_username,
    links_db,
    users_db,
    visits_db,
)
from app.utils import generate_short_code, is_expired, is_valid_url

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="URL Shortener API",
    description=(
        "A production-quality URL shortening service with JWT authentication, "
        "click tracking, custom aliases, and configurable link expiry."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------

def _log_creation(short_code: str, owner_username: str) -> None:
    print(
        f"[LINK CREATED] code={short_code!r} owner={owner_username!r} "
        f"ts={datetime.now(timezone.utc).isoformat()}"
    )


def _record_visit(short_code: str) -> None:
    if short_code in links_db:
        links_db[short_code]["clicks"] += 1
    if short_code not in visits_db:
        visits_db[short_code] = []
    visits_db[short_code].append(datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Helper: build a LinkResponse from a stored link dict
# ---------------------------------------------------------------------------

def _build_link_response(link: dict[str, Any]) -> LinkResponse:
    short_code = link["short_code"]
    active = not is_expired(link["expires_at"])
    return LinkResponse(
        short_code=short_code,
        short_url=f"{BASE_URL}/{short_code}",
        original_url=link["original_url"],
        clicks=link["clicks"],
        created_at=link["created_at"],
        expires_at=link["expires_at"],
        active=active,
        owner_username=link["owner_username"],
    )


# ===========================================================================
# Auth endpoints
# ===========================================================================


@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    tags=["auth"],
)
async def register(user_in: UserCreate) -> UserResponse:
    if get_user_by_username(user_in.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_in.username}' is already taken.",
        )

    if get_user_by_email(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user_in.email}' is already registered.",
        )

    uid = get_next_user_id()
    now = datetime.now(timezone.utc).isoformat()

    users_db[uid] = {
        "id": uid,
        "username": user_in.username,
        "email": user_in.email,
        "hashed_password": hash_password(user_in.password),
        "created_at": now,
    }

    return UserResponse(
        id=uid,
        username=user_in.username,
        email=user_in.email,
        created_at=now,
    )


@app.post(
    "/auth/token",
    response_model=Token,
    summary="Obtain a JWT access token (OAuth2 password flow)",
    tags=["auth"],
)
async def login(form: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = get_user_by_username(form.username)
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user["username"]})
    return Token(access_token=token, token_type="bearer")


@app.get(
    "/auth/me",
    response_model=UserResponse,
    summary="Get current user info",
    tags=["auth"],
)
async def me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        created_at=current_user["created_at"],
    )


# ===========================================================================
# Link management endpoints
# ===========================================================================


@app.post(
    "/shorten",
    response_model=LinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shortened URL",
    tags=["links"],
)
async def shorten(
    payload: ShortenRequest,
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> LinkResponse:
    if not is_valid_url(payload.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://.",
        )

    if payload.custom_alias:
        if payload.custom_alias in links_db:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Alias '{payload.custom_alias}' is already in use.",
            )
        short_code = payload.custom_alias
    else:
        for _ in range(10):
            candidate = generate_short_code()
            if candidate not in links_db:
                short_code = candidate
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate a unique short code. Please try again.",
            )

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=payload.expires_in_days)).isoformat()
    created_at = now.isoformat()

    link: dict[str, Any] = {
        "short_code": short_code,
        "original_url": payload.url,
        "owner_id": current_user["id"],
        "owner_username": current_user["username"],
        "clicks": 0,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    links_db[short_code] = link
    visits_db[short_code] = []

    background_tasks.add_task(_log_creation, short_code, current_user["username"])

    return _build_link_response(link)


@app.get(
    "/{short_code}",
    summary="Redirect to the original URL",
    tags=["redirect"],
    response_class=RedirectResponse,
    responses={
        307: {"description": "Redirect to the original URL"},
        404: {"description": "Short code not found"},
        410: {"description": "Link has expired"},
    },
)
async def redirect(
    short_code: str,
    background_tasks: BackgroundTasks,
) -> RedirectResponse:
    link = get_link_by_code(short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short code '{short_code}' not found.",
        )

    if is_expired(link["expires_at"]):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"This link expired on {link['expires_at']}.",
        )

    background_tasks.add_task(_record_visit, short_code)
    return RedirectResponse(url=link["original_url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get(
    "/stats/{short_code}",
    response_model=LinkStats,
    summary="Retrieve click statistics for a link (owner only)",
    tags=["links"],
)
async def stats(
    short_code: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> LinkStats:
    link = get_link_by_code(short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short code '{short_code}' not found.",
        )

    if link["owner_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view stats for this link.",
        )

    return LinkStats(
        short_code=short_code,
        original_url=link["original_url"],
        clicks=link["clicks"],
        created_at=link["created_at"],
        expires_at=link["expires_at"],
        active=not is_expired(link["expires_at"]),
        recent_visits=visits_db.get(short_code, []),
    )


@app.get(
    "/my-links",
    response_model=list[LinkResponse],
    summary="List all links created by the current user",
    tags=["links"],
)
async def my_links(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[LinkResponse]:
    owned = [
        link for link in links_db.values()
        if link["owner_id"] == current_user["id"]
    ]
    owned.sort(key=lambda lnk: lnk["created_at"], reverse=True)
    return [_build_link_response(lnk) for lnk in owned]


@app.delete(
    "/links/{short_code}",
    summary="Delete a short link (owner only)",
    tags=["links"],
)
async def delete_link(
    short_code: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    link = get_link_by_code(short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short code '{short_code}' not found.",
        )

    if link["owner_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this link.",
        )

    del links_db[short_code]
    visits_db.pop(short_code, None)

    return {"deleted": True, "short_code": short_code}


# ===========================================================================
# Health check
# ===========================================================================


@app.get(
    "/health",
    summary="Service health check",
    tags=["meta"],
)
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_links": len(links_db),
        "total_users": len(users_db),
    }