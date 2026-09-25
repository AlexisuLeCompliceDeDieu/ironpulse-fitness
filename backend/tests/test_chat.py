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


def test_healthz_ia_diagnostique_sans_secret(client):
    """Endpoint public de diagnostic : quel fournisseur est bloqué, et pourquoi."""
    resp = client.get("/healthz/ia")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "providers" in data and "message" in data
    assert set(data["providers"]) >= {"groq", "gemini"}
    assert "GROQ_API_KEY" not in resp.get_data(as_text=True)


def test_reset_quota_reactive_les_ia(auth_client, monkeypatch):
    from services import quota_tracker

    monkeypatch.setenv("GROQ_API_KEY", "cle-de-test")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    quota_tracker.disable_provider("groq", "daily_limit")

    assert auth_client.get("/api/chat/status").get_json()["ia"]["usable"] == []

    resp = auth_client.post("/api/chat/reset-quota")
    assert resp.status_code == 200
    assert "réactivés" in resp.get_json()["message"].lower()
    assert resp.get_json()["ia"]["usable"] == ["groq"]


def test_reset_quota_exige_authentification(client):
    assert client.post("/api/chat/reset-quota").status_code == 401