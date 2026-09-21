def test_chat_status_unauthenticated(client):
    resp = client.get("/api/chat/status")
    assert resp.status_code == 401


def test_chat_unauthenticated(client):
    resp = client.post("/api/chat/", json={"messages": [{"role": "user", "content": "salut"}]})
    assert resp.status_code == 401


def test_chat_status_disabled(auth_client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    resp = auth_client.get("/api/chat/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["groq_enabled"] is False


def test_chat_requires_messages(auth_client, monkeypatch):
    resp = auth_client.post("/api/chat/", json={"messages": []})
    assert resp.status_code == 400


def test_chat_unconfigured_returns_429(auth_client, monkeypatch):
    """Aucun fournisseur ne peut fonctionner : le routeur renvoie 429."""
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    resp = auth_client.post("/api/chat/", json={"messages": [{"role": "user", "content": "salut"}]})
    assert resp.status_code == 429