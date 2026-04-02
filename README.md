# URL Shortener API

Full-featured URL shortening service with authentication, click tracking,
and link expiry. Built with FastAPI, deployed on Railway.

**Live URL:** https://web-production-5bd50.up.railway.app
**Docs:** https://web-production-5bd50.up.railway.app/docs
**Tech:** Python · FastAPI · JWT · Pydantic · Railway

## Features

- JWT authentication (register, login, protected routes)
- Create short URLs with optional custom aliases
- Set expiry dates on links (1–365 days)
- Click tracking with visit timestamps
- Automatic redirect with 307 status
- 410 Gone response for expired links
- Per-user link management

## Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/register | No | Create account |
| POST | /auth/token | No | Login, get JWT |
| POST | /shorten | Yes | Create short URL |
| GET | /{short_code} | No | Redirect to original |
| GET | /stats/{short_code} | Yes | Link stats + clicks |
| GET | /my-links | Yes | All your links |
| DELETE | /links/{short_code} | Yes | Delete a link |
| GET | /health | No | Health check |

## Run Locally

```bash
git clone https://github.com/Fuad-Haque/url-shortener-api
cd url-shortener-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your SECRET_KEY
uvicorn app.main:app --reload