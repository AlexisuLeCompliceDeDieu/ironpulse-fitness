"""Logique de génération de programmes d'entraînement.

Algorithme:
  - Selon l'objectif -> choix du split (ex: prise de masse = Push/Pull/Legs sur 3-4 jours)
  - Selon le niveau -> volume/intensité (séries x répétitions)
  - Filtre des exercices selon le matériel disponible
  - Génère un programme de 4 semaines avec progression
"""

from datetime import date, timedelta

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


def get_presets():
    """Retourne les séances prédéfinies disponibles (splits par objectif)."""
    presets = []
    for goal, spec in SPLITS.items():
        presets.append({
            "goal": goal,
            "label": GOAL_LABELS.get(goal, goal),
            "days_per_week": len(spec["days"]),
            "days": [d["name"] for d in spec["days"]],
        })
    return presets


def generate_program(user, available_equipment=None, goal=None):
    """Génère un programme mensuel pour un utilisateur.

    `goal` permet de choisir l'objectif au moment de la génération
    (sinon on reprend l'objectif enregistré dans le profil).
    """
    from models import (
        TrainingProgram, ProgramDay, ProgramExercise, Exercise, db,
    )

    available_equipment = available_equipment or []
    selected_goal = goal or user.goal

    split = SPLITS.get(selected_goal, SPLITS["prise_masse"])
    prescription = LEVEL_PRESCRIPTIONS.get(user.level, LEVEL_PRESCRIPTIONS["debutant"])

    program = TrainingProgram(
        user_id=user.id,
        goal=selected_goal,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=28),
        is_active=True,
    )
    db.session.add(program)
    db.session.flush()

    day_number = 1
    for day_spec in split["days"]:
        day = ProgramDay(program_id=program.id, day_number=day_number, name=day_spec["name"])
        db.session.add(day)
        db.session.flush()

        order = 1
        for category in day_spec["categories"]:
            count = day_spec.get("exercises_per_category", 1)
            exercises = select_exercises(category, count, available_equipment)
            for ex in exercises:
                db.session.add(ProgramExercise(
                    day_id=day.id,
                    exercise_id=ex.id,
                    sets=prescription["sets"],
                    reps=prescription["reps"],
                    rest_seconds=prescription["rest"],
                    target_weight=estimate_weight(user, ex, prescription),
                    order=order,
                ))
                order += 1

        day_number += 1

    db.session.commit()
    return program


def select_exercises(category, count, available_equipment):
    """Sélectionne `count` exercices de la catégorie, préférant les polyarticulaires."""
    from models import Exercise

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
