"""
tests/test_security.py — CSRF validation, security headers, input sanitisation.
"""


class TestSecurityHeaders:
    def test_login_page_has_security_headers(self, client):
        res = client.get("/login")
        assert res.headers.get("X-Frame-Options")        == "DENY"
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert "Content-Security-Policy" in res.headers
        assert "Referrer-Policy" in res.headers

    def test_chat_api_has_security_headers(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.post("/api/chat", json={"message": "test"})
        assert res.headers.get("X-Frame-Options") == "DENY"


class TestCSRFProtection:
    def test_login_without_csrf_returns_403(self, client):
        res = client.post("/login", json={"email": "a@b.com", "password": "pw"})
        assert res.status_code == 403

    def test_logout_without_csrf_returns_403(self, client):
        res = client.post("/logout")
        assert res.status_code == 403

    def test_register_without_csrf_returns_403(self, client):
        res = client.post("/register", json={"action": "send_otp", "email": "x@x.com"})
        assert res.status_code == 403


class TestInputSanitisation:
    def test_xss_in_name_is_escaped(self, csrf_client):
        """Names with HTML are stored escaped, not raw."""
        from datetime import datetime, timedelta, timezone
        from extensions import otp_col, users_col
        evil_name = "<script>alert(1)</script>"
        import bcrypt
        hashed = bcrypt.hashpw(b"Test@12345", bcrypt.gensalt()).decode()
        otp_col.replace_one(
            {"email": "xss@test.dev"},
            {
                "email": "xss@test.dev", "otp": "000111",
                "name": evil_name, "password": hashed,
                "type": "register", "attempts": 0,
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            upsert=True,
        )
        res  = csrf_client.post("/register", json={
            "action": "verify_otp", "email": "xss@test.dev", "otp": "000111",
        })
        user = users_col.find_one({"email": "xss@test.dev"})
        if user:
            # Name must not contain raw < or > characters
            assert "<script>" not in user.get("name", "")
