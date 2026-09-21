"""Tools de l'agent IRONPULSE.

Un tool est une fonction Python ordinaire, décrite au modèle en langage
naturel (schéma JSON), que celui-ci peut demander à exécuter. Le LLM renvoie
une intention (nom + arguments) ; c'est TOOLS_IMPL qui exécute réellement.

Trois catégories couvertes (annexe A, schéma 5 du cahier des charges) :
  - Lecture   : consulter_profil, consulter_progression
  - Calcul    : calculer_macros
  - Lecture   : proposer_seance (recommandation à partir des données)
  - Écriture  : enregistrer_seance  ← sensible, demande la validation humaine

Règles :
  - une responsabilité unique par tool ;
  - des retours structurés (dict / list) sérialisables en JSON, pas du texte libre ;
  - en cas d'erreur, retourner un dict {"error": ...} au lieu de lever une exception.
"""

import json
from datetime import date as date_cls, datetime

from models import db, User, Session, SessionSet


# ─────────────────────────────────────────────────────────────────────
#  Implémentations (une fonction Python ordinaire)
# ─────────────────────────────────────────────────────────────────────

def consulter_profil(utilisateur_id: int) -> dict:
    """Retourne le profil complet de l'utilisateur depuis SQLite."""
    user = db.session.get(User, utilisateur_id)
    if not user:
        return {"error": "Utilisateur introuvable."}

    from services.nutrition import current_calories

    kcal = current_calories(user)
    return {
        "resume": f"{user.username} · objectif {user.goal or 'non renseigné'} · {kcal} kcal/j · {user.weight or '?'} kg",
        "pseudo": user.username,
        "objectif": user.goal,
        "niveau": user.level,
        "poids_kg": user.weight,
        "poids_cible_kg": user.target_weight,
        "taille_cm": user.height,
        "age": user.age,
        "calories_cibles": kcal,
        "restrictions": user.preferences_list(),
        "materiel": user.equipment_list(),
        "split": user.split_type or "automatique selon objectif",
        "seances_par_semaine": user.sessions_per_week or "auto",
    }


def consulter_progression(utilisateur_id: int) -> dict:
    """Retourne les statistiques de progression depuis l'historique des séances."""
    sessions = (
        Session.query.filter_by(user_id=utilisateur_id)
        .order_by(Session.date)
        .all()
    )
    if not sessions:
        return {
            "resume": "Aucune séance enregistrée pour le moment.",
            "message": "Aucune séance enregistrée pour le moment.",
            "total_sessions": 0,
            "volume_total_kg": 0,
            "ressenti_moyen": None,
            "dernieres_seances": [],
        }

    total_volume = 0.0
    ressenti_total = 0
    for s in sessions:
        for st in s.sets:
            if st.completed and st.reps and st.reps > 0:
                total_volume += (st.weight or 0.0) * st.reps
        ressenti_total += s.feeling or 0

    # Progression de charge par exercice (premier max vs dernier max)
    by_exercise = {}
    for s in sessions:
        per_day = {}
        for st in s.sets:
            if not st.exercise:
                continue
            name = st.exercise.name
            w = st.weight or 0
            if name not in per_day or w > per_day[name]:
                per_day[name] = w
        for name, w in per_day.items():
            by_exercise.setdefault(name, []).append(w)

    progression = []
    for name, weights in by_exercise.items():
        if len(weights) >= 2:
            first, last = weights[0], weights[-1]
            tendance = (
                "progression" if last > first
                else "stagnation" if last == first
                else "regression"
            )
            progression.append({"exercice": name, "premiere_charge_kg": first, "derniere_charge_kg": last, "tendance": tendance})
    progression = sorted(progression, key=lambda p: p["derniere_charge_kg"] - p["premiere_charge_kg"], reverse=True)[:5]

    dernieres = []
    for s in reversed(sessions[-5:]):
        vol = sum(
            (st.weight or 0.0) * st.reps
            for st in s.sets if st.completed and st.reps and st.reps > 0
        )
        dernieres.append({
            "date": s.date.isoformat() if s.date else None,
            "ressenti": s.feeling,
            "volume_kg": round(vol, 1),
            "nb_exercices": len({st.exercise.name for st in s.sets if st.exercise}),
        })

    return {
        "resume": (
            f"{len(sessions)} séances · volume {round(total_volume, 1)} kg · "
            f"ressenti moyen {round(ressenti_total / len(sessions), 1)}/5"
        ),
        "total_sessions": len(sessions),
        "volume_total_kg": round(total_volume, 1),
        "ressenti_moyen": round(ressenti_total / len(sessions), 1),
        "dernieres_seances": dernieres,
        "progression_exercices": progression,
    }


def calculer_macros(calories: float, objectif: str = "prise_masse") -> dict:
    """Répartit un apport calorique en protéines / glucides / lipides (calcul pur)."""
    calories = float(calories or 0)
    if calories <= 0:
        return {"error": "Le nombre de calories doit être strictement positif."}

    # Répartition selon l'objectif (pourcentages des kcal)
    SPLITS = {
        "prise_masse": {"protein": 0.30, "carbs": 0.50, "fat": 0.20},
        "perte_poids": {"protein": 0.40, "carbs": 0.30, "fat": 0.30},
        "force":        {"protein": 0.30, "carbs": 0.45, "fat": 0.25},
        "endurance":    {"protein": 0.25, "carbs": 0.55, "fat": 0.20},
    }
    split = SPLITS.get(objectif, SPLITS["prise_masse"])

    protein_kcal = calories * split["protein"]
    carbs_kcal = calories * split["carbs"]
    fat_kcal = calories * split["fat"]

    return {
        "resume": (
            f"{int(round(calories))} kcal → {round(protein_kcal / 4)} g protéines / "
            f"{round(carbs_kcal / 4)} g glucides / {round(fat_kcal / 9)} g lipides"
        ),
        "calories": int(round(calories)),
        "objectif": objectif,
        "proteines_g": round(protein_kcal / 4),
        "glucides_g": round(carbs_kcal / 4),
        "lipides_g": round(fat_kcal / 9),
        "proteines_kcal": int(round(protein_kcal)),
        "glucides_kcal": int(round(carbs_kcal)),
        "lipides_kcal": int(round(fat_kcal)),
    }


def proposer_seance(utilisateur_id: int) -> dict:
    """Analyse la progression et le ressenti pour recommander la prochaine séance."""
    sessions = (
        Session.query.filter_by(user_id=utilisateur_id)
        .order_by(Session.date)
        .all()
    )
    if not sessions:
        from services.advice import generate_advice
        user = db.session.get(User, utilisateur_id)
        conseils = generate_advice(user, {"total_sessions": 0})
        recommandation = "Aucune séance enregistrée : lance le programme pour suivre ta progression."
        return {
            "resume": recommandation,
            "recommandation": recommandation,
            "intensite": "démarrage",
            "motif": "première séance",
            "conseils": [c["text"] for c in conseils][:3],
        }

    from services.advice import generate_adaptation
    recommandations = generate_adaptation(sessions)
    recommandation = recommandations[0]["text"] if recommandations else "Ton intensité est bien calibrée."
    return {
        "resume": recommandation[:160],
        "recommandation": recommandation,
        "type": recommandations[0]["type"] if recommandations else "info",
        "nb_seances_analysees": len(sessions),
        "conseils": [r["text"] for r in recommandations],
    }


def enregistrer_seance(utilisateur_id: int, date: str = None, ressenti: int = 3, notes: str = "") -> dict:
    """Enregistre une séance terminée (ressenti + notes). Tool d'écriture SENSIBLE."""
    user = db.session.get(User, utilisateur_id)
    if not user:
        return {"error": "Utilisateur introuvable."}

    try:
        ressenti = int(ressenti)
    except (TypeError, ValueError):
        return {"error": "Le ressenti doit être un entier entre 1 et 5."}
    if not 1 <= ressenti <= 5:
        return {"error": "Le ressenti doit être compris entre 1 et 5."}

    try:
        session_date = date_cls.fromisoformat(date) if date else date_cls.today()
    except (TypeError, ValueError):
        return {"error": "Le format de la date doit être AAAA-MM-JJ."}

    session_obj = Session(
        user_id=utilisateur_id,
        date=session_date,
        feeling=ressenti,
        notes=str(notes or "")[:2000],
        completed=True,
    )
    db.session.add(session_obj)
    db.session.commit()
    return {
        "resume": f"Séance du {session_obj.date.isoformat()} enregistrée (ressenti {session_obj.feeling}/5)",
        "message": "Séance enregistrée.",
        "session": {
            "id": session_obj.id,
            "date": session_obj.date.isoformat(),
            "ressenti": session_obj.feeling,
            "notes": session_obj.notes,
        },
    }


# ─────────────────────────────────────────────────────────────────────
#  Déclarations au LLM (schémas JSON) + registre nom → fonction
# ─────────────────────────────────────────────────────────────────────

TOOLS_IMPL = {
    "consulter_profil": consulter_profil,
    "consulter_progression": consulter_progression,
    "calculer_macros": calculer_macros,
    "proposer_seance": proposer_seance,
    "enregistrer_seance": enregistrer_seance,
}

# Tools dont l'exécution modifie la base : validation humaine obligatoire
SENSITIVE_TOOLS = {"enregistrer_seance"}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "consulter_profil",
            "description": (
                "Retourne le profil sportif et nutritionnel de l'utilisateur : "
                "objectif, niveau, poids, poids cible, calories cibles, restrictions "
                "alimentaires et matériel disponible."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consulter_progression",
            "description": (
                "Retourne les statistiques de progression depuis les séances "
                "enregistrées : nombre de séances, volume total soulevé, ressenti "
                "moyen, dernières séances et évolution des charges par exercice."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculer_macros",
            "description": (
                "Calcule la répartition en grammes de protéines, glucides et lipides "
                "à partir d'un apport calorique et d'un objectif (prise_masse, "
                "perte_poids, force, endurance). Toujours utiliser ce tool pour un "
                "calcul de macros : il ne faut pas les deviner."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "calories": {
                        "type": "number",
                        "description": "Apport calorique quotidien en kcal.",
                    },
                    "objectif": {
                        "type": "string",
                        "description": "Objectif du profil. Par défaut 'prise_masse'.",
                        "enum": ["prise_masse", "perte_poids", "force", "endurance"],
                    },
                },
                "required": ["calories"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "proposer_seance",
            "description": (
                "Analyse les dernières séances (progression des charges et ressenti "
                "moyen) pour proposer l'adaptation de la prochaine séance : augmenter, "
                "stabiliser ou récupérer."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enregistrer_seance",
            "description": (
                "Enregistre une séance réalisée en base (date, ressenti de 1 à 5, "
                "notes). Cette action MODIFIE la base : elle sera soumise à la "
                "validation de l'utilisateur avant exécution."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date au format AAAA-MM-JJ (défaut : aujourd'hui)."},
                    "ressenti": {"type": "integer", "description": "Ressenti de la séance, de 1 (très dur) à 5 (très facile)."},
                    "notes": {"type": "string", "description": "Notes libres sur la séance (facultatif)."},
                },
                "required": ["ressenti"],
            },
        },
    },
]


# ─────────────────────────────────────────────────────────────────────
#  Métadonnées d'affichage (UI) : icône, libellé court, catégorie
#  et catalogue exposé au frontend via GET /api/agent/outils
# ─────────────────────────────────────────────────────────────────────

TOOL_META = {
    "consulter_profil":       {"libelle": "Profil",              "icone": "👤", "categorie": "Lecture"},
    "consulter_progression":  {"libelle": "Progression",         "icone": "📈", "categorie": "Lecture"},
    "calculer_macros":        {"libelle": "Calcul des macros",   "icone": "🧮", "categorie": "Calcul"},
    "proposer_seance":        {"libelle": "Séance conseillée",   "icone": "🏋️", "categorie": "Lecture"},
    "enregistrer_seance":     {"libelle": "Enregistrer une séance", "icone": "✅", "categorie": "Écriture"},
}


def meta_tool(nom: str) -> dict:
    """Métadonnées d'affichage d'un tool (icône, libellé, catégorie, sensible)."""
    base = TOOL_META.get(nom, {"libelle": nom, "icone": "🔧", "categorie": "Autre"})
    return {**base, "sensible": nom in SENSITIVE_TOOLS}


TOOL_CATALOG = [
    {
        "nom": schema["function"]["name"],
        "description": schema["function"]["description"],
        **meta_tool(schema["function"]["name"]),
    }
    for schema in TOOL_SCHEMAS
]