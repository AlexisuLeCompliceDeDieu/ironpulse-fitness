def test_tracking_requires_auth(client):
    resp = client.post("/api/tracking/sessions", json={})
    assert resp.status_code == 401


def _setup_session(client):
    client.post("/api/training/program/generate")
    program = client.get("/api/training/program/current").get_json()["program"]
    day = program["days"][0]
    ex_id = day["exercises"][0]["exercise"]["id"]
    return day["id"], ex_id


def test_create_session(auth_client):
    day_id, ex_id = _setup_session(auth_client)
    payload = {
        "program_day_id": day_id,
        "feeling": 4,
        "notes": "bonne séance",
        "sets": [
            {"exercise_id": ex_id, "set_number": 1, "weight": 50, "reps": 10},
            {"exercise_id": ex_id, "set_number": 2, "weight": 55, "reps": 8},
        ],
    }
    resp = auth_client.post("/api/tracking/sessions", json=payload)
    assert resp.status_code == 201
    s = resp.get_json()["session"]
    assert s["completed"] is True
    assert len(s["sets"]) == 2


def test_list_sessions_empty(auth_client):
    resp = auth_client.get("/api/tracking/sessions")
    assert resp.status_code == 200
    assert resp.get_json()["sessions"] == []


def test_list_sessions_after_creation(auth_client):
    day_id, ex_id = _setup_session(auth_client)
    auth_client.post(
        "/api/tracking/sessions",
        json={"program_day_id": day_id, "feeling": 3, "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 40, "reps": 10}]},
    )
    sessions = auth_client.get("/api/tracking/sessions").get_json()["sessions"]
    assert len(sessions) == 1


def test_update_session(auth_client):
    day_id, ex_id = _setup_session(auth_client)
    created = auth_client.post(
        "/api/tracking/sessions",
        json={"program_day_id": day_id, "feeling": 3, "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 40, "reps": 10}]},
    ).get_json()["session"]
    resp = auth_client.put(f"/api/tracking/sessions/{created['id']}", json={"feeling": 2})
    assert resp.status_code == 200
    assert resp.get_json()["session"]["feeling"] == 2


def test_create_free_session_without_program(auth_client):
    # Séance libre : pas besoin de programme associé (program_day_id absents)
    ex = auth_client.get("/api/exercises/").get_json()["exercises"][0]
    resp = auth_client.post(
        "/api/tracking/sessions",
        json={
            "feeling": 5,
            "notes": "séance libre",
            "sets": [
                {"exercise_id": ex["id"], "set_number": 1, "weight": 30, "reps": 12},
                {"exercise_id": ex["id"], "set_number": 2, "weight": 35, "reps": 10},
            ],
        },
    )
    assert resp.status_code == 201
    s = resp.get_json()["session"]
    assert s["program_day_id"] is None
    assert len(s["sets"]) == 2
