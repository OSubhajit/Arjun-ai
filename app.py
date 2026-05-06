"""
app.py — Flask application factory.

Kept intentionally slim: config validation → DB init → app creation → blueprint registration.
All route logic lives in blueprints/.
"""
import sys
from datetime import timedelta

import config
import extensions
from extensions import setup_logging

# ── 1. Logging (must be first) ────────────────────────────────────────────────
setup_logging(debug=not config.IS_PROD)

# ── 2. Config validation (exits on fatal misconfiguration) ───────────────────
config.validate()

# ── 3. Database ───────────────────────────────────────────────────────────────
extensions.init_db(config.MONGO_URI)

# ── 4. Flask app ──────────────────────────────────────────────────────────────
from flask import Flask  # noqa: E402  (import after logging is configured)

app = Flask(__name__)
app.secret_key                        = config.SECRET_KEY
app.config["SESSION_COOKIE_SECURE"]   = config.IS_PROD
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# ── 5. Inject AdSense pub ID into every template context ─────────────────────
@app.context_processor
def inject_globals():
    return {"adsense_pub_id": config.ADSENSE_PUB_ID}


# ── 6. Security headers ───────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"]        = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://pagead2.googlesyndication.com "
        "https://partner.googleadservices.com https://tpc.googlesyndication.com "
        "https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-src https://googleads.g.doubleclick.net https://tpc.googlesyndication.com;"
    )
    return response


# ── 7. Blueprints ─────────────────────────────────────────────────────────────
from blueprints.auth.routes    import auth_bp     # noqa: E402
from blueprints.chat.routes    import chat_bp     # noqa: E402
from blueprints.profile.routes import profile_bp  # noqa: E402
from blueprints.main.routes    import main_bp     # noqa: E402

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(profile_bp)


# ── 8. Dev entry-point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import logging
    log = logging.getLogger(__name__)
    try:
        log.info("Starting dev server on port %s", config.PORT)
        app.run(host="0.0.0.0", port=config.PORT, debug=not config.IS_PROD)
    except Exception as exc:
        log.critical("Startup error: %s", exc)
        sys.exit(1)
