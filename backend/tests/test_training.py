def test_generate_program_requires_auth(client):
    resp = client.post("/api/training/program/generate")
    assert resp.status_code == 401


def test_generate_program(auth_client):
    resp = auth_client.post("/api/training/program/generate")
    assert resp.status_code == 201
    program = resp.get_json()["program"]
    assert program["goal"] == "prise_masse"
    assert program["is_active"] is True
    assert len(program["days"]) > 0
    # Chaque jour doit contenir des exercices
    for day in program["days"]:
        assert len(day["exercises"]) > 0
        for pe in day["exercises"]:
            assert pe["exercise"] is not None


def test_current_program(auth_client):
    auth_client.post("/api/training/program/generate")
    resp = auth_client.get("/api/training/program/current")
    assert resp.status_code == 200
    assert resp.get_json()["program"]["is_active"] is True


def test_current_program_none(auth_client):
    resp = auth_client.get("/api/training/program/current")
    assert resp.status_code == 404


def test_generate_with_equipment_restriction(auth_client):
    auth_client.put("/api/profile/", json={"available_equipment": ["haltères", "aucun"], "goal": "prise_masse"})
    resp = auth_client.post("/api/training/program/generate")
    assert resp.status_code == 201


def test_replace_exercise(auth_client):
    ex = auth_client.get("/api/exercises/").get_json()["exercises"][0]
    resp = auth_client.post(
        f"/api/training/exercises/{ex['id']}/alternative",
        json={"available_equipment": []},
    )
    assert resp.status_code == 200
    assert resp.get_json()["alternative"]["name"]


def test_presets(auth_client):
    resp = auth_client.get("/api/training/presets")
    assert resp.status_code == 200
    presets = resp.get_json()["presets"]
    goals = {p["goal"] for p in presets}
    assert goals == {"prise_masse", "perte_poids", "force", "endurance"}
    perte = next(p for p in presets if p["goal"] == "perte_poids")
    assert perte["days_per_week"] == 3
    assert perte["days"]


def test_generate_with_goal_override(auth_client):
    resp = auth_client.post("/api/training/program/generate", json={"goal": "force"})
    assert resp.status_code == 201
    program = resp.get_json()["program"]
    assert program["goal"] == "force"
    assert len(program["days"]) == 2


def test_generate_defaults_to_profile_goal(auth_client):
    auth_client.put("/api/profile/", json={"goal": "perte_poids"})
    resp = auth_client.post("/api/training/program/generate")
    assert resp.status_code == 201
    program = resp.get_json()["program"]
    assert program["goal"] == "perte_poids"
    assert len(program["days"]) == 3
