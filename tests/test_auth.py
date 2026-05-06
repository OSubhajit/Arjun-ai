"""
tests/test_auth.py — login, register (OTP flow), forgot-password, logout.
"""
import pytest


class TestCSRFEndpoint:
    def test_returns_token(self, client):
        res = client.get("/api/csrf-token")
        assert res.status_code == 200
        data = res.get_json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) == 64  # 32-byte hex


class TestLogin:
    def test_get_renders_page(self, client):
        res = client.get("/login")
        assert res.status_code == 200
        assert b"GitaPath" in res.data

    def test_missing_csrf_rejected(self, client):
        res = client.post(
            "/login",
            json={"email": "a@b.com", "password": "password123"},
            headers={},  # no X-CSRF-Token
        )
        assert res.status_code == 403

    def test_invalid_credentials(self, csrf_client):
        res = csrf_client.post("/login", json={
            "email": "nobody@example.com", "password": "wrongpassword",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert not data["success"]
        assert "Invalid" in data["message"]

    def test_invalid_email_format(self, csrf_client):
        res = csrf_client.post("/login", json={
            "email": "not-an-email", "password": "password123",
        })
        data = res.get_json()
        assert not data["success"]

    def test_successful_login(self, logged_in_client):
        _, user = logged_in_client
        assert user["email"] == "test@gitapath.dev"


class TestRegister:
    def test_get_renders_page(self, client):
        res = client.get("/register")
        assert res.status_code == 200

    def test_verify_wrong_otp(self, csrf_client, registered_user):
        """After registration, verifying with wrong OTP decrements attempts."""
        from datetime import datetime, timedelta, timezone
        from extensions import otp_col
        # Plant a fresh OTP for a separate email
        otp_col.replace_one(
            {"email": "fresh@gitapath.dev"},
            {
                "email": "fresh@gitapath.dev", "otp": "999999",
                "name": "Fresh", "password": "hashed",
                "type": "register", "attempts": 0,
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            upsert=True,
        )
        res  = csrf_client.post("/register", json={
            "action": "verify_otp", "email": "fresh@gitapath.dev", "otp": "000000",
        })
        data = res.get_json()
        assert not data["success"]
        assert "attempt" in data["message"].lower()

    def test_duplicate_registration_rejected(self, csrf_client, registered_user):
        """Trying to register with an already-registered email returns an error."""
        from datetime import datetime, timedelta, timezone
        from extensions import otp_col
        otp_col.replace_one(
            {"email": registered_user["email"]},
            {
                "email": registered_user["email"], "otp": "111111",
                "name": "Dup", "password": "x",
                "type": "register", "attempts": 0,
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            upsert=True,
        )
        res  = csrf_client.post("/register", json={
            "action": "verify_otp",
            "email" : registered_user["email"],
            "otp"   : "111111",
        })
        data = res.get_json()
        assert not data["success"]


class TestLogout:
    def test_logout_clears_session(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.post("/logout")
        assert res.get_json()["success"]

    def test_logout_without_csrf_rejected(self, client):
        res = client.post("/logout")
        assert res.status_code == 403


class TestForgotPassword:
    def test_send_otp_always_returns_success(self, csrf_client):
        """Forgot-password never reveals whether email exists."""
        res  = csrf_client.post("/forgot", json={"action": "send_otp", "email": "nobody@example.com"})
        data = res.get_json()
        assert data["success"]

    def test_reset_with_bad_otp(self, csrf_client, registered_user):
        from datetime import datetime, timedelta, timezone
        from extensions import otp_col
        otp_col.replace_one(
            {"email": registered_user["email"]},
            {
                "email": registered_user["email"], "otp": "654321",
                "name": registered_user["name"],
                "type": "forgot", "attempts": 0,
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            upsert=True,
        )
        res  = csrf_client.post("/forgot", json={
            "action"  : "reset_password",
            "email"   : registered_user["email"],
            "otp"     : "000000",
            "password": "NewPass@999",
        })
        data = res.get_json()
        assert not data["success"]

    def test_reset_with_correct_otp(self, csrf_client, registered_user):
        from datetime import datetime, timedelta, timezone
        from extensions import otp_col
        otp_col.replace_one(
            {"email": registered_user["email"]},
            {
                "email": registered_user["email"], "otp": "777777",
                "name": registered_user["name"],
                "type": "forgot", "attempts": 0,
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            upsert=True,
        )
        res  = csrf_client.post("/forgot", json={
            "action"  : "reset_password",
            "email"   : registered_user["email"],
            "otp"     : "777777",
            "password": "NewPass@999",
        })
        assert res.get_json()["success"]
