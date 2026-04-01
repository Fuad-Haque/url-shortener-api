"""
Stateless utility helpers used across the application.
"""

from __future__ import annotations

import random
import re
import string
from datetime import datetime, timezone

# Only uppercase letters + digits to keep codes unambiguous (no l/1/O/0 confusion)
_ALPHABET = string.ascii_uppercase + string.digits
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def generate_short_code(length: int = 6) -> str:
    """
    Return a random alphanumeric code of *length* characters.

    Uses ``random.choices`` (uniform distribution) which is fast and
    sufficient for non-cryptographic short-code generation.

    >>> len(generate_short_code())
    6
    >>> all(c in _ALPHABET for c in generate_short_code())
    True
    """
    return "".join(random.choices(_ALPHABET, k=length))


def is_valid_url(url: str) -> bool:
    """
    Return **True** when *url* starts with ``http://`` or ``https://``.

    This is an intentionally lightweight check — Pydantic handles deeper
    URL validation in the request model; this helper is used for quick
    runtime guards.

    >>> is_valid_url("https://example.com")
    True
    >>> is_valid_url("ftp://example.com")
    False
    >>> is_valid_url("example.com")
    False
    """
    return bool(_URL_RE.match(url))


def is_expired(expires_at: str) -> bool:
    """
    Return **True** when the ISO-8601 UTC timestamp *expires_at* is in the past.

    *expires_at* is expected to be produced by
    ``datetime.now(timezone.utc).isoformat()``, so it always carries
    timezone information.

    >>> from datetime import timedelta
    >>> past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    >>> is_expired(past)
    True
    >>> future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    >>> is_expired(future)
    False
    """
    expiry = datetime.fromisoformat(expires_at)
    return datetime.now(timezone.utc) > expiry