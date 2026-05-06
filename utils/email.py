"""
utils/email.py — send OTP emails via a Google Apps Script webhook.
"""
import logging

import requests

import config

log = logging.getLogger(__name__)


def send_email_otp(email: str, otp: str, name: str = "User") -> bool:
    """
    POST the OTP to the configured Google Apps Script webhook.

    Returns True on success, False on any failure.
    Does not raise — callers should treat False as a transient error.
    """
    if not config.GMAIL_SCRIPT_URL:
        log.warning("GMAIL_SCRIPT_URL not set — OTP email not sent to %s", email)
        return False

    try:
        response = requests.post(
            config.GMAIL_SCRIPT_URL,
            json={"to": email, "name": name, "otp": otp},
            timeout=15,
        )
        result = response.json()
        if result.get("success"):
            log.info("OTP sent to %s", email)
            return True
        log.error("Apps Script error for %s: %s", email, result.get("error"))
        return False
    except requests.exceptions.Timeout:
        log.error("OTP email timed out for %s", email)
        return False
    except Exception as exc:
        log.error("OTP email failed for %s: %s", email, exc)
        return False
