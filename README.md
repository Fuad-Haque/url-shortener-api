# URL Shortener API

<div align="center">

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Sora&weight=700&size=22&duration=2800&pause=1000&color=6C63FF&center=true&vCenter=true&width=700&lines=Shorten+URLs.+Track+Every+Click.;JWT+Auth+%C2%B7+Custom+Aliases+%C2%B7+Link+Expiry;FastAPI+%C2%B7+PostgreSQL+%C2%B7+Railway;Built+for+developers+who+ship+fast.)](https://git.io/typing-svg)

</div>

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)

</div>

---

## Overview

**URL Shortener API** is a production-grade link management service that goes beyond simple redirection. Register an account, create short URLs with optional custom aliases, set expiry windows, and track every click — all behind JWT-authenticated endpoints. Expired links return a proper `410 Gone` response. Every visit is timestamped. Every link belongs to exactly one user.

**Live API** → [web-production-5bd50.up.railway.app](https://web-production-5bd50.up.railway.app)  
**Swagger Docs** → [web-production-5bd50.up.railway.app/docs](https://web-production-5bd50.up.railway.app/docs)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Stack](#stack)
- [API Reference](#api-reference)
- [Auth Flow](#auth-flow)
- [Link Expiry](#link-expiry)
- [Click Tracking](#click-tracking)
- [Environment Variables](#environment-variables)
- [Quick Start](#quick-start)
- [Docker](#docker)
- [Project Structure](#project-structure)
- [Error Handling](#error-handling)
- [Author](#author)

---

## Features

| Feature | Detail |
|---------|--------|
| JWT Authentication | Secure register and login flow — all link management routes are protected behind Bearer token auth |
| URL Shortening | Submit any valid URL and receive a unique short code — instant redirect via `307 Temporary Redirect` |
| Custom Aliases | Optionally specify your own short code (e.g. `/my-launch`) instead of the auto-generated one |
| Link Expiry | Set an expiry window of 1–365 days at creation time — expired links return `410 Gone` automatically |
| Click Tracking | Every redirect is recorded with a visit timestamp — full click history available via `/stats/{short_code}` |
| Per-User Link Management | List, inspect, and delete only your own links — full ownership isolation enforced at the database level |
| Health Endpoint | `/health` for uptime monitoring and deployment readiness checks |
| Swagger / OpenAPI Docs | Full interactive API documentation auto-generated at `/docs` |

---

## Architecture

```
Browser / API Client
    │
    └── HTTP (REST) ──────────── FastAPI (Railway)
                                      │
                                 PostgreSQL ──── Users table (hashed passwords, JWT issuance)
                                      │
                                      ├──────── Links table (short_code, original_url, expiry, owner)
                                      │
                                      └──────── Clicks table (short_code, visited_at timestamps)
```

### Create Link Flow

```
POST /shorten  (Bearer token required)
    │
    ├── Validate JWT → resolve user_id
    ├── Validate destination URL (format + length)
    ├── Generate short_code (random 6-char or user-provided alias)
    ├── Check alias uniqueness — 409 if already taken
    ├── Compute expiry_at = now + expiry_days (if provided)
    └── Insert into PostgreSQL links table → return short URL
```

### Redirect Flow

```
GET /{short_code}
    │
    ├── Lookup short_code in links table
    ├── If not found → 404 Not Found
    ├── If expiry_at < now → 410 Gone
    ├── Insert click record (short_code, visited_at = now)
    └── 307 Temporary Redirect → original_url
```

---

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy (async), asyncpg |
| Authentication | JWT (python-jose), bcrypt password hashing (passlib) |
| Relational Database | PostgreSQL |
| Validation | Pydantic v2 |
| Deployment | Railway |
| API Documentation | Swagger UI — auto-generated via FastAPI |

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | No | Create a new user account |
| `POST` | `/auth/token` | No | Login with credentials — returns JWT access token |
| `POST` | `/shorten` | Yes | Create a short URL with optional alias and expiry |
| `GET` | `/{short_code}` | No | Redirect to the original URL (`307`) or return `410` if expired |
| `GET` | `/stats/{short_code}` | Yes | Retrieve link metadata and full click history |
| `GET` | `/my-links` | Yes | List all links belonging to the authenticated user |
| `DELETE` | `/links/{short_code}` | Yes | Delete a link and its associated click records |
| `GET` | `/health` | No | Health check — returns service and database status |

### Request / Response Examples

**Register**

```http
POST /auth/register
Content-Type: application/json

{
  "username": "fuad",
  "password": "securepassword"
}
```

```json
{
  "id": "a1b2...",
  "username": "fuad",
  "created_at": "2025-05-01T10:00:00Z"
}
```

**Login**

```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=fuad&password=securepassword
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Create a short URL**

```http
POST /shorten
Authorization: Bearer <token>
Content-Type: application/json

{
  "original_url": "https://example.com/very/long/path",
  "custom_alias": "my-launch",
  "expiry_days": 30
}
```

```json
{
  "short_code": "my-launch",
  "short_url": "https://web-production-5bd50.up.railway.app/my-launch",
  "original_url": "https://example.com/very/long/path",
  "expiry_at": "2025-05-31T10:00:00Z",
  "created_at": "2025-05-01T10:00:00Z"
}
```

**Get link stats**

```http
GET /stats/my-launch
Authorization: Bearer <token>
```

```json
{
  "short_code": "my-launch",
  "original_url": "https://example.com/very/long/path",
  "click_count": 47,
  "expiry_at": "2025-05-31T10:00:00Z",
  "created_at": "2025-05-01T10:00:00Z",
  "clicks": [
    { "visited_at": "2025-05-01T11:23:00Z" },
    { "visited_at": "2025-05-01T14:07:00Z" }
  ]
}
```

**List your links**

```http
GET /my-links
Authorization: Bearer <token>
```

```json
[
  {
    "short_code": "my-launch",
    "original_url": "https://example.com/very/long/path",
    "click_count": 47,
    "expiry_at": "2025-05-31T10:00:00Z",
    "created_at": "2025-05-01T10:00:00Z"
  }
]
```

---

## Auth Flow

JWT authentication is implemented using `python-jose` for token signing and `passlib[bcrypt]` for password hashing. Passwords are never stored in plaintext.

```
Registration → hash password (bcrypt) → store in users table
Login        → verify password hash → issue signed JWT (HS256, 30-min expiry)
Protected routes → extract Bearer token → decode + validate → resolve user_id
```

All protected endpoints reject requests with expired, malformed, or missing tokens with `401 Unauthorized`.

---

## Link Expiry

Expiry is optional. When `expiry_days` is supplied at creation time, `expiry_at` is computed as `now + expiry_days` and stored alongside the link record.

On every redirect request:

```
expiry_at IS NULL      → link is permanent → proceed to redirect
expiry_at > now        → link is active    → proceed to redirect
expiry_at <= now       → link is expired   → return 410 Gone
```

Expiry is enforced at redirect time — no background job or cron required.

---

## Click Tracking

Every successful redirect inserts a row into the `clicks` table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `short_code` | VARCHAR | Foreign key → links table |
| `visited_at` | TIMESTAMP | UTC timestamp of the redirect |

Click history is returned in full via `GET /stats/{short_code}`. The `click_count` field on list endpoints is computed via an aggregate — no denormalized counter column is maintained.

---

## Environment Variables

### Backend (`.env`)

```env
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname

# JWT
SECRET_KEY=your-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
APP_ENV=production
BASE_URL=https://web-production-5bd50.up.railway.app
```

A fully documented `.env.example` file is included in the repository.

---

## Quick Start

```bash
git clone https://github.com/Fuad-Haque/url-shortener-api
cd url-shortener-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set DATABASE_URL and SECRET_KEY
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000` — Swagger docs at `http://localhost:8000/docs`.

---

## Docker

```bash
git clone https://github.com/Fuad-Haque/url-shortener-api
cd url-shortener-api
cp .env.example .env
docker compose up -d
```

Services started:

| Service | Port | Notes |
|---------|------|-------|
| `postgres` | `5432` | Local PostgreSQL — replace with managed DB URL in production |

Run the backend after Docker services are healthy:

```bash
uvicorn app.main:app --reload
```

For a fully containerized local setup including the backend process:

```bash
docker compose --profile full up --build
```

---

## Project Structure

```
url-shortener-api/
├── app/
│   ├── main.py                  # FastAPI application entry point, CORS, lifespan hooks
│   ├── config.py                # Settings via pydantic-settings — reads from .env
│   ├── database.py              # Async SQLAlchemy session factory and engine setup
│   ├── models/
│   │   ├── user.py              # SQLAlchemy ORM model — users table
│   │   ├── link.py              # SQLAlchemy ORM model — links table (short_code, expiry, owner)
│   │   ├── click.py             # SQLAlchemy ORM model — clicks table (visit timestamps)
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py              # Register, login, JWT issuance
│   │   ├── links.py             # Shorten, list, delete, stats
│   │   └── redirect.py          # /{short_code} redirect handler with expiry check
│   ├── services/
│   │   ├── auth_service.py      # Password hashing, JWT creation and validation
│   │   ├── link_service.py      # Short code generation, alias uniqueness check, expiry logic
│   │   └── click_service.py     # Click insertion and aggregation queries
│   └── utils/
│       └── dependencies.py      # get_current_user FastAPI dependency (JWT → user_id)
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── Procfile
└── requirements.txt
```

---

## Error Handling

| Status Code | Scenario |
|-------------|----------|
| `200 OK` | Request processed successfully |
| `307 Temporary Redirect` | Valid short code — redirecting to original URL |
| `400 Bad Request` | Invalid URL format, expiry out of range, or missing required fields |
| `401 Unauthorized` | Missing, expired, or malformed JWT token |
| `403 Forbidden` | Authenticated user attempting to modify another user's link |
| `404 Not Found` | Short code does not exist |
| `409 Conflict` | Custom alias is already taken |
| `410 Gone` | Short code exists but has passed its expiry date |
| `422 Unprocessable Entity` | Request validation error (Pydantic) |
| `500 Internal Server Error` | Database connectivity issue or unhandled server error |

---

## Author

Built by [Fuad Haque](https://fuadhaque.com)

[fuadhaque.dev@gmail.com](mailto:fuadhaque.dev@gmail.com) · [Book a Call](https://cal.com/fuad-haque) · [GitHub](https://github.com/Fuad-Haque)
