"""Configuration du client Groq pour l'agent IA nutrition."""

import os
import logging

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_ENABLED = bool(GROQ_API_KEY)


def get_client():
    """Retourne un client Groq ou None si non configuré."""
    if not GROQ_ENABLED:
        logger.warning("GROQ_API_KEY non définie — agent IA désactivé")
        return None
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Erreur création client Groq: {e}")
        return None
