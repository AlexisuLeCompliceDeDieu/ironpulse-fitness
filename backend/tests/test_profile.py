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


def test_add_and_get_weight(auth_client):
    resp = auth_client.post("/api/profile/weight", json={"weight": 80.5})
    assert resp.status_code == 201
    entries = auth_client.get("/api/profile/weight").get_json()["entries"]
    assert len(entries) == 1
    assert entries[0]["weight"] == 80.5
