"""Logique d'adaptation intelligente des séances."""

from models import Exercise


def find_alternative(exercise_id):
    """Trouve un exercice alternatif du même groupe musculaire."""
    exercise = Exercise.query.get(exercise_id)
    if not exercise:
        return None
    return exercise


def get_alternative_for(exercise, available_equipment):
    """Retourne un exercice utilisable avec le matériel disponible."""
    from models import Exercise as Ex

    candidates = Ex.query.filter_by(muscle_group=exercise.muscle_group).all()
    for candidate in candidates:
        if candidate.id != exercise.id and candidate.equipment_needed in available_equipment:
            return candidate
    # Fallback: n'importe quel exercice du même groupe
    for candidate in candidates:
        if candidate.id != exercise.id:
            return candidate
    return None


def adjust_intensity(user, feeling, previous_feeling_avg=None):
    """Adapte l'intensité recommandée selon le ressenti de l'utilisateur."""
    adjustment = 1.0
    if feeling is not None:
        if feeling <= 2:
            adjustment = 0.85   # séance difficile -> réduire l'intensité
        elif feeling >= 4:
            adjustment = 1.05   # séance facile -> augmenter légèrement
    else:
        if previous_feeling_avg is not None and previous_feeling_avg <= 2.5:
            adjustment = 0.9
    return round(adjustment, 2)
