"""
config.py — single source of truth for all environment config.
"""
import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ── Core ──────────────────────────────────────────────────────────────────────
API_KEY    = os.getenv("OPENROUTER_API_KEY")
MONGO_URI  = os.getenv("MONGO_URI")
SECRET_KEY = os.getenv("SECRET_KEY")
IS_PROD    = os.getenv("RENDER") == "true"
AI_MODEL   = os.getenv("AI_MODEL", "openai/gpt-3.5-turbo")
PORT       = int(os.getenv("PORT", 5000))

# ── AdSense (only set if you have an account — blank disables the tag) ────────
ADSENSE_PUB_ID = os.getenv("ADSENSE_PUB_ID", "")  # e.g. "ca-pub-XXXXXXXXXXXXXXXX"

# ── Gmail OTP webhook ─────────────────────────────────────────────────────────
GMAIL_SCRIPT_URL = os.getenv("GMAIL_SCRIPT_URL", "")

# ── Validation on startup ─────────────────────────────────────────────────────

def validate():
    """Call once at startup. Exits the process on fatal misconfiguration."""
    global SECRET_KEY  # noqa: PLW0603

    if not SECRET_KEY:
        if IS_PROD:
            log.critical("FATAL: SECRET_KEY env var not set — refusing to start in production")
            sys.exit(1)
        SECRET_KEY = "dev_only_not_for_production"
        log.warning("Using dev SECRET_KEY. Set SECRET_KEY env var before deploying.")

    if not MONGO_URI:
        log.critical("FATAL: MONGO_URI not set — exiting")
        sys.exit(1)

    log.info("=== STARTUP ===")
    log.info("MONGO_URI        : %s", "set" if MONGO_URI else "MISSING")
    log.info("API_KEY          : %s", "set" if API_KEY else "MISSING")
    log.info("AI_MODEL         : %s", AI_MODEL)
    log.info("ADSENSE_PUB_ID   : %s", ADSENSE_PUB_ID or "(not set — ads disabled)")
    log.info("GMAIL_SCRIPT_URL : %s", "set" if GMAIL_SCRIPT_URL else "(not set — OTP email disabled)")
    log.info("IS_PROD          : %s", IS_PROD)
    log.info("===============")

# ── Language registry ─────────────────────────────────────────────────────────

ALLOWED_LANGS = {
    # Indian
    "en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "or", "as", "ur",
    # European
    "es", "fr", "de", "it", "pt", "ru", "nl", "pl", "sv", "no", "da", "fi",
    "el", "ro", "cs", "hu", "uk", "tr", "sr", "hr", "sk", "bg",
    # Asian / Pacific
    "ja", "ko", "zh", "id", "ms", "th", "vi", "ar", "fa", "he", "ne", "si",
    # African
    "sw", "af",
}

LANGUAGE_NAMES = {
    "en": "English",      "hi": "Hindi",         "bn": "Bengali",
    "ta": "Tamil",        "te": "Telugu",        "mr": "Marathi",
    "gu": "Gujarati",     "kn": "Kannada",       "ml": "Malayalam",
    "pa": "Punjabi",      "or": "Odia",          "as": "Assamese",
    "ur": "Urdu",         "es": "Spanish",       "fr": "French",
    "de": "German",       "it": "Italian",       "pt": "Portuguese",
    "ru": "Russian",      "nl": "Dutch",         "pl": "Polish",
    "sv": "Swedish",      "no": "Norwegian",     "da": "Danish",
    "fi": "Finnish",      "el": "Greek",         "ro": "Romanian",
    "cs": "Czech",        "hu": "Hungarian",     "uk": "Ukrainian",
    "tr": "Turkish",      "sr": "Serbian",       "hr": "Croatian",
    "sk": "Slovak",       "bg": "Bulgarian",     "ja": "Japanese",
    "ko": "Korean",       "zh": "Chinese",       "id": "Indonesian",
    "ms": "Malay",        "th": "Thai",          "vi": "Vietnamese",
    "ar": "Arabic",       "fa": "Persian",       "he": "Hebrew",
    "ne": "Nepali",       "si": "Sinhala",       "sw": "Swahili",
    "af": "Afrikaans",
}


def get_lang_instruction(lang: str) -> str | None:
    """Return a system-prompt instruction for the given language, or None for English."""
    if lang == "en":
        return None
    name = LANGUAGE_NAMES.get(lang, lang)
    return (
        f"IMPORTANT: Respond entirely in {name}. "
        f"Keep all Sanskrit shlokas in their original Sanskrit script, "
        f"but provide their meaning and explanation in {name}."
    )
