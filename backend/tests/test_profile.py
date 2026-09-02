def test_profile_unauthenticated(client):
    resp = client.get("/api/profile/")
    assert resp.status_code == 401


def test_get_profile(auth_client):
    resp = auth_client.get("/api/profile/")
    assert resp.status_code == 200
    assert resp.get_json()["user"]["daily_calories"] == 2500


def test_update_profile(auth_client):
    resp = auth_client.put("/api/profile/", json={"goal": "force", "level": "avance", "weight": 82})
    assert resp.status_code == 200
    user = resp.get_json()["user"]
    assert user["goal"] == "force"
    assert user["level"] == "avance"
    assert user["weight"] == 82


def test_update_equipment(auth_client):
    resp = auth_client.put("/api/profile/", json={"available_equipment": ["haltères", "barre"]})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["available_equipment"] == ["haltères", "barre"]


def test_update_dietary_preferences(auth_client):
    resp = auth_client.put("/api/profile/", json={"dietary_preferences": ["vegan", "sans_noix"]})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["dietary_preferences"] == ["vegan", "sans_noix"]
    # Persisté dans le profil
    user = auth_client.get("/api/profile/").get_json()["user"]
    assert user["dietary_preferences"] == ["vegan", "sans_noix"]


def test_add_and_get_weight(auth_client):
    resp = auth_client.post("/api/profile/weight", json={"weight": 80.5})
    assert resp.status_code == 201
    entries = auth_client.get("/api/profile/weight").get_json()["entries"]
    assert len(entries) == 1
    assert entries[0]["weight"] == 80.5


def test_weight_upsert_same_day(auth_client):
    # Un seul poids par jour : un 2e POST du même jour remplace, n'ajoute pas
    r1 = auth_client.post("/api/profile/weight", json={"weight": 80.5})
    assert r1.status_code == 201
    assert r1.get_json()["action"] == "created"

    r2 = auth_client.post("/api/profile/weight", json={"weight": 82.0})
    assert r2.status_code == 201
    assert r2.get_json()["action"] == "replaced"
    assert r2.get_json()["previous"] == 80.5

    entries = auth_client.get("/api/profile/weight").get_json()["entries"]
    assert len(entries) == 1
    assert entries[0]["weight"] == 82.0


def test_export_requires_auth(client):
    resp = client.get("/api/profile/export")
    assert resp.status_code == 401


def test_export_data(auth_client):
    auth_client.post("/api/profile/weight", json={"weight": 81})
    resp = auth_client.get("/api/profile/export")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["user"]["email"] == "user1@test.fr"
    assert "password_hash" not in data["user"]
    assert len(data["weight_entries"]) == 1
    assert "training_programs" in data
    assert "sessions" in data


def test_delete_account_requires_auth(client):
    resp = client.delete("/api/profile/account")
    assert resp.status_code == 401


def test_delete_account(auth_client):
    resp = auth_client.delete("/api/profile/account")
    assert resp.status_code == 200
    # La session est nettoyée : plus authentifié ensuite
    me = auth_client.get("/api/auth/me")
    assert me.status_code == 401


def test_delete_account_removes_linked_data(auth_client):
    auth_client.post("/api/training/program/generate")
    resp = auth_client.delete("/api/profile/account")
    assert resp.status_code == 200
    # Re-créer un user pour vérifier que la base est vide des données précédentes
    auth_client.post("/api/auth/register", json={"username": "fresh", "email": "fresh@t.fr", "password": "x"})
    prog = auth_client.get("/api/training/program/current")
    assert prog.status_code == 404
