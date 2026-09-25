"""Tests de l'agent agentique IRONPULSE.

Couvre les exigences du cahier des charges :
  - la boucle agent (raisonner -> agir -> observer -> décider) ;
  - la trace en base (demandes / resultats avec outil_utilise) ;
  - la validation humaine des tools d'écriture (enregistrer_seance) ;
  - la gestion d'erreurs (tool en échec, quota, max_tours).

Le LLM est simulé au niveau du routeur (`_completion`), qui est le point
d'entrée de l'agent vers le failover multi-fournisseurs.
"""

import json

import pytest

from models import db, User, Session, Demande

from agent import agent as agent_runner
from agent import tools as agent_tools


@pytest.fixture()
def app_ctx(app):
    """Donne un contexte d'application actif pour toucher directement à la base."""
    with app.app_context():
        yield


# ── Fabrication d'une réponse LLM simulée (format du routeur) ──────

class _Call(dict):
    """Appel de tool normalisé : {id, name, arguments}."""

    def __init__(self, name, arguments=None, id="call_1"):
        super().__init__(id=id, name=name, arguments=arguments or {})


def _Msg(content, tool_calls=None):
    """Réponse LLM normalisée : {content, tool_calls}."""
    return {"content": content or "", "tool_calls": tool_calls or []}


def _Resp(msg):
    """Alias historique : une réponse est simplement un dict normalisé."""
    return msg


def seed_user():
    u = User(username="agent_test", email="agent@test.fr", password_hash="x")
    db.session.add(u)
    db.session.commit()
    return u


def patch_llm(monkeypatch, script, label="Groq"):
    """Simule le routeur multi-IA : renvoie les réponses du script dans l'ordre."""
    restante = list(script)
    appels = []

    def fake_completion(messages, max_tokens=900):
        appels.append(messages)
        reponse = restante.pop(0) if restante else _Msg("Terminé.")
        return reponse, {"provider": "groq", "label": label, "model": "modele-test"}

    monkeypatch.setattr(agent_runner, "_completion", fake_completion)
    monkeypatch.setattr(
        agent_runner.ai_providers, "available_provider",
        lambda: ("groq", type("P", (), {"label": label})(), None),
    )
    return appels


# ── Route : garde-fous de base ──────────────────────────────────────

def test_agent_unauthenticated(client):
    resp = client.post("/api/agent/", json={"demande": "bonjour"})
    assert resp.status_code == 401


def test_agent_demande_vide(auth_client):
    resp = auth_client.post("/api/agent/", json={"demande": "   "})
    assert resp.status_code == 400


def test_agent_confirmation_tool_inconnu(auth_client):
    resp = auth_client.post("/api/agent/", json={
        "demande": "test",
        "confirmation": {"tool": "supprimer_tout", "arguments": {}},
    })
    assert resp.status_code == 400


# ── Boucle agent ────────────────────────────────────────────────────

def test_executer_reponse_directe(app_ctx, monkeypatch):
    """Cas nominal : le LLM répond sans tool -> réponse + trace en base."""
    patch_llm(monkeypatch, [_Resp(_Msg("Salut !", []))])
    utilisateur = seed_user()

    resultat = agent_runner.executer(utilisateur, "Dis moi bonjour")

    assert resultat["statut"] == "reponse"
    assert resultat["reponse"] == "Salut !"
    demande = Demande.query.filter_by(utilisateur_id=utilisateur.id).one()
    assert demande.texte == "Dis moi bonjour"
    assert len(demande.resultats) == 1
    assert demande.resultats[0].outil_utilise is None
    assert demande.resultats[0].reponse == "Salut !"
    assert resultat["demande_id"] == demande.id


def test_executer_trace_le_fournisseur(app_ctx, monkeypatch):
    """Le fournisseur ayant répondu (après failover) est renvoyé à l'UI."""
    patch_llm(monkeypatch, [_Resp(_Msg("Salut !", []))], label="Google Gemini")
    utilisateur = seed_user()

    resultat = agent_runner.executer(utilisateur, "Dis moi bonjour")

    assert resultat["statut"] == "reponse"
    assert resultat["fournisseur"] == "Google Gemini"


def test_executer_appelle_tool_puis_repond(app_ctx, monkeypatch):
    """Niveau 2 : le LLM choisit calculer_macros, observe, puis conclut."""
    call = _Call("calculer_macros", {"calories": 3000, "objectif": "prise_masse"})
    patch_llm(monkeypatch, [
        _Resp(_Msg("", [call])),
        _Resp(_Msg("Voici ta répartition : 225 g de protéines", [])),
    ])
    utilisateur = seed_user()

    resultat = agent_runner.executer(utilisateur, "Répartis mes 3000 kcal")

    assert resultat["statut"] == "reponse"
    assert len(resultat["etapes"]) == 1
    assert resultat["etapes"][0]["outil"] == "calculer_macros"
    assert resultat["etapes"][0]["resultat"]["proteines_g"] == 225
    assert resultat["etapes"][0]["resultat"]["glucides_g"] == 375

    demande = Demande.query.filter_by(utilisateur_id=utilisateur.id).one()
    assert len(demande.resultats) == 2
    trace = [r for r in demande.resultats if r.outil_utilise]
    assert trace[0].outil_utilise == "calculer_macros"


def test_executer_max_tours(app_ctx, monkeypatch):
    """Garde-fou anti-boucle : le LLM qui boucle indéfiniment est stoppé."""
    call = _Call("calculer_macros", {"calories": 2000})
    patch_llm(monkeypatch, [_Resp(_Msg("", [call])) for _ in range(agent_runner.MAX_TOURS)])

    utilisateur = seed_user()
    resultat = agent_runner.executer(utilisateur, "boucle")

    assert resultat["statut"] == "limite"
    assert "nombre d'étapes" in resultat["reponse"]


def test_executer_quota_epuise(app_ctx, monkeypatch):
    """Aucun fournisseur IA disponible -> la boucle s'arrête proprement."""
    patch_llm(monkeypatch, [_Resp(_Msg("", []))])
    monkeypatch.setattr(agent_runner.ai_providers, "available_provider", lambda: (None, None, "none_available"))

    utilisateur = seed_user()
    resultat = agent_runner.executer(utilisateur, "dis bonjour")

    assert resultat["statut"] == "quota"


def test_tool_en_echec_renvoie_message(app_ctx):
    """Un tool qui échoue renvoie un dict d'erreur, pas une exception."""
    assert agent_tools.enregistrer_seance(999999, ressenti=9)["error"]
    assert agent_tools.enregistrer_seance(999999, ressenti=3, date="hier")["error"]
    assert agent_runner._execute_tool("tool_inconnu", {})["error"]


# ── Validation humaine des tools d'écriture ─────────────────────────

def test_tool_ecriture_demande_confirmation(app_ctx, monkeypatch):
    """enregistrer_seance est SENSIBLE : sans validation, l'action est en pause."""
    call = _Call("enregistrer_seance", {"date": "2026-09-20", "ressenti": 4})
    patch_llm(monkeypatch, [_Resp(_Msg("", [call]))])
    utilisateur = seed_user()

    resultat = agent_runner.executer(utilisateur, "Enregistre ma séance d'hier")

    assert resultat["statut"] == "confirmation_requise"
    assert resultat["confirmation"]["tool"] == "enregistrer_seance"
    assert Session.query.count() == 0
    assert Demande.query.count() == 1


def test_executer_avec_confirmation_execute(app_ctx, monkeypatch):
    """Après validation, l'action d'écriture est exécutée puis la boucle conclut."""
    patch_llm(monkeypatch, [_Resp(_Msg("Séance enregistrée, ressenti 4/5.", []))])
    utilisateur = seed_user()

    resultat = agent_runner.executer(
        utilisateur,
        "Enregistre ma séance d'hier",
        confirmation={"tool": "enregistrer_seance", "arguments": {"date": "2026-09-20", "ressenti": 4}},
    )

    assert resultat["statut"] == "reponse"
    session_obj = Session.query.one()
    assert session_obj.feeling == 4
    demande = Demande.query.one()
    assert demande.resultats[0].outil_utilise == "enregistrer_seance"


# ── Outils : lecture réelle en base ─────────────────────────────────

def test_consulter_progression_vide(app_ctx):
    u = seed_user()
    data = agent_tools.consulter_progression(u.id)
    assert data["total_sessions"] == 0
    assert data["message"]


def test_consulter_profil(app_ctx):
    u = seed_user()
    data = agent_tools.consulter_profil(u.id)
    assert data["pseudo"] == "agent_test"
    assert data["calories_cibles"] > 0


def test_calculer_macros_pure(app_ctx):
    data = agent_tools.calculer_macros(2000, "prise_masse")
    assert data["proteines_g"] == 150   # 2000 * 0.30 / 4
    assert data["lipides_g"] == 44      # 2000 * 0.20 / 9 ~ 44
    assert agent_tools.calculer_macros(-10)["error"]


# ── Route : historique (mémoire / audit) ────────────────────────────

def test_historique_agent(auth_client, monkeypatch):
    patch_llm(monkeypatch, [_Resp(_Msg("Réponse tracée", []))])
    resp = auth_client.post("/api/agent/", json={"demande": "ma première demande"})
    assert resp.status_code == 200
    assert resp.get_json()["statut"] == "reponse"

    hist = auth_client.get("/api/agent/historique")
    assert hist.status_code == 200
    demandes = hist.get_json()["demandes"]
    assert demandes[0]["texte"] == "ma première demande"
    assert demandes[0]["resultats"][0]["reponse"] == "Réponse tracée"


# ── Catalogue des outils (affichage UI) ─────────────────────────────

def test_catalogue_outils(auth_client):
    resp = auth_client.get("/api/agent/outils")
    assert resp.status_code == 200
    outils = resp.get_json()["outils"]
    noms = {o["nom"] for o in outils}
    assert noms == {
        "consulter_profil", "consulter_progression", "calculer_macros",
        "proposer_seance", "enregistrer_seance",
    }
    for o in outils:
        assert o["libelle"] and o["icone"] and o["description"]
    sensible = [o for o in outils if o["sensible"]]
    assert [o["nom"] for o in sensible] == ["enregistrer_seance"]


def test_catalogue_outils_unauthenticated(client):
    assert client.get("/api/agent/outils").status_code == 401


# ── Flux SSE : les étapes de la boucle en direct ────────────────────

def _lire_events(resp):
    """Décode une réponse SSE de l'agent en liste d'événements."""
    evenements = []
    for bloc in resp.data.decode("utf-8").split("\n\n"):
        ligne = bloc.strip()
        if not ligne.startswith("data:"):
            continue
        payload = ligne[5:].strip()
        if payload == "[DONE]":
            continue
        evenements.append(json.loads(payload))
    return evenements


def test_stream_unauthenticated(client):
    resp = client.post("/api/agent/stream", json={"demande": "bonjour"})
    assert resp.status_code == 401


def test_stream_events_boucle_complete(auth_client, monkeypatch):
    call = _Call("calculer_macros", {"calories": 3000, "objectif": "prise_masse"})
    patch_llm(monkeypatch, [
        _Resp(_Msg("", [call])),
        _Resp(_Msg("Ta répartition est prête.", [])),
    ])

    resp = auth_client.post("/api/agent/stream", json={"demande": "Répartis mes 3000 kcal"})
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"

    types = [e["type"] for e in _lire_events(resp)]
    assert types[0] == "debut"
    assert "tour" in types
    assert "tool_debut" in types
    assert "tool_fin" in types
    assert types[-1] == "reponse"

    evenements = _lire_events(resp)
    tour = next(e for e in evenements if e["type"] == "tour")
    assert tour["fournisseur"] == "Groq"          # fournisseur ayant répondu ce tour
    fin = next(e for e in evenements if e["type"] == "tool_fin")
    assert fin["outil"] == "calculer_macros"
    assert fin["icone"] == "🧮"
    assert "protéines" in fin["resume"]
    assert isinstance(fin["duree_ms"], int)


def test_stream_confirmation_met_en_pause(auth_client, app_ctx, monkeypatch):
    call = _Call("enregistrer_seance", {"date": "2026-09-20", "ressenti": 4})
    patch_llm(monkeypatch, [_Resp(_Msg("", [call]))])

    resp = auth_client.post("/api/agent/stream", json={"demande": "Enregistre ma séance"})
    events = _lire_events(resp)
    types = [e["type"] for e in events]

    assert "confirmation" in types
    assert types[-1] == "confirmation"
    conf = next(e for e in events if e["type"] == "confirmation")
    assert conf["confirmation"]["tool"] == "enregistrer_seance"
    assert conf["icone"] == "✅"
    # l'action d'écriture n'a PAS été exécutée avant validation
    assert Session.query.count() == 0