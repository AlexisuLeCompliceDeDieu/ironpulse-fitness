"""Logique de génération de programmes d'entraînement.

Algorithme:
  - Selon l'objectif -> choix du split (ex: prise de masse = Push/Pull/Legs sur 3-4 jours)
  - Selon le niveau -> volume/intensité (séries x répétitions)
  - Filtre des exercices selon le matériel disponible
  - Génère un programme de 4 semaines avec progression
"""

from datetime import date, timedelta
import random

SPLITS = {
    "prise_masse": {
        "days": [
            {"name": "Push", "categories": ["pectoraux", "epaule", "triceps"],
             "exercises_per_category": 2},
            {"name": "Pull", "categories": ["dos", "biceps"],
             "exercises_per_category": 2},
            {"name": "Jambes", "categories": ["quadriceps", "ischio", "fessiers"],
             "exercises_per_category": 2},
            {"name": "Push + Pull", "categories": ["pectoraux", "dos", "epaule", "biceps"],
             "exercises_per_category": 1},
        ]
    },
    "perte_poids": {
        "days": [
            {"name": "Full Body 1", "categories": ["quadriceps", "pectoraux", "dos", "core"],
             "exercises_per_category": 1},
            {"name": "Full Body 2", "categories": ["ischio", "epaule", "dos", "core"],
             "exercises_per_category": 1},
            {"name": "Cardio + Core", "categories": ["core", "cardio"],
             "exercises_per_category": 1},
        ]
    },
    "force": {
        "days": [
            {"name": "Force A", "categories": ["quadriceps", "pectoraux", "dos"],
             "exercises_per_category": 1},
            {"name": "Force B", "categories": ["ischio", "epaule"],
             "exercises_per_category": 2},
        ]
    },
    "endurance": {
        "days": [
            {"name": "Endurance 1", "categories": ["quadriceps", "pectoraux", "core"],
             "exercises_per_category": 1},
            {"name": "Endurance 2", "categories": ["ischio", "dos", "core"],
             "exercises_per_category": 1},
            {"name": "Endurance 3", "categories": ["cardio", "core"],
             "exercises_per_category": 1},
        ]
    },
}

LEVEL_PRESCRIPTIONS = {
    "debutant": {"sets": 3, "reps": 12, "rest": 90},
    "intermediaire": {"sets": 4, "reps": 10, "rest": 75},
    "avance": {"sets": 5, "reps": 8, "rest": 60},
}


GOAL_LABELS = {
    "prise_masse": "Prise de masse",
    "perte_poids": "Perte de poids",
    "force": "Développement de la force",
    "endurance": "Amélioration de l'endurance",
}


# Splits nommés (types de séances) — chaque template décrit un "jour type"
# avec les groupes musculaires à travailler. L'utilisateur choisit un split
# et un nombre de séances/semaine ; on répartit les jours en conséquence.
SPLIT_TEMPLATES = {
    "full_body": {
        "label": "Full Body",
        "icon": "🧘",
        "max_days": 3,
        "days": [
            {"name": "Full Body A", "categories": ["quadriceps", "pectoraux", "dos", "core"], "exercises_per_category": 1},
            {"name": "Full Body B", "categories": ["ischio", "fessiers", "epaule", "biceps", "triceps", "core"], "exercises_per_category": 1},
        ],
    },
    "upper_lower": {
        "label": "Upper / Lower",
        "icon": "🍗",
        "max_days": 4,
        "days": [
            {"name": "Upper", "categories": ["pectoraux", "dos", "epaule", "biceps", "triceps"], "exercises_per_category": 1},
            {"name": "Lower", "categories": ["quadriceps", "ischio", "fessiers", "core"], "exercises_per_category": 1},
        ],
    },
    "push_pull_legs": {
        "label": "Push / Pull / Legs",
        "icon": "🏋️",
        "max_days": 6,
        "days": [
            {"name": "Push", "categories": ["pectoraux", "epaule", "triceps"], "exercises_per_category": 2},
            {"name": "Pull", "categories": ["dos", "biceps"], "exercises_per_category": 2},
            {"name": "Jambes", "categories": ["quadriceps", "ischio", "fessiers"], "exercises_per_category": 2},
        ],
    },
    "upper_lower_push_pull": {
        "label": "U/L + Push/Pull (4 j)",
        "icon": "⚡",
        "max_days": 4,
        "days": [
            {"name": "Upper A", "categories": ["pectoraux", "dos", "epaule", "triceps"], "exercises_per_category": 1},
            {"name": "Lower A", "categories": ["quadriceps", "ischio", "fessiers"], "exercises_per_category": 2},
            {"name": "Upper B", "categories": ["dos", "epaule", "biceps"], "exercises_per_category": 1},
            {"name": "Lower B", "categories": ["quadriceps", "ischio", "fessiers", "core"], "exercises_per_category": 1},
        ],
    },
    "bro_split": {
        "label": "Split par muscle (5 j)",
        "icon": "💪",
        "max_days": 5,
        "days": [
            {"name": "Pectoraux", "categories": ["pectoraux"], "exercises_per_category": 3},
            {"name": "Dos", "categories": ["dos"], "exercises_per_category": 3},
            {"name": "Jambes", "categories": ["quadriceps", "ischio", "fessiers"], "exercises_per_category": 2},
            {"name": "Épaules", "categories": ["epaule"], "exercises_per_category": 3},
            {"name": "Bras", "categories": ["biceps", "triceps"], "exercises_per_category": 2},
        ],
    },
}

SPLIT_LABELS = {
    "prise_masse": "Prise de masse (Push/Pull/Legs)",
    "perte_poids": "Perte de poids (Full Body)",
    "force": "Force (Full Body)",
    "endurance": "Endurance (Full Body)",
}


def default_split_for(goal):
    """Split automatique selon l'objectif (comportement historique)."""
    return {
        "goal": goal,
        "split_type": goal,
        "label": SPLIT_LABELS.get(goal, goal),
        "days": SPLITS.get(goal, SPLITS["prise_masse"])["days"],
    }


def get_presets():
    """Retourne les options de programme : splits nommés + splits par objectif."""
    presets = []
    for split_type, spec in SPLIT_TEMPLATES.items():
        presets.append({
            "kind": "split",
            "split_type": split_type,
            "label": spec["label"],
            "icon": spec.get("icon", "🏋️"),
            "max_days": spec["max_days"],
            "days": [d["name"] for d in spec["days"]],
            "days_per_week": len(spec["days"]),
        })
    for goal, spec in SPLITS.items():
        presets.append({
            "kind": "goal",
            "goal": goal,
            "split_type": goal,
            "label": GOAL_LABELS.get(goal, goal),
            "icon": "🎯",
            "days_per_week": len(spec["days"]),
            "days": [d["name"] for d in spec["days"]],
        })
    return presets


def build_days(templates, days_count):
    """Répartit les jours du split sur `days_count` séances hebdomadaires.

    Si le nombre demandé correspond au nombre de templates, on les prend tels quels.
    Sinon on parcourt/cycle les templates jusqu'à atteindre le nombre demandé,
    en suffixant les jours répétés (ex: "Push 2").
    """
    templates = list(templates)
    if days_count <= 0:
        days_count = len(templates)
    days = []
    for i in range(days_count):
        template = templates[i % len(templates)]
        occurrences = sum(1 for d in days if d["name"] == template["name"])
        name = template["name"]
        if occurrences > 0:
            name = f"{template['name']} {occurrences + 1}"
        days.append({**template, "name": name})
    return days


def generate_program(user, available_equipment=None, goal=None, split_type=None, days_per_week=None):
    """Génère un programme mensuel pour un utilisateur.

    - `goal` : objectif (sinon celui du profil).
    - `split_type` : split nommé (full_body, upper_lower, push_pull_legs...)
      ou None pour utiliser celui du profil ou l'objectif par défaut.
    - `days_per_week` : nombre de séances/semaine (sinon sessions_per_week du profil,
      ou le nombre de jours du split).
    """
    from models import (
        TrainingProgram, ProgramDay, ProgramExercise, Exercise, db,
    )

    available_equipment = available_equipment or []
    selected_goal = goal or user.goal

    # Déterminer le split
    selected_split = split_type or user.split_type
    if selected_split and selected_split in SPLIT_TEMPLATES:
        templates = SPLIT_TEMPLATES[selected_split]["days"]
    else:
        # Fallback : split par objectif
        templates = SPLITS.get(selected_goal, SPLITS["prise_masse"])["days"]
        selected_split = selected_goal

    # Déterminer le nombre de séances / semaine
    target_days = days_per_week or user.sessions_per_week
    if not target_days:
        target_days = len(templates)
    if selected_split in SPLIT_TEMPLATES:
        target_days = min(target_days, SPLIT_TEMPLATES[selected_split]["max_days"])

    prescription = LEVEL_PRESCRIPTIONS.get(user.level, LEVEL_PRESCRIPTIONS["debutant"])

    # Désactiver les anciens programmes actifs
    TrainingProgram.query.filter_by(user_id=user.id, is_active=True).update({TrainingProgram.is_active: False})
    db.session.flush()

    program = TrainingProgram(
        user_id=user.id,
        goal=selected_goal,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=28),
        is_active=True,
    )
    db.session.add(program)
    db.session.flush()

    day_specs = build_days(templates, target_days)
    # Générateur aléatoire propre au programme : chaque régénération varie
    rng = random.Random()
    day_number = 1
    for day_spec in day_specs:
        day = ProgramDay(program_id=program.id, day_number=day_number, name=day_spec["name"])
        db.session.add(day)
        db.session.flush()

        order = 1
        for category in day_spec["categories"]:
            count = day_spec.get("exercises_per_category", 1)
            exercises = select_exercises(category, count, available_equipment, rng=rng)
            for ex in exercises:
                # Repos : plus long sur les gros exercices (polyarticulaires), plus court
                # sur les petits (isolations).
                rest_seconds = 150 if ex.is_compound else 90
                db.session.add(ProgramExercise(
                    day_id=day.id,
                    exercise_id=ex.id,
                    sets=prescription["sets"],
                    reps=prescription["reps"],
                    rest_seconds=rest_seconds,
                    target_weight=estimate_weight(user, ex, prescription),
                    order=order,
                ))
                order += 1

        day_number += 1

    db.session.commit()
    return program


def select_exercises(category, count, available_equipment, rng=None):
    """Sélectionne `count` exercices de la catégorie, préférant les polyarticulaires.

    `rng` (random.Random) permet de varier la sélection d'un programme à l'autre :
    les exercices polyarticulaires sont prioritaires mais leur ordre est mélangé.
    """
    from models import Exercise

    rng = rng or random

    query = Exercise.query.filter_by(category=category)
    all_ex = query.all()

    def in_equipment(ex):
        if not available_equipment:
            return True
        # Les exercices au poids du corps sont toujours possibles
        if ex.equipment_needed == "aucun":
            return True
        return ex.equipment_needed in available_equipment

    matching = [ex for ex in all_ex if in_equipment(ex)]
    # Si aucun exercice de la catégorie ne correspond au matériel restreint,
    # on retombe sur tous ceux de la catégorie (le programme reste générable)
    if not matching:
        matching = all_ex.copy()

    compound = sorted([e for e in matching if e.is_compound], key=lambda e: e.id)
    isolation = sorted([e for e in matching if not e.is_compound], key=lambda e: e.id)

    # Mélange pour varier, tout en gardant la priorité aux polyarticulaires
    rng.shuffle(compound)
    rng.shuffle(isolation)

    selected = []
    for e in (compound + isolation):
        if len(selected) >= count:
            break
        if e not in selected:
            selected.append(e)
    return selected


def estimate_weight(user, exercise, prescription):
    """Estime le poids cible de départ selon le niveau de l'utilisateur."""
    # Ratio simplifié sur le poids de corps
    body_weight = user.weight or 70.0
    factor_map = {"debutant": 0.5, "intermediaire": 0.7, "avance": 0.85}
    target = body_weight * factor_map.get(user.level, 0.5) * (1.0 if exercise.is_compound else 0.6)
    return round(target, 1)
