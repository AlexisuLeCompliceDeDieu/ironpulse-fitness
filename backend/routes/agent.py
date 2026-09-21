"""Route des requêtes adressées à l'agent IRONPULSE (boucle agentique).

POST /api/agent/         {demande, confirmation?}
  - Sans confirmation : lance la boucle agent. Si l'agent demande l'exécution
    d'un tool d'écriture, la réponse est `confirmation_requise` : l'action est
    MISE EN PAUSE et soumise à la validation humaine (diapo 18 du CDC).
  - Avec confirmation : l'action validée par l'utilisateur est exécutée puis
    la boucle reprend pour produire la réponse finale.

POST /api/agent/stream   même contrat, mais renvoie un flux SSE (text/event-stream)
  d'événements décrivant la boucle en direct : debut, tour, tool_debut,
  tool_fin, confirmation, reponse, limite, quota, erreur. C'est ce qui permet
  à l'interface de montrer les tools appelés au fur et à mesure.

GET /api/agent/outils     catalogue des tools (nom, description, icône, sensible).
GET /api/agent/historique dernières demandes + trace des étapes (mémoire).

Chaque appel à l'agent est tracé en base (tables demandes / resultats dans
SQLite) : c'est ce qui rend le raisonnement auditable en soutenance.
"""

import json
import logging

from flask import Blueprint, jsonify, request, session, Response, stream_with_context

from models import db, User, Demande

from agent import agent as agent_runner
from agent.tools import SENSITIVE_TOOLS, TOOL_CATALOG

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__)

MAX_DEMANDE_LENGTH = 2000


def _current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def _parse_body(data):
    """Valide le corps de requête. Retourne (demande, confirmation, demande_id, erreur)."""
    demande = (data.get("demande") or "").strip()
    if not demande:
        return None, None, None, (jsonify({"error": "demande requise", "statut": "erreur"}), 400)
    if len(demande) > MAX_DEMANDE_LENGTH:
        return None, None, None, (
            jsonify({"error": f"demande trop longue (max {MAX_DEMANDE_LENGTH} caractères)", "statut": "erreur"}), 400
        )

    confirmation = data.get("confirmation")
    if confirmation is not None:
        if not isinstance(confirmation, dict):
            return None, None, None, (jsonify({"error": "confirmation invalide", "statut": "erreur"}), 400)
        if confirmation.get("tool") not in SENSITIVE_TOOLS:
            return None, None, None, (jsonify({"error": "tool de confirmation inconnu", "statut": "erreur"}), 400)
        if not isinstance(confirmation.get("arguments"), dict):
            return None, None, None, (jsonify({"error": "arguments de confirmation invalides", "statut": "erreur"}), 400)

    return demande, confirmation, (confirmation or {}).get("demande_id"), None


@agent_bp.route("/", methods=["POST"])
def run_agent():
    utilisateur = _current_user()
    if not utilisateur:
        return jsonify({"error": "Non authentifié"}), 401

    demande, confirmation, demande_id, erreur = _parse_body(request.get_json(silent=True) or {})
    if erreur:
        return erreur

    resultat = agent_runner.executer(utilisateur, demande, confirmation=confirmation, demande_id=demande_id)

    if resultat["statut"] == "quota":
        return jsonify(resultat), 429
    if resultat["statut"] == "erreur":
        if "non configuré" in resultat["reponse"]:
            return jsonify(resultat), 503
        return jsonify(resultat), 400

    return jsonify(resultat), 200


@agent_bp.route("/stream", methods=["POST"])
def stream_agent():
    """Boucle agent diffusée en SSE : chaque étape (tool) est visible en direct."""
    utilisateur = _current_user()
    if not utilisateur:
        return jsonify({"error": "Non authentifié"}), 401

    demande, confirmation, demande_id, erreur = _parse_body(request.get_json(silent=True) or {})
    if erreur:
        return erreur

    def generate():
        try:
            for evenement in agent_runner.executer_iter(
                utilisateur, demande, confirmation=confirmation, demande_id=demande_id
            ):
                yield f"data: {json.dumps(evenement, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:  # noqa: BLE001
            logger.exception("Agent : erreur pendant le flux SSE")
            payload = {"type": "erreur", "reponse": f"Erreur interne : {str(e)[:200]}"}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@agent_bp.route("/outils", methods=["GET"])
def outils():
    """Catalogue des tools de l'agent (pour l'affichage dans l'interface)."""
    utilisateur = _current_user()
    if not utilisateur:
        return jsonify({"error": "Non authentifié"}), 401
    return jsonify({"outils": TOOL_CATALOG}), 200


@agent_bp.route("/historique", methods=["GET"])
def historique():
    """Dernières demandes de l'utilisateur avec la trace des étapes de l'agent."""
    utilisateur = _current_user()
    if not utilisateur:
        return jsonify({"error": "Non authentifié"}), 401

    demandes = (
        Demande.query.filter_by(utilisateur_id=utilisateur.id)
        .order_by(Demande.date_creation.desc(), Demande.id.desc())
        .limit(20)
        .all()
    )
    return jsonify({"demandes": [d.to_dict() for d in demandes]}), 200
