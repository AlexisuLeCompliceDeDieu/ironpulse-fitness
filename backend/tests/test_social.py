def _make_user(client, username, email):
    client.post("/api/auth/register", json={"username": username, "email": email, "password": "secret123"})


def _login(client, email):
    client.post("/api/auth/login", json={"email": email, "password": "secret123"})



def _login_user1(auth_client):
    _login(auth_client, "user1@test.fr")


def test_machines_list(client):
    resp = client.get("/api/machines/")
    assert resp.status_code == 200
    machines = resp.get_json()["machines"]
    assert len(machines) > 0
    first = machines[0]
    assert first["code"]
    assert first["brand"]


def test_machine_detail(client):
    mid = client.get("/api/machines/").get_json()["machines"][0]["id"]
    resp = client.get(f"/api/machines/{mid}")
    assert resp.status_code == 200
    assert resp.get_json()["machine"]["id"] == mid


def test_social_requires_auth(client):
    assert client.get("/api/social/friends").status_code == 401
    assert client.get("/api/social/leaderboard").status_code == 401


def test_add_friend_sends_request(auth_client, client):
    _make_user(client, "pote", "pote@test.fr")
    _login_user1(auth_client)
    resp = auth_client.post("/api/social/friends", json={"email": "pote@test.fr"})
    assert resp.status_code == 201
    # Pas encore ami : la demande attend la validation du destinataire
    usernames = {f["username"] for f in auth_client.get("/api/social/friends").get_json()["friends"]}
    assert "pote" not in usernames
    # L'email saisit est dans "outgoing"
    reqs = auth_client.get("/api/social/friends/requests").get_json()
    assert reqs["outgoing"][0]["username"] == "pote"


def test_accept_friend(auth_client, client):
    _make_user(client, "pote", "pote@test.fr")
    _login_user1(auth_client)
    auth_client.post("/api/social/friends", json={"email": "pote@test.fr"})
    # Le destinataire voit la demande entrante et l'accepte
    _login(client, "pote@test.fr")
    reqs = client.get("/api/social/friends/requests").get_json()
    incoming = reqs["incoming"]
    assert incoming and incoming[0]["username"] == "user1"
    resp = client.post("/api/social/friends/accept", json={"friend_id": incoming[0]["id"]})
    assert resp.status_code == 200
    # Les deux comptes sont maintenant amis
    _login_user1(auth_client)
    usernames = {f["username"] for f in auth_client.get("/api/social/friends").get_json()["friends"]}
    assert "pote" in usernames


def test_decline_friend(auth_client, client):
    _make_user(client, "pote", "pote@test.fr")
    _login_user1(auth_client)
    auth_client.post("/api/social/friends", json={"email": "pote@test.fr"})
    _login(client, "pote@test.fr")
    incoming = client.get("/api/social/friends/requests").get_json()["incoming"]
    resp = client.post("/api/social/friends/decline", json={"friend_id": incoming[0]["id"]})
    assert resp.status_code == 200
    _login_user1(auth_client)
    assert auth_client.get("/api/social/friends").get_json()["friends"] == []
    reqs = auth_client.get("/api/social/friends/requests").get_json()
    assert reqs["outgoing"] == []


def test_mutual_requests_auto_accept(auth_client, client):
    _make_user(client, "pote", "pote@test.fr")
    _login_user1(auth_client)
    auth_client.post("/api/social/friends", json={"email": "pote@test.fr"})
    # Le destinataire envoie aussi une demande pendant que la sienne est en attente
    _login(client, "pote@test.fr")
    resp = client.post("/api/social/friends", json={"email": "user1@test.fr"})
    assert resp.status_code == 201
    _login_user1(auth_client)
    usernames = {f["username"] for f in auth_client.get("/api/social/friends").get_json()["friends"]}
    assert "pote" in usernames


def test_add_friend_duplicate(auth_client, client):
    _make_user(client, "pote2", "pote2@test.fr")
    _login_user1(auth_client)
    auth_client.post("/api/social/friends", json={"email": "pote2@test.fr"})
    resp = auth_client.post("/api/social/friends", json={"email": "pote2@test.fr"})
    assert resp.status_code == 409


def test_add_friend_self(auth_client):
    _login_user1(auth_client)
    resp = auth_client.post("/api/social/friends", json={"email": "user1@test.fr"})
    assert resp.status_code == 400


def test_remove_friend(auth_client, client):
    _make_user(client, "pote3", "pote3@test.fr")
    _login_user1(auth_client)
    auth_client.post("/api/social/friends", json={"email": "pote3@test.fr"})
    _login(client, "pote3@test.fr")
    incoming = client.get("/api/social/friends/requests").get_json()["incoming"]
    client.post("/api/social/friends/accept", json={"friend_id": incoming[0]["id"]})
    _login_user1(auth_client)
    friend = auth_client.get("/api/social/friends").get_json()["friends"][0]
    resp = auth_client.delete(f"/api/social/friends/{friend['id']}")
    assert resp.status_code == 200
    assert auth_client.get("/api/social/friends").get_json()["friends"] == []


def test_leaderboard_includes_self(auth_client):
    resp = auth_client.get("/api/social/leaderboard")
    assert resp.status_code == 200
    rows = resp.get_json()["leaderboard"]
    assert any(r["me"] for r in rows)


def test_session_difficulty_saved(auth_client):
    ex = auth_client.get("/api/exercises/").get_json()["exercises"][0]
    resp = auth_client.post(
        "/api/tracking/sessions",
        json={"feeling": 4, "sets": [
            {"exercise_id": ex["id"], "set_number": 1, "weight": 40, "reps": 10, "difficulty": "facile"},
            {"exercise_id": ex["id"], "set_number": 2, "weight": 45, "reps": 8, "difficulty": "difficile"},
        ]},
    )
    assert resp.status_code == 201
    sets = resp.get_json()["session"]["sets"]
    assert sets[0]["difficulty"] == "facile"
    assert sets[1]["difficulty"] == "difficile"


def test_future_date_session_flagged(auth_client):
    from datetime import date, timedelta
    ex = auth_client.get("/api/exercises/").get_json()["exercises"][0]
    future = (date.today() + timedelta(days=2)).isoformat()
    resp = auth_client.post(
        "/api/tracking/sessions",
        json={"date": future, "sets": [
            {"exercise_id": ex["id"], "set_number": 1, "weight": 60, "reps": 10},
        ]},
    )
    assert resp.status_code == 201
    assert resp.get_json()["session"]["flagged"] is True