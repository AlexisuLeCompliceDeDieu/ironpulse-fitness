"""Tests de la génération de programme par IA (avec repli algorithmique).

L'IA est simulée au niveau du routeur (`ai_providers.generate_text`) : on vérifie
ce qui compte vraiment côté backend, à savoir la construction du contexte, la
validation/réparation de la réponse du modèle et le repli quand l'IA est
indisponible.
"""

import json

import pytest

from models import db, User, TrainingProgram, Session, SessionSet, Exercise

from services import ai_program, program_generator


def _reponse_ia(jours, resume="Plan personnalisé"):
    return json.dumps({"resume": resume, "jours": jours}, ensure_ascii=False)


def patch_ia(monkeypatch, contenu, label="Groq", provider="groq"):
    """Simule le routeur : renvoie `contenu` et mémorise les messages envoyés."""
    messages_vus = []

    def fake_generate_text(messages, max_tokens=2048, temperature=0.7):
        messages_vus.append(messages)
        if contenu is None:
            return None, {"reason": "daily_limit"}
        return contenu, {"provider": provider, "label": label, "model": "modele-test"}

    monkeypatch.setattr(ai_program.ai_providers, "generate_text", fake_generate_text)
    return messages_vus


_GROUPES = {
    "Push": ("pectoraux", "epaule", "triceps"),
    "Pull": ("dos", "biceps"),
    "Jambes": ("quadriceps", "ischio", "fessiers"),
}


def _jours_ia(par_cat, noms=("Push", "Pull", "Jambes")):
    """Construit une réponse IA plausible (un objet par jour de séance)."""
    jours = []
    for nom in noms:
        exos = []
        for cat in _GROUPES[nom]:
            ex = par_cat[cat][0]
            exos.append({"exercise_id": ex.id, "series": 4, "reps": 10,
                         "repos_secondes": 120, "charge_kg": 30})
        jours.append({"nom": nom, "exercices": exos})
    return jours


@pytest.fixture()
def app_ctx(app):
    with app.app_context():
        yield


@pytest.fixture()
def user_ia(app_ctx):
    u = User(
        username="coach", email="coach@test.fr", password_hash="x",
        goal="prise_masse", level="intermediaire", weight=80.0,
        target_weight=88.0, height=180, age=28, split_type=None, sessions_per_week=3,
    )
    db.session.add(u)
    db.session.commit()
    return u


def _par_categorie(user, materiel=None):
    """Exercices du catalogue, groupés par catégorie."""
    groupes = {}
    for ex in ai_program._catalogue(user, materiel or []):
        groupes.setdefault(ex.category, []).append(ex)
    return groupes


# ── Chemin nominal : l'IA propose un programme valide ───────────────

def test_generation_ia_cree_le_programme(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    patch_ia(monkeypatch, _reponse_ia(_jours_ia(par_cat)))

    program, meta = ai_program.generer_programme(user_ia, [], source="ia")

    assert program.generation_source == "ia"
    assert program.is_active is True
    assert len(program.days) == 3
    assert all(len(d.exercises) >= 1 for d in program.days)
    assert meta["source"] == "ia"
    assert meta["fournisseur"] == "Groq"
    assert meta["raison"] is None
    assert meta["regenere"] is False
    assert meta["resume"] == "Plan personnalisé"

    jour1 = program.days[0]
    assert jour1.exercises[0].sets == 4
    assert jour1.exercises[0].reps == 10
    assert jour1.exercises[0].rest_seconds == 120
    assert jour1.exercises[0].target_weight == 30.0


def test_generation_ia_envoie_le_contexte_utilisateur(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    messages_vus = patch_ia(monkeypatch, _reponse_ia(_jours_ia(par_cat)))

    ai_program.generer_programme(user_ia, [], source="ia", consigne="plus de jambes")

    prompt = messages_vus[0][-1]["content"]
    assert "niveau intermediaire" in prompt
    assert "prise_masse" in prompt
    assert "plus de jambes" in prompt
    assert "CATALOGUE D'EXERCICES AUTORISÉS" in prompt
    # Les ids du catalogue sont bien transmis : l'IA ne peut choisir que parmi eux
    for ex in Exercise.query.limit(3).all():
        assert f"{ex.id} | {ex.name}" in prompt


def test_generation_ia_respecte_le_materiel(app_ctx, user_ia, monkeypatch):
    """Aucun exercice nécessitant un matériel absent ne doit être programmé."""
    user_ia.available_equipment = json.dumps(["aucun"])
    db.session.commit()
    catalogue = ai_program._catalogue(user_ia, user_ia.equipment_list())
    machines = [ex for ex in Exercise.query.all() if ex.equipment_needed not in ("aucun",)]
    choisi = next(ex for ex in machines if ex.id not in {c.id for c in catalogue})
    jours = [{"nom": "Full Body A", "exercices": [
        {"exercise_id": choisi.id, "series": 3, "reps": 12},
        {"exercise_id": catalogue[0].id, "series": 3, "reps": 12},
    ]}]
    patch_ia(monkeypatch, _reponse_ia(jours))

    program, meta = ai_program.generer_programme(user_ia, user_ia.equipment_list(), source="ia")

    ids = {pe.exercise_id for pe in program.days[0].exercises}
    assert choisi.id not in ids
    assert ids <= {ex.id for ex in catalogue}


# ── Réparation des réponses douteuses ───────────────────────────────

def test_reponse_ia_bidon_ou_envelope_est_reparsee(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    contenu = "Voici ton plan !\n```json\n" + _reponse_ia(_jours_ia(par_cat)) + "```\nBon courage 💪"
    patch_ia(monkeypatch, contenu)

    program, meta = ai_program.generer_programme(user_ia, [], source="ia")

    assert meta["source"] == "ia"
    assert len(program.days[0].exercises) >= 1


def test_virgules_parasites_et_objet_par_jour(app_ctx, user_ia, monkeypatch):
    """Certains modèles sortent un objet par jour : on fusionne les listes."""
    jours = _jours_ia(par_cat := _par_categorie(user_ia))
    contenu = '{"jours": [' + ",".join(json.dumps(j, ensure_ascii=False) for j in jours) + ",]}"
    patch_ia(monkeypatch, contenu)

    program, meta = ai_program.generer_programme(user_ia, [], source="ia")

    assert [d.name for d in program.days] == ["Push", "Pull", "Jambes"]


def test_exercices_inconnus_ignores(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    jours = _jours_ia(par_cat)
    jours[0]["exercices"].append({"exercise_id": 999999, "series": 3, "reps": 10})
    jours[0]["exercices"].append({"exercise_id": None, "nom": "Exercice inventé", "series": 3, "reps": 10})
    patch_ia(monkeypatch, _reponse_ia(jours))

    program, meta = ai_program.generer_programme(user_ia, [], source="ia")

    ids = {pe.exercise_id for pe in program.days[0].exercises}
    assert 999999 not in ids
    assert len(program.days[0].exercises) == 3


def test_serie_rep_aberantes_bornees(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    jours = _jours_ia(par_cat)
    jours[0]["exercices"][0].update({"series": 99, "reps": 200, "repos_secondes": 5, "charge_kg": -10})
    patch_ia(monkeypatch, _reponse_ia(jours))

    program, _ = ai_program.generer_programme(user_ia, [], source="ia")

    pe = program.days[0].exercises[0]
    assert pe.sets == ai_program.SETS_MAX
    assert pe.reps == ai_program.REPS_MAX
    assert pe.rest_seconds == ai_program.REST_MIN
    # charge négative -> estimation par niveau
    assert pe.target_weight > 0


def test_charge_ia_plafonnee_au_corps(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    jours = _jours_ia(par_cat)
    ex = par_cat["pectoraux"][0]
    jours[0]["exercices"][0]["exercise_id"] = ex.id
    jours[0]["exercices"][0]["charge_kg"] = 900
    patch_ia(monkeypatch, _reponse_ia(jours))

    program, _ = ai_program.generer_programme(user_ia, [], source="ia")

    pe = program.days[0].exercises[0]
    assert pe.target_weight <= (user_ia.weight * 1.5) + 0.1


def test_nom_exercice_utilise_si_id_absent(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    ex = par_cat["pectoraux"][0]
    jours = [{"nom": "Push", "exercices": [
        {"nom": ex.name.upper(), "series": 4, "reps": 10},
        {"nom": par_cat["dos"][0].name, "series": 4, "reps": 10},
        {"nom": par_cat["quadriceps"][0].name, "series": 3, "reps": 12},
    ]}]
    patch_ia(monkeypatch, _reponse_ia(jours))

    program, meta = ai_program.generer_programme(user_ia, [], source="ia")

    assert ex.id in {pe.exercise_id for pe in program.days[0].exercises}


def test_jour_vide_complete_par_algorithme(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    jours = _jours_ia(par_cat)
    jours[1] = {"nom": "Pull", "exercices": [{"exercise_id": 999999}]}
    patch_ia(monkeypatch, _reponse_ia(jours))

    program, meta = ai_program.generer_programme(user_ia, [], source="ia")

    assert len(program.days[1].exercises) >= 1
    assert any("complétée" in a for a in meta["avertissements"])


def test_reponse_hors_format_declenche_le_repli(app_ctx, user_ia, monkeypatch):
    patch_ia(monkeypatch, "Je ne peux pas faire de programme, consulte un coach.")

    program, meta = ai_program.generer_programme(user_ia, [], source="auto")

    assert meta["source"] == "algorithme"
    assert meta["raison"]
    assert program.is_active is True
    assert len(program.days) == 3


def test_ia_source_stricte_renvoie_503_si_indisponible(app_ctx, user_ia, monkeypatch):
    patch_ia(monkeypatch, None)

    with pytest.raises(ai_program.ErreurIAProgram):
        ai_program.generer_programme(user_ia, [], source="ia")

    assert TrainingProgram.query.filter_by(user_id=user_ia.id).count() == 0


# ── Repli et choix de source ────────────────────────────────────────

def test_repli_quand_aucun_fournisseur(app_ctx, user_ia, monkeypatch):
    patch_ia(monkeypatch, None)

    program, meta = ai_program.generer_programme(user_ia, [], source="auto")

    assert meta["source"] == "algorithme"
    assert "daily_limit" in meta["raison"]
    assert program.generation_source == "algorithme"
    for day in program.days:
        assert len(day.exercises) > 0


def test_source_algorithme_nappelle_pas_ia(app_ctx, user_ia, monkeypatch):
    messages_vus = patch_ia(monkeypatch, _reponse_ia([]))

    program, meta = ai_program.generer_programme(user_ia, [], source="algorithme")

    assert messages_vus == []
    assert meta["source"] == "algorithme"
    assert program.generation_source == "algorithme"


def test_erreur_inattendue_ne_casse_pas(app_ctx, user_ia, monkeypatch):
    def boom(messages, max_tokens=2048, temperature=0.7):
        raise RuntimeError("HTTP 500")

    monkeypatch.setattr(ai_program.ai_providers, "generate_text", boom)

    program, meta = ai_program.generer_programme(user_ia, [], source="auto")

    assert meta["source"] == "algorithme"
    assert program is not None


# ── Régénération ─────────────────────────────────────────────────────

def test_regeneration_passe_les_exercices_deja_faits(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    patch_ia(monkeypatch, _reponse_ia(_jours_ia(par_cat)))
    premier, _ = ai_program.generer_programme(user_ia, [], source="ia")
    noms = {pe.exercise.name for pe in premier.days[0].exercises}

    exos = [{"exercise_id": e.id, "series": 4, "reps": 10, "repos_secondes": 120, "charge_kg": 35}
            for e in list(par_cat["pectoraux"][1:3]) + list(par_cat["dos"][:1])]
    messages_vus = patch_ia(monkeypatch, _reponse_ia([{"nom": "Push", "exercices": exos}]))
    second, meta = ai_program.generer_programme(user_ia, [], source="ia", consigne="charge un peu plus lourd")

    assert second.id > premier.id
    assert second.is_active is True
    assert TrainingProgram.query.get(premier.id).is_active is False
    assert meta["regenere"] is True
    assert meta["variation"] == 1
    prompt = messages_vus[0][-1]["content"]
    assert "VARIANTE 1" in prompt
    assert "EXERCICES DÉJÀ PRÉVUS" in prompt
    for nom in noms:
        assert nom in prompt
    assert "charge un peu plus lourd" in prompt


def test_regeneration_conserve_historique_et_progression(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    patch_ia(monkeypatch, _reponse_ia(_jours_ia(par_cat)))
    premier, _ = ai_program.generer_programme(user_ia, [], source="ia")

    ex = list(par_cat["pectoraux"])[:2]
    jour = premier.days[0]
    seance = Session(user_id=user_ia.id, program_day_id=jour.id, date=premier.start_date)
    db.session.add(seance)
    db.session.flush()
    for i, pe in enumerate(jour.exercises[:2], start=1):
        db.session.add(SessionSet(session_id=seance.id, exercise_id=pe.exercise_id,
                                   set_number=1, weight=55.0, reps=12))
    db.session.commit()

    messages_vus = patch_ia(monkeypatch, _reponse_ia(_jours_ia(par_cat)))
    second, meta = ai_program.generer_programme(user_ia, [], source="ia")

    assert meta["regenere"] is True
    # La séance reste rattachée à l'ancien programme, qui n'est plus actif
    assert seance.program_day_id == jour.id
    assert TrainingProgram.query.get(premier.id).is_active is False
    assert Session.query.filter_by(user_id=user_ia.id).count() == 1
    # Les performances réalisées sont réinjectées dans le prompt
    prompt = messages_vus[0][-1]["content"]
    assert "DERNIÈRES PERFORMANCES" in prompt
    assert "55.0 kg" in prompt


def test_variation_incremente_a_chaque_regeneration(app_ctx, user_ia, monkeypatch):
    par_cat = _par_categorie(user_ia)
    patch_ia(monkeypatch, _reponse_ia(_jours_ia(par_cat)))
    _, meta1 = ai_program.generer_programme(user_ia, [], source="ia")
    _, meta2 = ai_program.generer_programme(user_ia, [], source="ia")
    _, meta3 = ai_program.generer_programme(user_ia, [], source="ia")
    assert (meta1["variation"], meta2["variation"], meta3["variation"]) == (0, 1, 2)


# ── Utilitaires ─────────────────────────────────────────────────────

def test_parse_reponse_refuse_un_texte_hors_json():
    with pytest.raises(ValueError):
        ai_program._parse_reponse("pas de json ici")


def test_resoudre_split_mutualise(program_generator_module=None):
    u = User(goal="force", level="debutant", split_type="upper_lower", sessions_per_week=2)
    ctx = program_generator.resoudre_split(u)
    assert ctx["goal"] == "force"
    assert ctx["split_type"] == "upper_lower"
    assert ctx["days_count"] == 2

    ctx2 = program_generator.resoudre_split(u, goal="prise_masse", split_type="push_pull_legs", days_per_week=5)
    assert ctx2["split_type"] == "push_pull_legs"
    assert ctx2["days_count"] == 5


def test_borne_defaut_si_valeur_invalide():
    assert ai_program._borne("abc", 1, 8, 3) == 3
    assert ai_program._borne(None, 1, 8, 3) == 3
    assert ai_program._borne(99, 1, 8, 3) == 8
    assert ai_program._borne("4", 1, 8, 3) == 4
