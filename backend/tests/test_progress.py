def test_advice_requires_auth(client):
    resp = client.get("/api/progress/advice")
    assert resp.status_code == 401


def test_advice_new_user(auth_client):
    resp = auth_client.get("/api/progress/advice")
    assert resp.status_code == 200
    advice = resp.get_json()["advice"]
    assert len(advice) > 0
    assert all("text" in a and "type" in a for a in advice)


def test_advice_after_session(auth_client):
    auth_client.post("/api/training/program/generate")
    program = auth_client.get("/api/training/program/current").get_json()["program"]
    day_id = program["days"][0]["id"]
    ex_id = program["days"][0]["exercises"][0]["exercise"]["id"]
    auth_client.post(
        "/api/tracking/sessions",
        json={"program_day_id": day_id, "feeling": 1, "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 20, "reps": 8}]},
    )
    advice = auth_client.get("/api/progress/advice").get_json()["advice"]
    # Un message sur le ressenti ou la régularité doit être présent
    texts = " ".join(a["text"] for a in advice).lower()
    assert "séance" in texts


def test_stats(auth_client):
    resp = auth_client.get("/api/progress/stats")
    assert resp.status_code == 200
    assert resp.get_json()["total_sessions"] == 0


def test_exercise_progress_empty(auth_client):
    ex = auth_client.get("/api/exercises/").get_json()["exercises"][0]
    resp = auth_client.get(f"/api/progress/exercises/{ex['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["data"] == []


def test_exercise_progress_after_session(auth_client):
    auth_client.post("/api/training/program/generate")
    program = auth_client.get("/api/training/program/current").get_json()["program"]
    day_id = program["days"][0]["id"]
    ex_id = program["days"][0]["exercises"][0]["exercise"]["id"]
    auth_client.post(
        "/api/tracking/sessions",
        json={"program_day_id": day_id, "feeling": 3, "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 60, "reps": 10}]},
    )
    data = auth_client.get(f"/api/progress/exercises/{ex_id}").get_json()["data"]
    assert len(data) == 1
    assert data[0]["max_weight"] == 60


def test_adaptation_requires_auth(client):
    resp = client.get("/api/progress/adaptation")
    assert resp.status_code == 401


def test_adaptation_no_sessions(auth_client):
    resp = auth_client.get("/api/progress/adaptation")
    assert resp.status_code == 200
    assert resp.get_json()["adaptation"] == []


def test_adaptation_low_feeling_warns_deload(auth_client):
    auth_client.post("/api/training/program/generate")
    program = auth_client.get("/api/training/program/current").get_json()["program"]
    day_id = program["days"][0]["id"]
    ex_id = program["days"][0]["exercises"][0]["exercise"]["id"]
    auth_client.post(
        "/api/tracking/sessions",
        json={"program_day_id": day_id, "feeling": 1, "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 20, "reps": 8}]},
    )
    adaptation = auth_client.get("/api/progress/adaptation").get_json()["adaptation"]
    assert any(a["type"] == "warning" for a in adaptation)
