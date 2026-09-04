"""Suivi du quota d'appels Groq — alerte avant dépassement.

Limites tier gratuit Groq (septembre 2026) :
  - 30 requêtes / minute
  - 14 400 requêtes / jour  (≈ 10 req/min × 24h)

Le compteur est persisté sur disque (JSON) pour survivre aux redémarrages
du serveur Render (free tier = dyno sleep après 15 min d'inactivité).
"""

import json
import os
import time
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

# ── Limites configurables ──────────────────────────────────────────
RPM_LIMIT = int(os.environ.get("GROQ_RPM_LIMIT", "25"))       # 25/30 (marge de sécurité)
RPD_LIMIT = int(os.environ.get("GROQ_RPD_LIMIT", "13000"))     # 13000/14400 (marge)
RPM_WARN_PCT = float(os.environ.get("GROQ_RPM_WARN", "0.8"))   # avertir à 80%
RPD_WARN_PCT = float(os.environ.get("GROQ_RPD_WARN", "0.85"))  # avertir à 85%

# ── Fichier de persistance ─────────────────────────────────────────
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_QUOTA_FILE = os.path.join(_DATA_DIR, "groq_quota.json")


def _load():
    """Charge le compteur depuis le disque."""
    try:
        with open(_QUOTA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "rpm_timestamps": [],
            "rpd_date": str(date.today()),
            "rpd_count": 0,
            "total_all_time": 0,
            "auto_disabled": False,
            "last_warning": "",
        }


def _save(data):
    """Sauvegarde le compteur sur disque."""
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_QUOTA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Erreur sauvegarde quota: {e}")


def _clean_rpm(timestamps):
    """Supprime les timestamps de plus d'1 minute."""
    cutoff = time.time() - 60
    return [t for t in timestamps if t > cutoff]


def check_quota():
    """Vérifie le quota. Retourne (allowed: bool, info: dict)."""
    data = _load()
    now = time.time()
    today = str(date.today())

    # Reset quotidien
    if data["rpd_date"] != today:
        data["rpd_date"] = today
        data["rpd_count"] = 0

    # RPM
    data["rpm_timestamps"] = _clean_rpm(data.get("rpm_timestamps", []))
    rpm_used = len(data["rpm_timestamps"])

    # RPD
    rpd_used = data["rpd_count"]

    # Vérifications
    rpm_full = rpm_used >= RPM_LIMIT
    rpd_full = rpd_used >= RPD_LIMIT
    disabled = data.get("auto_disabled", False)

    rpm_warn = rpm_used >= int(RPM_LIMIT * RPM_WARN_PCT)
    rpd_warn = rpd_used >= int(RPD_LIMIT * RPD_WARN_PCT)

    info = {
        "rpm_used": rpm_used,
        "rpm_limit": RPM_LIMIT,
        "rpm_warn_pct": RPM_WARN_PCT,
        "rpd_used": rpd_used,
        "rpd_limit": RPD_LIMIT,
        "rpd_warn_pct": RPD_WARN_PCT,
        "auto_disabled": disabled,
    }

    if disabled:
        logger.warning("Agent IA AUTO-DÉSACTIVÉ (quota dépassé)")
        info["reason"] = "auto_disabled"
        return False, info

    if rpm_full:
        info["reason"] = "rpm_limit"
        logger.warning(f"RPM limit atteint ({rpm_used}/{RPM_LIMIT})")
        return False, info

    if rpd_full:
        info["reason"] = "rpd_limit"
        logger.warning(f"RPD limit atteint ({rpd_used}/{RPD_LIMIT})")
        data["auto_disabled"] = True
        _save(data)
        info["auto_disabled"] = True
        return False, info

    # Alertes
    if rpm_warn:
        pct = round(rpm_used / RPM_LIMIT * 100, 1)
        msg = f"⚠️ RPM: {rpm_used}/{RPM_LIMIT} ({pct}%)"
        if data.get("last_warning") != msg:
            logger.warning(msg)
            data["last_warning"] = msg
        info["warning"] = msg

    if rpd_warn:
        pct = round(rpd_used / RPD_LIMIT * 100, 1)
        msg = f"⚠️ RPD: {rpd_used}/{RPD_LIMIT} ({pct}%)"
        if data.get("last_warning") != msg:
            logger.warning(msg)
            data["last_warning"] = msg
        info["warning"] = msg

    _save(data)
    return True, info


def record_usage():
    """Enregistre un appel API consommé."""
    data = _load()
    now = time.time()
    today = str(date.today())

    if data["rpd_date"] != today:
        data["rpd_date"] = today
        data["rpd_count"] = 0

    data["rpm_timestamps"] = _clean_rpm(data.get("rpm_timestamps", []))
    data["rpm_timestamps"].append(now)
    data["rpd_count"] += 1
    data["total_all_time"] += 1
    data["auto_disabled"] = False

    _save(data)


def get_status():
    """Retourne le statut complet du quota (pour /healthz)."""
    data = _load()
    rpm_used = len(_clean_rpm(data.get("rpm_timestamps", [])))
    rpd_used = data["rpd_count"]
    return {
        "groq_rpm": f"{rpm_used}/{RPM_LIMIT}",
        "groq_rpd": f"{rpd_used}/{RPD_LIMIT}",
        "groq_rpm_pct": round(rpm_used / RPM_LIMIT * 100, 1),
        "groq_rpd_pct": round(rpd_used / RPD_LIMIT * 100, 1),
        "groq_auto_disabled": data.get("auto_disabled", False),
        "groq_total_all_time": data.get("total_all_time", 0),
        "groq_enabled": bool(os.environ.get("GROQ_API_KEY")),
    }


def reset_quota():
    """Reset complet (admin)."""
    _save({
        "rpm_timestamps": [],
        "rpd_date": str(date.today()),
        "rpd_count": 0,
        "total_all_time": 0,
        "auto_disabled": False,
        "last_warning": "",
    })
    logger.info("Quota Groq réinitialisé")
