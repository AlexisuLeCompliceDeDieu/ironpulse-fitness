"""Chat IA "IRONPULSE Coach" — assistant conversationnel via Groq (streaming SSE).

Point d'entrée : POST /api/chat/
  body : {"messages": [{"role": "user", "content": "..."}, ...]}
  réponse : EventSource de tokens (data: {"token": "..."}), terminé par data: [DONE].
"""

import json
import logging
from flask import Blueprint, request, jsonify, session, Response

logger = logging.getLogger(__name__)

from services.groq_config import get_client, GROQ_MODEL, GROQ_ENABLED
from services import quota_tracker

chat_bp = Blueprint("chat", __name__)

MAX_HISTORY = 24   # derniers messages envoyés au modèle (au total)
MAX_TOKENS = 2048
TEMPERATURE = 0.7

GOAL_LABELS = {
    "prise_masse": "Prise de masse",
    "perte_poids": "Perte de poids",
    "force": "Développement de la force",
    "endurance": "Amélioration de l'endurance",
}


def _current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    from models import User, db
    return db.session.get(User, user_id)


def _system_prompt(user):
    from services.nutrition import current_calories

    goal_label = GOAL_LABELS.get(user.goal, user.goal or "non renseigné")
    prefs = user.preferences_list() if hasattr(user, "preferences_list") else []
    equipment = user.equipment_list() if hasattr(user, "equipment_list") else []
    kcal = current_calories(user)

    return f"""Tu es « IRONPULSE Coach », un coach sportif et nutritionniste intégré à l'application IRONPULSE. Tu accompagnes un utilisateur dans son entraînement, sa nutrition et sa progression.

PROFIL ACTUEL DE L'UTILISATEUR :
- Pseudo : {user.username}
- Objectif : {goal_label}
- Niveau : {user.level}
- Poids : {user.weight} kg · Poids cible : {user.target_weight} kg
- Taille : {user.height} cm · Âge : {user.age} ans
- Calories cibles : {kcal} kcal/jour
- Restrictions alimentaires : {', '.join(prefs) if prefs else 'aucune'}
- Entraînement : split {user.split_type or 'automatique selon objectif'} · {user.sessions_per_week or 'auto'} séance(s)/semaine
- Matériel disponible : {', '.join(equipment) if equipment else 'non renseigné'}

RÈGLES :
- Réponds en français, de façon concise (2 à 6 phrases), pratique et encourageante.
- Personnalise à partir du profil (alimentation, programme, progression). Tu peux calculer des macros ou proposer des repas précis avec quantités en grammes.
- Conseils éthiques, réalistes et sûrs ; signale de consulter un médecin quand c'est pertinent.
- Si la question ne concerne pas le fitness/nutrition, recentre poliment."""  # noqa: E501


@chat_bp.route("/", methods=["POST"])
def chat():
    user = _current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json(silent=True) or {}
    messages = data.get("messages")
    if not messages or not isinstance(messages, list) or len(messages) == 0:
        return jsonify({"error": "messages requis"}), 400

    # Vérification quota AVANT d'ouvrir le stream
    allowed, quota_info = quota_tracker.check_quota()
    if not allowed:
        reason = quota_info.get("reason", "quota")
        return jsonify({"error": f"Quota IA épuisé (raison : {reason}). Réessayez plus tard.", "quota": quota_info}), 429

    client = get_client()
    if client is None:
        return jsonify({"error": "Agent IA non configuré", "groq_enabled": GROQ_ENABLED}), 503

    # Historique borné pour rester rapide et sous la limite de contexte
    history = [
        {"role": m.get("role"), "content": (m.get("content") or "")[:4000]}
        for m in messages[-MAX_HISTORY:]
    ]
    payload = [{"role": "system", "content": _system_prompt(user)}] + history

    try:
        stream = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=payload,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"Chat Groq : échec du démarrage du stream : {e}")
        return jsonify({"error": f"Erreur d'appel IA : {str(e)[:200]}"}), 502

    def generate():
        try:
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {json.dumps({'token': delta}, ensure_ascii=False)}\n\n"
            # Consommation comptabilisée une seule fois par réponse complète
            quota_tracker.record_usage()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Chat Groq : erreur pendant le stream : {e}")
            yield f"data: {json.dumps({'error': 'Erreur pendant la génération'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@chat_bp.route("/status", methods=["GET"])
def status():
    """Statut de l'assistant IA (accessible aux utilisateurs connectés)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    return jsonify({
        "groq_enabled": GROQ_ENABLED,
        "model": GROQ_MODEL if GROQ_ENABLED else None,
        "quota": quota_tracker.get_status(),
    }), 200