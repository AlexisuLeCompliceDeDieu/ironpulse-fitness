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

# Limites par fournisseur (routeur multi-IA) : dépassées => failover automatique
PROVIDER_DEFAULTS = {
    "groq": {
        "rpm": int(os.environ.get("GROQ_RPM_LIMIT", "25")),
        "rpd": int(os.environ.get("GROQ_RPD_LIMIT", "13000")),
    },
    "gemini": {
        "rpm": int(os.environ.get("GEMINI_RPM_LIMIT", "15")),
        "rpd": int(os.environ.get("GEMINI_RPD_LIMIT", "400")),
    },
    "mistral": {
        "rpm": int(os.environ.get("MISTRAL_RPM_LIMIT", "15")),
        "rpd": int(os.environ.get("MISTRAL_RPD_LIMIT", "400")),
    },
    "openrouter": {
        "rpm": int(os.environ.get("OPENROUTER_RPM_LIMIT", "10")),
        "rpd": int(os.environ.get("OPENROUTER_RPD_LIMIT", "200")),
    },
}

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

    # Reset quotidien (le compteur ET la désactivation automatique)
    if data["rpd_date"] != today:
        data["rpd_date"] = today
        data["rpd_count"] = 0
        data["auto_disabled"] = False

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
    """Retourne le statut complet (quota Groq historique + fournisseurs IA)."""
    data = _load()
    rpm_used = len(_clean_rpm(data.get("rpm_timestamps", [])))
    rpd_used = data["rpd_count"]
    status = {
        "groq_rpm": f"{rpm_used}/{RPM_LIMIT}",
        "groq_rpd": f"{rpd_used}/{RPD_LIMIT}",
        "groq_rpm_pct": round(rpm_used / RPM_LIMIT * 100, 1),
        "groq_rpd_pct": round(rpd_used / RPD_LIMIT * 100, 1),
        "groq_auto_disabled": data.get("auto_disabled", False),
        "groq_total_all_time": data.get("total_all_time", 0),
        "groq_enabled": bool(os.environ.get("GROQ_API_KEY")),
    }
    status.update(ai_configuration_status())
    return status


def disable_today():
    """Désactive l'agent IA jusqu'à demain (ex : limites de tokens par jour atteintes).

    La désactivation se lève automatiquement au changement de date
    (voir le reset quotidien dans `check_quota`).
    """
    data = _load()
    data["auto_disabled"] = True
    _save(data)
    logger.warning("Agent IA désactivé automatiquement pour aujourd'hui")


# ── Suivi et limites PAR FOURNISSEUR (routeur multi-IA) ─────────────

def _providers(data):
    """Initialise et retourne l'index par-fournisseur du compteur."""
    index = data.setdefault("providers", {})
    for pid, lims in PROVIDER_DEFAULTS.items():
        entry = index.setdefault(pid, {
            "date": str(date.today()),
            "rpm": [],
            "rpd": 0,
            "disabled": False,
            "disabled_reason": "",
            "cooldown_until": 0.0,
        })
        entry.setdefault("rpm", [])
        entry.setdefault("rpd", 0)
        entry.setdefault("disabled", False)
        entry.setdefault("disabled_reason", "")
        entry.setdefault("cooldown_until", 0.0)
        entry.setdefault("date", str(date.today()))
        lims.setdefault("rpm", 25)
        lims.setdefault("rpd", 13000)
    return index


def _provider_entry(provider_id):
    data = _load()
    index = _providers(data)
    entry = index.setdefault(provider_id, {
        "date": str(date.today()), "rpm": [], "rpd": 0,
        "disabled": False, "disabled_reason": "", "cooldown_until": 0.0,
    })
    today = str(date.today())
    if entry["date"] != today:  # nouveau jour : réinitialise et réactive
        entry["date"] = today
        entry["rpd"] = 0
        entry["disabled"] = False
        entry["disabled_reason"] = ""
    entry["rpm"] = _clean_rpm(entry["rpm"])
    return data, entry


def can_use_provider(provider_id):
    """(ok, reason) — un fournisseur bloqué est une raison de failover."""
    _, entry = _provider_entry(provider_id)
    if entry["disabled"]:
        return False, entry.get("disabled_reason", "disabled")
    if entry.get("cooldown_until", 0) > time.time():
        return False, "cooldown"
    lims = PROVIDER_DEFAULTS.get(provider_id, {"rpm": 25, "rpd": 13000})
    if len(entry["rpm"]) >= lims["rpm"]:
        return False, "rpm_limit"
    if entry["rpd"] >= lims["rpd"]:
        return False, "rpd_limit"
    return True, None


def record_provider_usage(provider_id):
    """Comptabilise un appel réussi par fournisseur."""
    data, entry = _provider_entry(provider_id)
    entry["rpm"].append(time.time())
    entry["rpd"] += 1
    entry["cooldown_until"] = 0.0
    _save(data)


def disable_provider(provider_id, reason="daily_limit"):
    """Désactive un fournisseur (souvent jusqu'à minuit)."""
    data, entry = _provider_entry(provider_id)
    entry["disabled"] = True
    entry["disabled_reason"] = reason or "disabled"
    _save(data)
    logger.warning(f"Fournisseur {provider_id} désactivé ({reason})")


def set_provider_cooldown(provider_id, seconds=75):
    """Cooldown court après une limite par minute / taux de requêtes."""
    data, entry = _provider_entry(provider_id)
    entry["cooldown_until"] = time.time() + seconds
    _save(data)


def get_providers_status():
    """Statut lisible de chaque fournisseur (pour l'UI)."""
    data = _load()
    index = _providers(data)
    out = {}
    for pid, lims in PROVIDER_DEFAULTS.items():
        entry = index.get(pid, {})
        ok, reason = can_use_provider(pid)
        out[pid] = {
            "enabled": ok,
            "blocked_reason": reason,
            "rpm_used": len(entry.get("rpm", [])),
            "rpm_limit": lims["rpm"],
            "rpd_used": entry.get("rpd", 0),
            "rpd_limit": lims["rpd"],
            "rpd_pct": round(entry.get("rpd", 0) / lims["rpd"] * 100, 1),
            "disabled": entry.get("disabled", False),
            "disabled_reason": entry.get("disabled_reason", ""),
        }
    return out


# ── API publique historique (rétro-compat) ──────────────────────────

def ai_configuration_status():
    """Retourne un statut agrégé compatible avec l'UI existante."""
    providers = get_providers_status()
    configured = [pid for pid, st in providers.items() if _provider_configured(pid)]
    any_configured = bool(configured)
    any_usable = any(st["enabled"] for pid, st in providers.items() if _provider_configured(pid))
    max_rpd_pct = max((st["rpd_pct"] for pid, st in providers.items()
                       if _provider_configured(pid)), default=0.0)
    max_rpm_pct = max((round(st["rpm_used"] / st["rpm_limit"] * 100, 1)
                       for pid, st in providers.items()
                       if _provider_configured(pid) and st["rpm_limit"]), default=0.0)
    return {
        "groq_enabled": any_configured,
        "groq_usable": any_usable,
        "groq_auto_disabled": not any_usable and any_configured,
        "groq_rpd": f"{sum(st['rpd_used'] for st in providers.values())}",
        "groq_rpd_pct": max_rpd_pct,
        "groq_rpm_pct": max_rpm_pct,
        "providers": providers,
    }


def _provider_configured(provider_id):
    return bool(os.environ.get({
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }.get(provider_id, "")))


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
