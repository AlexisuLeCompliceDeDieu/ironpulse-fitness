"""Chat IA "IRONPULSE Coach" — assistant conversationnel multi-IA (streaming SSE).

Point d'entrée : POST /api/chat/
  body : {"messages": [{"role": "user", "content": "..."}, ...]}
  réponse : EventSource de tokens (data: {"token": "..."}), terminé par data: [DONE].

Le routeur `ai_providers` choisit le premier fournisseur disponible (Groq,
Gemini, Mistral, OpenRouter) et bascule automatiquement en cas de limite.
"""

import json
import logging
from flask import Blueprint, request, jsonify, session, Response

from services import ai_providers

logger = logging.getLogger(__name__)

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

    # Historique borné pour rester rapide et sous la limite de contexte
    history = [
        {"role": m.get("role"), "content": (m.get("content") or "")[:4000]}
        for m in messages[-MAX_HISTORY:]
    ]
    payload = [{"role": "system", "content": _system_prompt(user)}] + history

    # Vérification QUANTIQUE : un fournisseur est-il disponible ?
    pid, provider, _ = ai_providers.available_provider()
    if provider is None:
        return jsonify({
            "error": "Aucune IA disponible (tous les fournisseurs ont atteint leur limite).",
            "quota": quota_status(),
        }), 429

    stream, info = ai_providers.stream_text(
        payload, max_tokens=MAX_TOKENS, temperature=TEMPERATURE
    )
    if stream is None:
        return jsonify({
            "error": "Aucune IA disponible (tous les fournisseurs ont atteint leur limite).",
            "quota": quota_status(),
        }), 429

    provider_label = info.get("label") or info.get("provider") or "IA"

    def generate():
        got_any = False
        try:
            for delta in stream:
                if delta:
                    got_any = True
                    yield f"data: {json.dumps({'token': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001
            logger.error(f"Chat IA : erreur pendant le stream : {e}")
            yield f"data: {json.dumps({'error': 'Erreur pendant la génération'}, ensure_ascii=False)}\n\n"
        if not got_any:
            msg = f"Le fournisseur {provider_label} n'a rien renvoyé"
            yield f"data: {json.dumps({'error': msg}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


def quota_status():
    """Petit résumé du quota pour les messages d'erreur du chat."""
    try:
        from services import quota_tracker
        return quota_tracker.get_status()
    except Exception:
        return {}


@chat_bp.route("/status", methods=["GET"])
def status():
    """Statut de l'assistant IA (accessible aux utilisateurs connectés)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    active = ai_providers.active_provider_id()
    return jsonify({
        "groq_enabled": any(p.configured for p in ai_providers.PROVIDERS.values()),
        "model": ai_providers.PROVIDERS[active].model if active else None,
        "provider": active,
        "quota": quota_status(),
    }), 200