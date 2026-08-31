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


def generate_adaptation(sessions):
    """Adaptation dynamique : analyse l'évolution des charges par exercice
    et le ressenti moyen pour recommander l'intensité de la prochaine séance.

    Retourne une liste de recommandations (dict {type, text}).
    """
    recommendations = []
    if not sessions:
        return recommendations

    from collections import defaultdict
    by_exercise = defaultdict(list)
    for s in sorted(sessions, key=lambda x: x.date):
        per_exercise = {}
        for set_obj in s.sets:
            name = set_obj.exercise.name if set_obj.exercise else "Exercice"
            w = set_obj.weight or 0
            if name not in per_exercise or w > per_exercise[name]:
                per_exercise[name] = w
        for name, w in per_exercise.items():
            by_exercise[name].append((s.date, w))

    progressing = []
    stalled = []
    for name, series in by_exercise.items():
        if len(series) >= 2:
            first_w = series[0][1]
            last_w = series[-1][1]
            if last_w > first_w:
                progressing.append(name)
            elif last_w == first_w and last_w > 0:
                stalled.append(name)

    avg_feeling = sum(s.feeling for s in sessions) / len(sessions)

    if avg_feeling <= 2:
        recommendations.append({
            "type": "warning",
            "text": (
                f"Ressenti moyen {avg_feeling:.1f}/5 : vos derniers efforts sont très "
                f"éprouvants. Prévoyez une séance de récupération active ou réduisez le "
                f"volume d'environ 20% lors de la prochaine séance pour éviter le surentraînement."
            ),
        })
    elif avg_feeling >= 4.5 and progressing:
        names = ", ".join(progressing[:3])
        recommendations.append({
            "type": "success",
            "text": (
                f"Bonne dynamique, vos charges progressent sur : {names}. Vous pouvez "
                f"augmenter la charge de 2,5 à 5 % sur ces exercices pour continuer la surcharge progressive."
            ),
        })
    elif stalled:
        names = ", ".join(stalled[:3])
        recommendations.append({
            "type": "info",
            "text": (
                f"Charges stables sur : {names}. Variez les répétitions, l'ordre des exercices "
                f"ou ajoutez une série pour relancer la progression musculaire."
            ),
        })
    else:
        recommendations.append({
            "type": "info",
            "text": (
                "L'intensité globale semble équilibrée. Visez une progression légère et "
                "régulière (poids, répétitions ou volume) à chaque séance."
            ),
        })

    return recommendations
