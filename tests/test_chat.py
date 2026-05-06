"""
tests/test_chat.py — /api/chat, /api/history, rate limiting.
"""
from unittest.mock import MagicMock, patch


class TestChatPage:
    def test_redirects_when_not_logged_in(self, client):
        res = client.get("/chat")
        assert res.status_code == 302

    def test_renders_when_logged_in(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.get("/chat")
        assert res.status_code == 200
        assert b"Arjun" in res.data


class TestApiChat:
    def test_unauthenticated_returns_401(self, csrf_client):
        res = csrf_client.post("/api/chat", json={"message": "Hello"})
        assert res.status_code == 401

    def test_empty_message_rejected(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.post("/api/chat", json={"message": ""})
        assert res.status_code == 400

    def test_too_long_message_rejected(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.post("/api/chat", json={"message": "x" * 2001})
        assert res.status_code == 400

    def test_successful_chat(self, logged_in_client):
        c, _ = logged_in_client
        mock_reply = {"choices": [{"message": {"content": "Namaste. The Gita teaches…"}}]}
        with patch("blueprints.chat.routes.http.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_reply)
            res  = c.post("/api/chat", json={"message": "I feel lost.", "language": "en"})
            data = res.get_json()
        assert res.status_code == 200
        assert "reply" in data
        assert "Gita" in data["reply"]

    def test_invalid_language_falls_back_to_english(self, logged_in_client):
        c, _ = logged_in_client
        mock_reply = {"choices": [{"message": {"content": "I am Arjun."}}]}
        with patch("blueprints.chat.routes.http.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_reply)
            res = c.post("/api/chat", json={"message": "Hello", "language": "zz"})
        assert res.status_code == 200

    def test_ai_timeout_returns_friendly_message(self, logged_in_client):
        import requests as req
        c, _ = logged_in_client
        with patch("blueprints.chat.routes.http.post", side_effect=req.exceptions.Timeout):
            res  = c.post("/api/chat", json={"message": "Test timeout."})
            data = res.get_json()
        assert "timed out" in data["reply"].lower()


class TestApiHistory:
    def test_unauthenticated_returns_empty(self, client):
        res = client.get("/api/history")
        assert res.status_code == 401

    def test_returns_history_list(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.get("/api/history")
        assert res.status_code == 200
        assert "history" in res.get_json()
