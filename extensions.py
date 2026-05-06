"""
extensions.py — initialise shared resources (MongoDB, logging).

All blueprints import `db`, `users_col`, `otp_col`, `rate_col` from here.
"""
import logging
import sys
import traceback

from pymongo import MongoClient, ASCENDING
from pymongo.errors import OperationFailure

# ── Logging setup ─────────────────────────────────────────────────────────────
# Call setup_logging() once in app.py before anything else.

def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Quieten noisy third-party loggers
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


log = logging.getLogger(__name__)

# ── MongoDB ───────────────────────────────────────────────────────────────────
# These are module-level names; they're populated by init_db().
client     = None
db         = None
users_col  = None
otp_col    = None
rate_col   = None


def init_db(mongo_uri: str) -> None:
    """Connect to MongoDB and ensure all indexes exist. Exits on failure."""
    global client, db, users_col, otp_col, rate_col  # noqa: PLW0603

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        log.info("MongoDB connected")
    except Exception as exc:
        log.critical("MongoDB connection failed: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    db        = client["OSubhajit"]
    users_col = db["users"]
    otp_col   = db["otp_store"]
    rate_col  = db["rate_limits"]

    _ensure_indexes()


def _ensure_indexes() -> None:
    """Create indexes idempotently; log warnings, never crash."""
    _safe_index(lambda: users_col.create_index("email", unique=True, background=True),
                "unique email index")
    _safe_index(
        lambda: otp_col.create_index(
            [("expires_at", ASCENDING)], expireAfterSeconds=0, background=True
        ),
        "OTP TTL index",
    )
    _safe_index(
        lambda: rate_col.create_index(
            [("expires_at", ASCENDING)], expireAfterSeconds=0, background=True
        ),
        "rate-limit TTL index",
    )


def _safe_index(fn, label: str) -> None:
    try:
        fn()
        log.info("%s ready", label)
    except OperationFailure as exc:
        log.warning("%s warning: %s", label, exc)
    except Exception as exc:
        log.warning("%s error: %s", label, exc)
