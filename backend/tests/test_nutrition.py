def test_foods_seeded(client):
    resp = client.get("/api/nutrition/foods")
    assert resp.status_code == 200
    foods = resp.get_json()["foods"]
    assert len(foods) > 0
    assert all("kcal" in f and "protein" in f for f in foods)


def test_plan_generate_requires_auth(client):
    resp = client.post("/api/nutrition/plan/generate", json={"num_days": 7})
    assert resp.status_code == 401


def test_generate_plan(auth_client):
    resp = auth_client.post("/api/nutrition/plan/generate", json={"num_days": 7})
    assert resp.status_code == 201
    plan = resp.get_json()["plan"]
    assert plan["num_days"] == 7
    assert plan["target_calories"] == 2500
    # 4 repas/jour x 7 jours = 28 repas
    assert len(plan["meals"]) == 28
    for meal in plan["meals"]:
        assert meal["items"]  # chaque repas contient des aliments
        assert meal["totals"]["kcal"] > 0


def test_latest_plan(auth_client):
    auth_client.post("/api/nutrition/plan/generate", json={"num_days": 3})
    resp = auth_client.get("/api/nutrition/plan/latest")
    assert resp.status_code == 200
    assert resp.get_json()["plan"]["num_days"] == 3


def test_latest_plan_none(auth_client):
    resp = auth_client.get("/api/nutrition/plan/latest")
    assert resp.status_code == 404


def test_generate_shopping_list(auth_client):
    plan = auth_client.post("/api/nutrition/plan/generate", json={"num_days": 3}).get_json()["plan"]
    resp = auth_client.post("/api/nutrition/shopping-list/generate", json={"meal_plan_id": plan["id"]})
    assert resp.status_code == 201
    items = resp.get_json()["shopping_list"]["items"]
    assert len(items) > 0
    assert all("qty_grams" in i and i["qty_grams"] > 0 for i in items)


def test_shopping_list_requires_plan(auth_client):
    resp = auth_client.post("/api/nutrition/shopping-list/generate", json={})
    assert resp.status_code == 404
