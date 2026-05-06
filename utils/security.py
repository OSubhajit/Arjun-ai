"""
utils/security.py — CSRF token management, rate limiting, OTP helpers.
"""
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import request, session

from extensions import otp_col, rate_col

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


# ── Email validation ──────────────────────────────────────────────────────────

def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


# ── IP helpers ────────────────────────────────────────────────────────────────

def get_client_ip() -> str:
    """Return real client IP, honouring Render/proxy X-Forwarded-For header."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "unknown"


# ── CSRF ──────────────────────────────────────────────────────────────────────

def generate_csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf() -> bool:
    token  = request.headers.get("X-CSRF-Token", "")
    stored = session.get("csrf_token", "")
    if not token or not stored:
        return False
    return hmac.compare_digest(token, stored)


# ── Rate limiting ─────────────────────────────────────────────────────────────

def is_rate_limited(ip: str, max_calls: int = 3, window_sec: int = 600) -> bool:
    """OTP send limiter — 3 requests per 10 minutes per IP."""
    return _check_rate(ip, max_calls, window_sec)


def is_login_rate_limited(ip: str) -> bool:
    """Login attempt limiter — 10 attempts per 15 minutes per IP."""
    return _check_rate(f"login:{ip}", max_calls=10, window_sec=900)


def is_chat_rate_limited(email: str, max_calls: int = 20, window_sec: int = 60) -> bool:
    """Chat message limiter — 20 messages per minute per user account."""
    return _check_rate(f"chat:{email}", max_calls=max_calls, window_sec=window_sec)


def _check_rate(key: str, max_calls: int, window_sec: int) -> bool:
    now          = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_sec)
    count = rate_col.count_documents({"ip": key, "created_at": {"$gte": window_start}})
    if count >= max_calls:
        return True
    rate_col.insert_one({
        "ip"        : key,
        "created_at": now,
        "expires_at": now + timedelta(seconds=window_sec),
    })
    return False


# ── OTP helpers ───────────────────────────────────────────────────────────────

def generate_otp() -> str:
    """Cryptographically secure 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)


def verify_otp_value(stored: str, provided: str) -> bool:
    if not stored or not provided:
        return False
    return hmac.compare_digest(str(stored), str(provided))


def otp_save(email: str, data: dict) -> None:
    data["email"]      = email
    data["expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=10)
    data.setdefault("attempts", 0)
    otp_col.replace_one({"email": email}, data, upsert=True)


def otp_get(email: str) -> dict | None:
    doc = otp_col.find_one({"email": email})
    if not doc:
        return None
    expires_at = doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        otp_col.delete_one({"email": email})
        return None
    return doc


def otp_delete(email: str) -> None:
    otp_col.delete_one({"email": email})


def otp_record_failed_attempt(email: str) -> int:
    result = otp_col.find_one_and_update(
        {"email": email},
        {"$inc": {"attempts": 1}},
        return_document=True,
    )
    return result["attempts"] if result else 999
