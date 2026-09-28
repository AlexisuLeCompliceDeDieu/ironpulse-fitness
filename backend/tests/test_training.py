import json

import pytest

from models import TrainingProgram


def _reponse_ia(noms=("Push", "Pull", "Jambes"), decalage=0):
    """Réponse IA minimale mais valide, construite depuis le vrai catalogue.

    `decalage` décale le choix d'exercices pour obtenir une vraie variante.
    """
    from models import Exercise

    groupes = {
        "Push": ("pectoraux", "epaule", "triceps"),
        "Pull": ("dos", "biceps"),
        "Jambes": ("quadriceps", "ischio", "fessiers"),
    }
    jours = []
    for nom in noms:
        exos = []
        for c in groupes[nom]:
            categorie = Exercise.query.filter_by(category=c).order_by(Exercise.id).all()
            ex = categorie[min(decalage, len(categorie) - 1)]
            exos.append({"exercise_id": ex.id, "series": 4, "reps": 10,
                         "repos_secondes": 120, "charge_kg": 40})
        jours.append({"nom": nom, "exercices": exos})
    return json.dumps({"resume": "Objectif : Chest et triceps.", "jours": jours}, ensure_ascii=False)


def patch_ia(monkeypatch, contenu="auto", noms=("Push", "Pull", "Jambes"), decalage=0):
    """Simule le routeur IA. La réponse est fabriquée à l'appel (contexte applicatif)."""
    from services import ai_program

    def fake(messages, max_tokens=2048, temperature=0.7, provider_pref=None):
        if contenu is None:
            return None, {"reason": "daily_limit"}
        corps = _reponse_ia(noms, decalage) if contenu == "auto" else contenu
        return corps, {"provider": "groq", "label": "Groq", "model": "llama-test"}

    monkeypatch.setattr(ai_program.ai_providers, "generate_text", fake)


@pytest.fixture()
def app_ctx(app):
    with app.app_context():
        yield


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


def test_rest_depends_on_exercise_size(auth_client):
    """Repos : 2min30 sur les exercices polyarticulaires, 1min30 sur les isolations."""
    program = auth_client.post("/api/training/program/generate").get_json()["program"]
    rests = {pe["exercise"]["is_compound"]: pe["rest_seconds"] for day in program["days"] for pe in day["exercises"]}
    assert rests.get(True) == 150
    assert rests.get(False) == 90


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
    goals = {p["goal"] for p in presets if p.get("kind") == "goal"}
    assert goals == {"prise_masse", "perte_poids", "force", "endurance"}
    splits = [p for p in presets if p.get("kind") == "split"]
    split_types = {p["split_type"] for p in splits}
    assert "full_body" in split_types
    assert "upper_lower" in split_types
    assert "push_pull_legs" in split_types
    perte = next(p for p in presets if p.get("goal") == "perte_poids")
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


def test_regenerate_deactivates_previous_and_returns_newest(auth_client):
    first = auth_client.post("/api/training/program/generate", json={"goal": "prise_masse"}).get_json()["program"]
    assert first["goal"] == "prise_masse"

    second = auth_client.post("/api/training/program/generate", json={"goal": "perte_poids"}).get_json()["program"]
    assert second["goal"] == "perte_poids"
    assert second["id"] > first["id"]

    # /current renvoie le plus récent (perte_poids)
    cur = auth_client.get("/api/training/program/current").get_json()["program"]
    assert cur["goal"] == "perte_poids"

    # Le premier programme n'est plus actif
    old = auth_client.get(f"/api/training/program/{first['id']}").get_json()["program"]
    assert old["is_active"] is False
    # Le second est bien actif
    new = auth_client.get(f"/api/training/program/{second['id']}").get_json()["program"]
    assert new["is_active"] is True


def test_generate_full_body_split(auth_client):
    resp = auth_client.post("/api/training/program/generate", json={"split_type": "full_body", "days_per_week": 3})
    assert resp.status_code == 201
    program = resp.get_json()["program"]
    assert len(program["days"]) == 3
    for day in program["days"]:
        assert len(day["exercises"]) > 0


def test_generate_upper_lower_split(auth_client):
    resp = auth_client.post("/api/training/program/generate", json={"split_type": "upper_lower", "days_per_week": 4})
    assert resp.status_code == 201
    program = resp.get_json()["program"]
    assert len(program["days"]) == 4


def test_generate_ppl_cycles_to_more_days(auth_client):
    # 6 séances/semaine depuis un split PPL à 3 jours -> les jours sont répétés
    resp = auth_client.post("/api/training/program/generate", json={"split_type": "push_pull_legs", "days_per_week": 6})
    assert resp.status_code == 201
    program = resp.get_json()["program"]
    assert len(program["days"]) == 6


def test_generate_uses_profile_split_and_week(auth_client):
    auth_client.put("/api/profile/", json={"split_type": "upper_lower", "sessions_per_week": 2})
    resp = auth_client.post("/api/training/program/generate")
    assert resp.status_code == 201
    program = resp.get_json()["program"]
    assert len(program["days"]) == 2


def test_profile_saves_split_fields(auth_client):
    resp = auth_client.put("/api/profile/", json={"split_type": "push_pull_legs", "sessions_per_week": 5})
    assert resp.status_code == 200
    user = resp.get_json()["user"]
    assert user["split_type"] == "push_pull_legs"
    assert user["sessions_per_week"] == 5


# ── Génération par IA + régénération ────────────────────────────────

def test_generate_ia_returns_source_et_fournisseur(auth_client, monkeypatch):
    patch_ia(monkeypatch)
    resp = auth_client.post("/api/training/program/generate", json={"source": "ia", "days_per_week": 3})
    assert resp.status_code == 201
    data = resp.get_json()
    assert "IA" in data["message"]
    assert data["meta"]["source"] == "ia"
    assert data["meta"]["fournisseur"] == "Groq"
    assert data["program"]["generation_source"] == "ia"
    assert data["program"]["variation"] == 0
    assert [d["name"] for d in data["program"]["days"]] == ["Push", "Pull", "Jambes"]
    assert data["program"]["days"][0]["exercises"][0]["sets"] == 4


def test_generate_transmet_le_fournisseur_choisi(auth_client, monkeypatch):
    """Le switch de l'UI doit atteindre le routeur IA (provider_pref)."""
    vus = {}

    def fake(messages, max_tokens=2048, temperature=0.7, provider_pref=None):
        vus["provider_pref"] = provider_pref
        return _reponse_ia(("Push", "Pull", "Jambes"), 0), {"provider": "gemini", "label": "Google Gemini", "model": "m"}

    from services import ai_program
    monkeypatch.setattr(ai_program.ai_providers, "generate_text", fake)

    resp = auth_client.post("/api/training/program/generate",
                            json={"source": "ia", "days_per_week": 3, "provider": "gemini"})

    assert resp.status_code == 201
    assert vus["provider_pref"] == "gemini"
    assert resp.get_json()["meta"]["fournisseur"] == "Google Gemini"


def test_generate_repli_algorithme_quand_ia_indisponible(auth_client, monkeypatch):
    patch_ia(monkeypatch, None)
    resp = auth_client.post("/api/training/program/generate", json={"source": "auto"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["meta"]["source"] == "algorithme"
    assert data["meta"]["raison"]
    assert data["program"]["generation_source"] == "algorithme"
    assert data["program"]["days"]


def test_generate_source_ia_strict_renvoie_503(auth_client, app_ctx, monkeypatch):
    patch_ia(monkeypatch, None)
    resp = auth_client.post("/api/training/program/generate", json={"source": "ia"})
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["raison"] == "daily_limit"
    # L'utilisateur voit une cause lisible, pas un code technique
    assert data["raison_fr"] == "limite quotidienne atteinte"
    assert data["reinitialiser_ia"] is True
    assert TrainingProgram.query.count() == 0


def test_generate_algorithme_ignore_la_ia(auth_client, monkeypatch):
    patch_ia(monkeypatch)
    resp = auth_client.post("/api/training/program/generate", json={"source": "algorithme"})
    assert resp.status_code == 201
    assert resp.get_json()["meta"]["source"] == "algorithme"


def test_generate_erreur_inattendue_renvoie_un_json_lisible(auth_client, monkeypatch):
    """Une exception non gérée ne doit plus renvoyer la page HTML de Flask."""
    def boom(*args, **kwargs):
        raise RuntimeError("colonne manquante")

    monkeypatch.setattr("services.ai_program.generer_programme", boom)
    resp = auth_client.post("/api/training/program/generate", json={})

    assert resp.status_code == 500
    data = resp.get_json()
    assert "échoué" in data["error"]
    assert "RuntimeError" in data["detail"]
    assert data["programme_conserve"] is True


def test_regenerate_requires_auth(client):
    assert client.post("/api/training/program/regenerate").status_code == 401


def test_regenerate_sans_programme_404(auth_client):
    assert auth_client.post("/api/training/program/regenerate", json={}).status_code == 404


def test_regenerate_cree_une_variante_et_conserve_l_historique(auth_client, app_ctx, monkeypatch):
    patch_ia(monkeypatch)
    premier = auth_client.post(
        "/api/training/program/generate", json={"source": "ia", "days_per_week": 3}
    ).get_json()["program"]
    ids_premier = [e["exercise"]["id"] for e in premier["days"][0]["exercises"]]

    patch_ia(monkeypatch, decalage=1)
    resp = auth_client.post("/api/training/program/regenerate", json={"consigne": "mets de la cardio"})
    assert resp.status_code == 201
    data = resp.get_json()
    second = data["program"]

    assert "régénéré" in data["message"].lower()
    assert data["meta"]["source"] == "ia"
    assert second["id"] > premier["id"]
    assert second["variation"] == 1
    assert second["is_active"] is True
    # La régénération conserve la structure du programme (3 séances)
    assert len(second["days"]) == len(premier["days"]) == 3
    # La sélection d'exercices a réellement changé
    ids_second = [e["exercise"]["id"] for e in second["days"][0]["exercises"]]
    assert ids_second != ids_premier
    assert TrainingProgram.query.get(premier["id"]).is_active is False
    # Le nouveau programme actif est bien celui rendu par /current
    assert auth_client.get("/api/training/program/current").get_json()["program"]["id"] == second["id"]


def test_regenerate_ia_strict_503_conserve_le_programme(auth_client, monkeypatch):
    patch_ia(monkeypatch)
    auth_client.post("/api/training/program/generate", json={"source": "ia"})
    actif = auth_client.get("/api/training/program/current").get_json()["program"]

    patch_ia(monkeypatch, None)
    resp = auth_client.post("/api/training/program/regenerate", json={"source": "ia"})
    assert resp.status_code == 503
    courant = auth_client.get("/api/training/program/current").get_json()["program"]
    assert courant["id"] == actif["id"]


def test_source_inconnu_retombe_sur_auto(auth_client, monkeypatch):
    patch_ia(monkeypatch)
    resp = auth_client.post("/api/training/program/generate", json={"source": "quantum"})
    assert resp.status_code == 201
    assert resp.get_json()["meta"]["source"] == "ia"
