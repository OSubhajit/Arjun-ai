"""
tests/test_profile.py — /profile, /api/profile, /api/conversations, DELETE.
"""


class TestProfilePage:
    def test_redirects_when_not_logged_in(self, client):
        res = client.get("/profile")
        assert res.status_code == 302

    def test_renders_when_logged_in(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.get("/profile")
        assert res.status_code == 200


class TestApiProfile:
    def test_unauthenticated_returns_401(self, client):
        res = client.get("/api/profile")
        assert res.status_code == 401

    def test_returns_user_data(self, logged_in_client):
        c, user = logged_in_client
        res  = c.get("/api/profile")
        data = res.get_json()
        assert data["email"] == user["email"]
        assert data["name"]  == user["name"]
        assert "total_messages" in data
        assert "total_sessions" in data
        assert "conversations"  in data


class TestApiConversations:
    def test_unauthenticated_returns_401(self, client):
        res = client.get("/api/conversations")
        assert res.status_code == 401

    def test_returns_conversation_list(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.get("/api/conversations")
        data = res.get_json()
        assert "conversations" in data
        assert isinstance(data["conversations"], list)

    def test_delete_invalid_id_returns_400(self, logged_in_client):
        c, _ = logged_in_client
        res  = c.delete("/api/conversations/../../etc/passwd")
        assert res.status_code in (400, 404)

    def test_delete_requires_csrf(self, client):
        res = client.delete("/api/conversations/12345")
        assert res.status_code == 403
