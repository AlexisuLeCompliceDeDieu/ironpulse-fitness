"""Route des requêtes adressées à l'agent IRONPULSE (boucle agentique).

POST /api/agent/  {demande, confirmation?}
  - Sans confirmation : lance la boucle agent. Si l'agent demande l'exécution
    d'un tool d'écriture, la réponse est `confirmation_requise` : l'action est
    MISE EN PAUSE et soumise à la validation humaine (diapo 18 du CDC).
  - Avec confirmation : l'action validée par l'utilisateur est exécutée puis
    la boucle reprend pour produire la réponse finale.

GET /api/agent/historique   dernières demandes + trace des étapes (mémoire).

Chaque appel à l'agent est tracé en base (tables demandes / resultats dans
SQLite) : c'est ce qui rend le raisonnement auditable en soutenance.
"""

import logging

from flask import Blueprint, jsonify, request, session

from models import db, User, Demande

from agent import agent as agent_runner
from agent.tools import SENSITIVE_TOOLS

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__)

MAX_DEMANDE_LENGTH = 2000


def _current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


@agent_bp.route("/", methods=["POST"])
def run_agent():
    utilisateur = _current_user()
    if not utilisateur:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json(silent=True) or {}
    demande = (data.get("demande") or "").strip()
    if not demande:
        return jsonify({"error": "demande requise", "statut": "erreur"}), 400
    if len(demande) > MAX_DEMANDE_LENGTH:
        return jsonify({"error": f"demande trop longue (max {MAX_DEMANDE_LENGTH} caractères)", "statut": "erreur"}), 400

    confirmation = data.get("confirmation")
    if confirmation is not None:
        if not isinstance(confirmation, dict):
            return jsonify({"error": "confirmation invalide", "statut": "erreur"}), 400
        tool_nom = confirmation.get("tool")
        if tool_nom not in SENSITIVE_TOOLS:
            return jsonify({"error": "tool de confirmation inconnu", "statut": "erreur"}), 400
        if not isinstance(confirmation.get("arguments"), dict):
            return jsonify({"error": "arguments de confirmation invalides", "statut": "erreur"}), 400

    resultat = agent_runner.executer(
        utilisateur,
        demande,
        confirmation=confirmation,
        demande_id=(confirmation or {}).get("demande_id"),
    )

    if resultat["statut"] == "quota":
        return jsonify(resultat), 429
    if resultat["statut"] == "erreur":
        if "non configuré" in resultat["reponse"]:
            return jsonify(resultat), 503
        return jsonify(resultat), 400

    return jsonify(resultat), 200


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