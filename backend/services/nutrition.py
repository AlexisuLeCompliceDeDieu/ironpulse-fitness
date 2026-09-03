"""Calculs nutritionnels : calories quotidiennes suggérées à partir du profil.

Formule de Mifflin-St Jeor pour le métabolisme de base (BMR), multipliée par
un coefficient lié au niveau sportif, puis ajustée selon l'objectif (surplus,
déficit ou maintien).
"""

# Coefficient d'activité selon le niveau sportif du profil
ACTIVITY_MULTIPLIER = {
    "debutant": 1.375,      # ~peu d'activité en dehors des séances
    "intermediaire": 1.55,  # ~3 à 5 séances / semaine
    "avance": 1.725,        # ~6 à 7 séances / semaine
}

# Facteur d'ajustement selon l'objectif
GOAL_FACTOR = {
    "prise_masse": 1.10,   # léger surplus calorique pour prendre du muscle
    "perte_poids": 0.85,   # déficit calorique modéré pour perdre du gras
    "force": 1.0,          # maintien (recomposition)
    "endurance": 1.05,     # léger apport supplémentaire pour le cardio
}


def compute_daily_calories(user):
    """Calories quotidiennes suggérées arrondies à la cinquantaine la plus proche.

    Le profil ne renseigne pas de sexe : on utilise la formule masculine par
    défaut (la plus courante dans ce contexte). Le résultat reste éditable
    manuellement par l'utilisateur dans son profil.
    """
    weight = user.weight or 70.0
    height = user.height or 175.0
    age = user.age or 25

    # Mifflin-St Jeor (homme) : 10×poids + 6.25×taille − 5×âge + 5
    bmr = 10.0 * weight + 6.25 * height - 5.0 * age + 5.0
    tdee = bmr * ACTIVITY_MULTIPLIER.get(user.level, 1.55)
    total = tdee * GOAL_FACTOR.get(user.goal, 1.0)

    # Arrondi à 50 kcal près et plancher de sécurité
    return max(1200, int(round(total / 50) * 50))


def current_calories(user):
    """Calories réellement utilisées pour le plan alimentaire.

    Si l'utilisateur suit le calcul automatique (champ laissé en auto), on
    utilise la valeur suggérée ; sinon on garde sa saisie manuelle.
    """
    if getattr(user, "calories_auto", True):
        return compute_daily_calories(user)
    return user.daily_calories or compute_daily_calories(user)