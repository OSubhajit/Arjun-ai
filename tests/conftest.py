"""
tests/conftest.py — shared pytest fixtures.

Uses a real in-memory mongomock database so no live MongoDB is needed.
"""
import os
import pytest

# ── Point at a safe test environment before any app code runs ────────────────
os.environ.setdefault("MONGO_URI",            "mongodb://localhost:27017/test_arjun")
os.environ.setdefault("SECRET_KEY",           "test-secret-key-not-for-production")
os.environ.setdefault("OPENROUTER_API_KEY",   "test-api-key")
os.environ.setdefault("GMAIL_SCRIPT_URL",     "")
os.environ.setdefault("RENDER",               "")   # force dev mode


@pytest.fixture(scope="session")
def app():
    """Create a Flask test application with an isolated mongomock database."""
    import mongomock

    # Patch MongoClient before app imports so extensions.init_db() gets a mock
    with mongomock.patch(servers=(("localhost", 27017),)):
        from app import app as flask_app
        flask_app.config.update({
            "TESTING"                : True,
            "WTF_CSRF_ENABLED"       : False,
            "SESSION_COOKIE_SECURE"  : False,
        })
        yield flask_app


@pytest.fixture()
def client(app):
    """Return a Flask test client with a fresh request context."""
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture()
def csrf_client(client):
    """Test client that automatically fetches and injects CSRF tokens."""
    res   = client.get("/api/csrf-token")
    token = res.get_json()["csrf_token"]

    class CSRFClient:
        def post(self, url, json=None, **kwargs):
            headers = kwargs.pop("headers", {})
            headers["X-CSRF-Token"] = token
            return client.post(url, json=json, headers=headers, **kwargs)

        def delete(self, url, **kwargs):
            headers = kwargs.pop("headers", {})
            headers["X-CSRF-Token"] = token
            return client.delete(url, headers=headers, **kwargs)

        def get(self, url, **kwargs):
            return client.get(url, **kwargs)

    return CSRFClient()


@pytest.fixture()
def registered_user(csrf_client):
    """Register a user and return their credentials for use in other tests."""
    email    = "test@gitapath.dev"
    password = "Test@12345"
    name     = "Test Arjun"

    # Step 1: send OTP (mocked — GMAIL_SCRIPT_URL is empty so send silently fails,
    # but we can bypass by inserting the OTP record directly)
    import bcrypt
    from extensions import otp_col, users_col

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    from datetime import datetime, timedelta, timezone
    otp_col.replace_one(
        {"email": email},
        {
            "email"     : email,
            "otp"       : "123456",
            "name"      : name,
            "password"  : hashed,
            "type"      : "register",
            "attempts"  : 0,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        upsert=True,
    )

    # Step 2: verify OTP
    res = csrf_client.post("/register", json={"action": "verify_otp", "email": email, "otp": "123456"})
    assert res.status_code == 200
    assert res.get_json()["success"]

    return {"email": email, "password": password, "name": name}


@pytest.fixture()
def logged_in_client(csrf_client, registered_user):
    """Return a csrf_client already authenticated as registered_user."""
    res = csrf_client.post("/login", json={
        "email"   : registered_user["email"],
        "password": registered_user["password"],
    })
    assert res.get_json()["success"]
    return csrf_client, registered_user
