"""Agent IA pour la génération de plans alimentaires via Groq (LLaMA 3.1).

Fonctionnement :
  1. Construit un prompt avec le profil utilisateur + base d'aliments
  2. Appelle Groq (LLaMA 3.1 8B instant)
  3. Parse la réponse JSON structurée
  4. Sauvegarde en base (MealPlan, Meal, MealItem)
  5. Fallback vers le générateur classique si échec

Sécurité :
  - Jamais de données personnelles envoyées (seulement préférences nutritionnelles)
  - Quota tracker vérifie les limites avant chaque appel
  - Fallback automatique si indisponible
"""

import json
import logging
from services.groq_config import get_client, GROQ_MODEL, GROQ_ENABLED
from services import quota_tracker, meal_generator

logger = logging.getLogger(__name__)

# ── Prompt système ──────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un nutritionniste sportif expert. Tu génères des plans alimentaires personnalisés pour des athlètes.

RÈGLES STRICTES :
1. Utilise UNIQUEMENT les aliments fournis dans la liste "aliments_disponibles"
2. Chaque repas doit contenir exactement 3-5 aliments
3. Les quantités sont en GRAMMES (entiers ou .5)
4. Répartition calorique : Petit-déjeuner ~25%, Déjeuner ~35%, Collation ~15%, Dîner ~25%
5. Respecte les calories cibles (±100 kcal par jour)
6. Varie les recettes au fil des jours (jamais 2× le même repas consécutivement)
7. Respecte STRICTEMENT les restrictions alimentaires
8. Format de sortie : JSON valide uniquement, pas de texte avant/après

FORMAT DE SORTIE (JSON) :
{
  "meals": [
    {
      "day": 1,
      "meal_type": "Petit-déjeuner",
      "name": "Nom du repas",
      "items": [
        {"food": "Nom exact de l'aliment", "quantity": 160}
      ]
    }
  ]
}

meal_type doit être UNIQUEMENT : "Petit-déjeuner", "Déjeuner", "Collation", "Dîner"
"""


def _build_user_context(user, foods_by_name):
    """Construit le contexte utilisateur pour le prompt."""
    preferences = user.preferences_list() if hasattr(user, "preferences_list") else []

    restrictions_map = {
        "vegetarien": "PAS de viande ni poisson",
        "vegan": "PAS de viande, poisson, œufs, ni produits laitiers",
        "sans_lactose": "PAS de produits laitiers",
        "sans_gluten": "PAS de gluten (pain, pâtes, avoine…)",
        "sans_noix": "PAS de noix ni fruits à coque",
    }
    restrictions = []
    for pref in preferences:
        if pref in restrictions_map:
            restrictions.append(restrictions_map[pref])

    foods_list = []
    for name, food in foods_by_name.items():
        tags = food.tags_list()
        foods_list.append({
            "name": name,
            "kcal": food.kcal,
            "protein": food.protein,
            "carbs": food.carbs,
            "fat": food.fat,
            "category": food.category,
            "tags": tags,
        })

    return {
        "calories": user.daily_calories or 2500,
        "goal": user.goal or "prise_masse",
        "weight": user.weight or 70,
        "restrictions": restrictions,
        "foods": foods_list,
    }


def _build_prompt(context, num_days, recent_meals=None):
    """Construit le prompt utilisateur complet."""
    goal_labels = {
        "prise_masse": "prise de masse (muscle)",
        "perte_poids": "perte de poids (sèche)",
        "force": "force (powerlifting)",
        "endurance": "endurance (cardio)",
    }
    goal_label = goal_labels.get(context["goal"], context["goal"])

    restrictions_text = "Aucune"
    if context["restrictions"]:
        restrictions_text = " / ".join(context["restrictions"])

    recent_text = ""
    if recent_meals:
        recent_text = "\n\nREpas RÉCENTS (évite de répéter) :\n" + "\n".join(
            f"  Jour {m['day']} - {m['meal_type']}: {m['name']}"
            for m in recent_meals[-16:]
        )

    foods_text = json.dumps(context["foods"], ensure_ascii=False, indent=None)

    return f"""Génère un plan alimentaire pour {num_days} jour(s).

CONTEXTE UTILISATEUR :
- Objectif : {goal_label}
- Poids : {context['weight']} kg
- Calories cibles : {context['calories']} kcal/jour
- Restrictions : {restrictions_text}

ALIMENTS DISPONIBLES (avec valeurs nutritionnelles pour 100g) :
{foods_text}{recent_text}

Pour chaque jour, génère 4 repas : Petit-déjeuner, Déjeuner, Collation, Dîner.
Respecte les calories cibles et les restrictions.
Variété : ne répète JAMAIS le même nom de repas 2 jours d'affilée pour un même type de repas."""


def generate_ai_meal_plan(user, num_days, foods_by_name, recent_meals=None):
    """Génère un plan alimentaire via l'agent IA Groq.

    Retourne (plan_db, info) où plan_db est un MealPlan en base
    et info contient des métadonnées (mode, quota, etc.).

    En cas d'échec, fallback automatique vers le générateur classique.
    """
    from models import MealPlan, Meal, MealItem, db
    from services.nutrition import current_calories

    # Vérification quota AVANT l'appel
    allowed, quota_info = quota_tracker.check_quota()
    if not allowed:
        logger.warning(f"Quota Groq dépassé ({quota_info.get('reason')}) — fallback classique")
        plan = meal_generator.generate_meal_plan(user, num_days, foods_by_name)
        return plan, {"mode": "classic", "reason": "quota_exceeded", "quota": quota_info}

    # Vérification disponibilité Groq
    client = get_client()
    if client is None:
        logger.info("Groq non configuré — fallback classique")
        plan = meal_generator.generate_meal_plan(user, num_days, foods_by_name)
        return plan, {"mode": "classic", "reason": "groq_unavailable"}

    # Construction du prompt
    context = _build_user_context(user, foods_by_name)
    prompt = _build_prompt(context, num_days, recent_meals)

    # Appel IA
    try:
        logger.info(f"Appel Groq : {GROQ_MODEL}, {num_days} jour(s), {len(foods_by_name)} aliments")
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=4096,
        )

        # Enregistrement de l'usage (APRÈS l'appel réussi)
        quota_tracker.record_usage()

        content = response.choices[0].message.content
        logger.info(f"Réponse Groq reçue ({len(content)} chars)")

    except Exception as e:
        logger.error(f"Erreur Groq: {e} — fallback classique")
        plan = meal_generator.generate_meal_plan(user, num_days, foods_by_name)
        return plan, {"mode": "classic", "reason": f"groq_error: {str(e)[:200]}"}

    # Parse de la réponse (robuste : gère ```json ... ```)
    try:
        raw = content.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines).strip()
        data = json.loads(raw)
        meals_data = data.get("meals", [])
        if not meals_data:
            raise ValueError("Réponse IA vide (pas de meals)")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Parse réponse IA échoué: {e} — fallback classique")
        plan = meal_generator.generate_meal_plan(user, num_days, foods_by_name)
        return plan, {"mode": "classic", "reason": f"parse_error: {str(e)[:200]}"}

    # Sauvegarde en base
    try:
        target_calories = current_calories(user)
        plan = MealPlan(
            user_id=user.id,
            num_days=num_days,
            target_calories=target_calories,
        )
        db.session.add(plan)
        db.session.flush()

        valid_meals = 0
        skipped = 0

        for meal_data in meals_data:
            day = int(meal_data.get("day", 1))
            if day < 1 or day > num_days:
                skipped += 1
                continue

            meal_type = meal_data.get("meal_type", "")
            if meal_type not in ("Petit-déjeuner", "Déjeuner", "Collation", "Dîner"):
                skipped += 1
                continue

            meal_name = str(meal_data.get("name", "Repas"))[:150]

            meal = Meal(
                meal_plan_id=plan.id,
                day=day,
                meal_type=meal_type,
                name=meal_name,
            )
            db.session.add(meal)
            db.session.flush()

            for item_data in meal_data.get("items", []):
                food_name = item_data.get("food", "")
                food = foods_by_name.get(food_name)
                if food is None:
                    # Recherche floue
                    for fn, fobj in foods_by_name.items():
                        if fn.lower() == food_name.lower():
                            food = fobj
                            break
                if food is None:
                    skipped += 1
                    continue

                qty = float(item_data.get("quantity", 100))
                qty = max(10, min(qty, 2000))  # bornes raisonnables
                db.session.add(MealItem(meal_id=meal.id, food_id=food.id, quantity=qty))
                valid_meals += 1

        db.session.commit()
        logger.info(f"Plan IA sauvegardé: {valid_meals} items, {skipped} skippés")

        info = {
            "mode": "ai",
            "model": GROQ_MODEL,
            "meals_generated": valid_meals,
            "skipped": skipped,
            "quota": quota_info,
        }
        return plan, info

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur sauvegarde plan IA: {e} — fallback classique")
        plan = meal_generator.generate_meal_plan(user, num_days, foods_by_name)
        return plan, {"mode": "classic", "reason": f"db_error: {str(e)[:200]}"}
