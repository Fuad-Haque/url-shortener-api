"""
In-memory storage layer.

Production deployments should swap these dicts for a proper database.
All state lives at module level so it persists for the lifetime of the
process (suitable for the portfolio demo and local testing).
"""

from __future__ import annotations

from typing import Any, Optional

# ---------------------------------------------------------------------------
# Data stores
# ---------------------------------------------------------------------------

# user_id (int) → {id, username, email, hashed_password, created_at}
users_db: dict[int, dict[str, Any]] = {}

# short_code (str) → {short_code, original_url, owner_id, owner_username,
#                      clicks, created_at, expires_at}
links_db: dict[str, dict[str, Any]] = {}

# short_code (str) → [ISO-8601 timestamp strings]
visits_db: dict[str, list[str]] = {}

# Auto-increment counter for user primary keys
_next_user_id: int = 1


# ---------------------------------------------------------------------------
# Counter helper (keeps the mutable int accessible from other modules)
# ---------------------------------------------------------------------------

def get_next_user_id() -> int:
    """Return the current counter value and advance it by 1."""
    global _next_user_id
    uid = _next_user_id
    _next_user_id += 1
    return uid


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    """
    Linear scan of *users_db* for a matching username.

    Returns the user dict or **None** if not found.
    Case-sensitive to match what was registered.
    """
    for user in users_db.values():
        if user["username"] == username:
            return user
    return None


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    """
    Linear scan of *users_db* for a matching email address.

    Comparison is case-insensitive (email addresses are case-insensitive
    per RFC 5321 local-part convention in practice).
    """
    email_lower = email.lower()
    for user in users_db.values():
        if user["email"].lower() == email_lower:
            return user
    return None


def get_link_by_code(short_code: str) -> Optional[dict[str, Any]]:
    """Return the link dict for *short_code*, or **None** if absent."""
    return links_db.get(short_code)