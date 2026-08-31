def test_list_exercises(client):
    resp = client.get("/api/exercises/")
    assert resp.status_code == 200
    exercises = resp.get_json()["exercises"]
    assert len(exercises) > 0
    assert all("name" in e and "muscle_group" in e for e in exercises)


def test_filter_exercises_by_category(client):
    resp = client.get("/api/exercises/?category=pectoraux")
    assert resp.status_code == 200
    for e in resp.get_json()["exercises"]:
        assert e["category"] == "pectoraux"


def test_get_single_exercise(client):
    ex = client.get("/api/exercises/").get_json()["exercises"][0]
    resp = client.get(f"/api/exercises/{ex['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["exercise"]["id"] == ex["id"]


def test_get_missing_exercise(client):
    resp = client.get("/api/exercises/999999")
    assert resp.status_code == 404


def test_alternatives(client):
    ex = client.get("/api/exercises/").get_json()["exercises"][0]
    resp = client.get(f"/api/exercises/{ex['id']}/alternatives")
    assert resp.status_code == 200
    e = resp.get_json()
    assert "alternatives" in e
