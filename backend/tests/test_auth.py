def test_register_success(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@test.fr", "password": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["user"]["username"] == "alice"
    assert "password" not in data["user"]


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json={"username": "a", "email": "dup@test.fr", "password": "x"})
    resp = client.post("/api/auth/register", json={"username": "b", "email": "dup@test.fr", "password": "x"})
    assert resp.status_code == 409


def test_register_with_profile_details(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "carol",
            "email": "carol@test.fr",
            "password": "secret123",
            "goal": "perte_poids",
            "level": "intermediaire",
            "weight": 78,
            "target_weight": 70,
            "height": 180,
            "age": 30,
            "daily_calories": 2200,
            "split_type": "upper_lower",
            "sessions_per_week": 4,
        },
    )
    assert resp.status_code == 201
    u = resp.get_json()["user"]
    assert u["goal"] == "perte_poids"
    assert u["level"] == "intermediaire"
    assert u["weight"] == 78
    assert u["target_weight"] == 70
    assert u["height"] == 180
    assert u["age"] == 30
    assert u["daily_calories"] == 2200
    assert u["split_type"] == "upper_lower"
    assert u["sessions_per_week"] == 4


def test_register_missing_fields(client):
    resp = client.post("/api/auth/register", json={"username": "c"})
    assert resp.status_code == 400


def test_login_success(client):
    client.post("/api/auth/register", json={"username": "bob", "email": "bob@test.fr", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "bob@test.fr", "password": "pass123"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["username"] == "bob"


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"username": "bob2", "email": "bob2@test.fr", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "bob2@test.fr", "password": "mauvais"})
    assert resp.status_code == 401


def test_me_unauthenticated(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_authenticated(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "user1@test.fr"


def test_logout(auth_client):
    resp = auth_client.post("/api/auth/logout")
    assert resp.status_code == 200
    after = auth_client.get("/api/auth/me")
    assert after.status_code == 401
