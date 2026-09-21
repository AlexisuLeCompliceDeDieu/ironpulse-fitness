def test_chat_status_unauthenticated(client):
    resp = client.get("/api/chat/status")
    assert resp.status_code == 401


def test_chat_unauthenticated(client):
    resp = client.post("/api/chat/", json={"messages": [{"role": "user", "content": "salut"}]})
    assert resp.status_code == 401


def test_chat_status_disabled(auth_client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    resp = auth_client.get("/api/chat/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["groq_enabled"] is False


def test_chat_requires_messages(auth_client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    resp = auth_client.post("/api/chat/", json={"messages": []})
    assert resp.status_code == 400


def test_chat_unconfigured_returns_503(auth_client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    resp = auth_client.post("/api/chat/", json={"messages": [{"role": "user", "content": "salut"}]})
    # clé présente mais "fake" : get_client() tente de créer un client Groq (réussit),
    # l'appel réseau échouera en 502 — on teste donc le 502 ou le 503 si clé absente.
    assert resp.status_code in (502, 503)