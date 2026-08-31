"""Génération de conseils personnalisés (logique locale / prompt engineering).

Produit des recommandations actionnables à partir du profil et des
statistiques de progression de l'utilisateur.
"""

GOAL_LABELS = {
    "prise_masse": "prise de masse",
    "perte_poids": "perte de poids",
    "force": "développement de la force",
    "endurance": "amélioration de l'endurance",
}

LEVEL_LABELS = {
    "debutant": "débutant",
    "intermediaire": "intermédiaire",
    "avance": "avancé",
}


def generate_advice(user, stats=None, weight_entries=None):
    """Retourne une liste de conseils (dict {type, text}) personnalisés."""
    advice = []

    # 1. Conseil global selon l'objectif et le niveau
    goal_label = GOAL_LABELS.get(user.goal, user.goal)
    level_label = LEVEL_LABELS.get(user.level, user.level)
    advice.append({
        "type": "info",
        "text": (
            f"Votre objectif actuel est la {goal_label} avec un profil {level_label}. "
            f"Continuez à respecter votre programme pour progresser régulièrement."
        ),
    })

    # 2. Conseil basé sur le ressenti moyen
    if stats and stats.get("total_sessions", 0) > 0:
        avg_feeling = stats.get("avg_feeling", 3)
        if avg_feeling <= 2:
            advice.append({
                "type": "warning",
                "text": (
                    f"Votre ressenti moyen est de {avg_feeling}/5 : vos dernières séances "
                    f"semblent très intenses. Pensez à augmenter les temps de repos ou à "
                    f"réduire légèrement les charges pour récupérer."
                ),
            })
        elif avg_feeling >= 4.5:
            advice.append({
                "type": "success",
                "text": (
                    f"Ressenti moyen excellent ({avg_feeling}/5). C'est le bon moment pour "
                    f"augmenter légèrement vos charges ou vos répétitions et continuer à progresser."
                ),
            })
        else:
            advice.append({
                "type": "info",
                "text": "Votre intensité est bien calibrée. Gardez le rythme et restez régulier.",
            })

    # 3. Conseil sur la régularité des séances
    if stats:
        sessions = stats.get("total_sessions", 0)
        if sessions == 0:
            advice.append({
                "type": "warning",
                "text": "Vous n'avez encore enregistré aucune séance. Lancez votre programme et suivez vos performances !",
            })
        elif sessions < 3:
            advice.append({
                "type": "info",
                "text": (
                    f"Vous avez réalisé {sessions} séance(s). Essayez d'atteindre au moins 3 séances "
                    f"par semaine pour des résultats visibles."
                ),
            })

    # 4. Conseil nutritionnel selon l'écart au poids cible
    if user.target_weight and user.weight:
        diff = user.weight - user.target_weight
        if abs(diff) >= 1:
            if diff > 0:
                advice.append({
                    "type": "info",
                    "text": (
                        f"Vous êtes à {abs(round(diff,1))} kg au-dessus de votre poids cible "
                        f"({user.target_weight} kg). Privilégiez un léger déficit calorique et "
                        f"une répartition riche en protéines pour préserver la masse musculaire."
                    ),
                })
            else:
                advice.append({
                    "type": "success",
                    "text": (
                        f"Vous êtes à {abs(round(diff,1))} kg en dessous de votre poids cible "
                        f"({user.target_weight} kg). Augmentez légèrement votre apport calorique, "
                        f"en particulier en protéines et glucides complexes."
                    ),
                })

    # 5. Conseil selon objectif / macros
    if user.daily_calories:
        protein_reco = round(user.daily_calories * 0.30 / 4)
        advice.append({
            "type": "info",
            "text": (
                f"Avec un objectif de {user.daily_calories} kcal/jour, visez environ "
                f"{protein_reco} g de protéines par jour pour soutenir la progression."
            ),
        })

    return advice
