"""Agent IA pour la génération de plans alimentaires via un routeur multi-IA.

Fonctionnement :
  1. Construit un prompt avec le profil utilisateur + base d'aliments
  2. Appelle le premier fournisseur disponible (Groq, Gemini, Mistral,
     OpenRouter) via `ai_providers` — failover automatique si limite atteinte
  3. Parse la réponse JSON structurée
  4. Sauvegarde en base (MealPlan, Meal, MealItem)
  5. Fallback vers le générateur classique si tout échoue

Sécurité :
  - Jamais de données personnelles envoyées (seulement préférences nutritionnelles)
  - Quota tracker vérifie les limites par fournisseur avant chaque appel
  - Fallback automatique si indisponible
"""

import json
import logging
from services import meal_generator
from services import ai_providers

logger = logging.getLogger(__name__)


def _max_tokens_for(num_days):
    """Plafond de tokens de sortie adapté au nombre de jours (par morceau).

    Les tiers gratuits limitent les tokens de sortie par minute : des sorties
    courtes (2 jours / appel) restent largement sous ces limites.
    """
    return max(700, min(3000, int(num_days) * 380))

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
    from services.nutrition import current_calories

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
        "calories": current_calories(user),
        "goal": user.goal or "prise_masse",
        "weight": user.weight or 70,
        "restrictions": restrictions,
        "foods": foods_list,
    }


def _build_prompt(context, num_days, recent_meals=None, day_offset=0):
    """Construit le prompt pour un morceau de `num_days` jours du plan.

    `day_offset` : nombre de jours déjà générés avant ce morceau (le champ
    `day` de l'IA est relatif au morceau : 1 = jour suivant le offset).
    """
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
    abs_first = day_offset + 1
    abs_last = day_offset + num_days

    return f"""Génère un plan alimentaire pour {num_days} jour(s) : les JOURS {abs_first} à {abs_last} du plan global.

CONTEXTE UTILISATEUR :
- Objectif : {goal_label}
- Poids : {context['weight']} kg
- Calories cibles : {context['calories']} kcal/jour
- Restrictions : {restrictions_text}

ALIMENTS DISPONIBLES (avec valeurs nutritionnelles pour 100g) :
{foods_text}{recent_text}

IMPORTANT : Le champ "day" de chaque repas est relatif à CE morceau :
day 1 = jour {abs_first}, day 2 = jour {abs_first + 1}, etc. (donc de 1 à {num_days}).

Pour chaque jour, génère 4 repas : Petit-déjeuner, Déjeuner, Collation, Dîner.
Respecte les calories cibles et les restrictions.
Variété : ne répète JAMAIS le même nom de repas 2 jours d'affilée pour un même type de repas."""


# ── Normalisation des réponses IA ───────────────────────────────────

_DAY_NAMES = {
    "lundi": 1, "mardi": 2, "mercredi": 3, "jeudi": 4,
    "vendredi": 5, "samedi": 6, "dimanche": 7,
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
}
_MEAL_TYPE_MAP = {
    "breakfast": "Petit-déjeuner", "petit-déjeuner": "Petit-déjeuner", "petit dejeuner": "Petit-déjeuner",
    "lunch": "Déjeuner", "dejeuner": "Déjeuner", "déjeuner": "Déjeuner",
    "snack": "Collation", "collation": "Collation",
    "dinner": "Dîner", "diner": "Dîner", "dîner": "Dîner",
}
_MEAL_TYPES_VALID = ("Petit-déjeuner", "Déjeuner", "Collation", "Dîner")


def _parse_content(content):
    """Parse la réponse IA en liste de dicts repas (robuste aux artefacts).

    Le modèle sort parfois UN objet JSON par jour au lieu d'un seul, ou ajoute
    du texte autour : on tente d'abord un `json.loads` du cadre {…}, puis on
    collecte tous les objets JSON présents et on fusionne leurs `meals`.
    """
    import re as _re
    raw = content.strip()
    # Supprimer les balises  thinking de Qwen
    if " thinking" in raw:
        raw = _re.sub(r" thinking.*? response", "", raw, flags=_re.DOTALL).strip()
    # Supprimer les blocs markdown
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()
    # Réparation légère : virgules parasites avant ] ou }
    raw = _re.sub(r",\s*([\]}])", r"\1", raw)

    # 1) Tentative rapide : on espère que le cadre {…} est un JSON unique.
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start:end + 1]
        try:
            data = json.loads(candidate)
            meals = data.get("meals", [])
            if isinstance(meals, list) and meals:
                return meals
        except Exception:
            pass

    # 2) Mode robuste : on collecte tous les objets JSON du texte (le modèle
    #    sort parfois un objet par jour) et on fusionne leurs champs "meals".
    meals = []
    decoder = json.JSONDecoder()
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch in "{[":
            try:
                obj, end_i = decoder.raw_decode(raw, i)
                if isinstance(obj, dict):
                    m = obj.get("meals")
                    if isinstance(m, list):
                        meals.extend(m)
                i = end_i
            except json.JSONDecodeError:
                i += 1  # avance d'un caractère et continue
        else:
            i += 1
    if meals:
        return meals
    raise ValueError("Réponse IA sans meals valides")


def _normalize_day(raw_day, chunk_days):
    """Convertit le champ day (relatif au morceau) en entier 1..chunk_days."""
    if isinstance(raw_day, str):
        day = _DAY_NAMES.get(raw_day.lower().strip())
        if day is None:
            import re
            nums = re.findall(r"\d+", raw_day)
            day = int(nums[0]) if nums else None
    else:
        try:
            day = int(raw_day)
        except (TypeError, ValueError):
            day = None
    if day is None or day < 1 or day > chunk_days:
        return None
    return day


def _normalize_meal_type(raw):
    mt = _MEAL_TYPE_MAP.get(str(raw).lower().strip(), str(raw).strip())
    return mt if mt in _MEAL_TYPES_VALID else None


def _get_ai_content(prompt, chunk_days, strict=False):
    """Appelle le routeur multi-IA pour un morceau. Retourne (content, provider_info).

    Le routeur fait lui-même le failover : limites par minute (cooldown), par
    jour (désactivé jusqu'à minuit), clé invalide, erreur serveur… En mode
    `strict`, on ajoute une consigne de JSON strict (après un premier essai).
    """
    user_content = prompt
    if strict:
        user_content += (
            "\n\nRappel STRICT : renvoie UNIQUEMENT un objet JSON valide."
            " Toutes les clés entre guillemets doubles, pas de texte avant ou après le JSON."
        )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    max_tokens = _max_tokens_for(chunk_days)
    logger.info(f"Appel IA (morceau {chunk_days}j{' strict' if strict else ''}) : max_tokens={max_tokens}")
    content, info = ai_providers.generate_text(messages, max_tokens=max_tokens, temperature=0.7)
    if content is None:
        reason = info.get("reason", "none_available")
        return None, {"reason": reason}
    return content, info


def _classic_fallback(user, num_days, foods_by_name, reason, quota_info=None):
    plan = meal_generator.generate_meal_plan(user, num_days, foods_by_name)
    info = {"mode": "classic", "reason": reason}
    if quota_info:
        info["quota"] = quota_info
    return plan, info


def generate_ai_meal_plan(user, num_days, foods_by_name, recent_meals=None):
    """Génère un plan alimentaire via le routeur multi-IA (failover).

    Génération PAR MORCEAUX (2 jours / appel) pour rester largement sous les
    limites de tokens de sortie par minute des tiers gratuits. Si aucun
    fournisseur n'est disponible, fallback automatique vers le classique.

    Retourne (plan_db, info).
    """
    from models import MealPlan, Meal, MealItem, db
    from services.nutrition import current_calories

    # Plafond réaliste : 1 appel / 2 jours, on limite à 30 jours en IA
    if num_days > 30:
        logger.info("Plan > 30 jours : génération IA non pertinente, classique utilisé")
        return _classic_fallback(user, num_days, foods_by_name, "too_many_days")

    context = _build_user_context(user, foods_by_name)

    # ── Génération par morceaux ─────────────────────────────────────
    normalized = []  # [ {day, meal_type, name, items:[(food_id, qty)]} ]
    skipped = 0
    CHUNK_DAYS = 2
    last_provider = None

    for offset in range(0, num_days, CHUNK_DAYS):
        nb = min(CHUNK_DAYS, num_days - offset)
        prompt = _build_prompt(context, nb, recent_meals, day_offset=offset)

        content, info = _get_ai_content(prompt, nb)
        if content is None:
            reason = info.get("reason", "none_available")
            return _classic_fallback(user, num_days, foods_by_name, f"provider_error: {reason[:200]}")
        last_provider = info

        try:
            chunk_meals = _parse_content(content)
        except Exception as e:
            # Re-jeu "strict" une fois avant d'abandonner le plan
            logger.warning(f"Parse invalide (morceau {offset + 1}-{offset + nb}), re-jeu strict: {e}")
            content2, info2 = _get_ai_content(prompt, nb, strict=True)
            if content2 is None:
                reason = info2.get("reason", "none_available")
                return _classic_fallback(user, num_days, foods_by_name, f"provider_error: {reason[:200]}")
            last_provider = info2
            try:
                chunk_meals = _parse_content(content2)
            except Exception as e2:
                logger.error(f"Parse invalide même en strict: {e2}")
                return _classic_fallback(user, num_days, foods_by_name, f"parse_error: {str(e2)[:200]}")
        # Le morceau a été généré : on le retient et on passe au suivant

        for meal_data in chunk_meals:
            rel_day = _normalize_day(meal_data.get("day", 1), nb)
            if rel_day is None:
                skipped += 1
                continue
            meal_type = _normalize_meal_type(meal_data.get("meal_type", ""))
            if meal_type is None:
                skipped += 1
                continue

            items = []
            for item_data in meal_data.get("items", []):
                food_name = item_data.get("food", "")
                food = foods_by_name.get(food_name)
                if food is None:
                    for fn, fobj in foods_by_name.items():
                        if fn.lower() == food_name.lower():
                            food = fobj
                            break
                if food is None:
                    skipped += 1
                    continue
                qty = max(10, min(float(item_data.get("quantity", 100)), 2000))
                items.append((food.id, qty))

            if not items:
                skipped += 1
                continue

            normalized.append({
                "day": offset + rel_day,
                "meal_type": meal_type,
                "name": str(meal_data.get("name", "Repas"))[:150],
                "items": items,
            })

    if not normalized:
        return _classic_fallback(user, num_days, foods_by_name, "parse_error: no meals")

    # ── Sauvegarde en base ──────────────────────────────────────────
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
        for m in normalized:
            meal = Meal(
                meal_plan_id=plan.id,
                day=m["day"],
                meal_type=m["meal_type"],
                name=m["name"],
            )
            db.session.add(meal)
            db.session.flush()
            for food_id, qty in m["items"]:
                db.session.add(MealItem(meal_id=meal.id, food_id=food_id, quantity=qty))
                valid_meals += 1

        db.session.commit()
        logger.info(f"Plan IA sauvegardé: {len(normalized)} repas, {valid_meals} items, {skipped} skippés")

        info = {
            "mode": "ai",
            "provider": (last_provider or {}).get("provider"),
            "provider_label": (last_provider or {}).get("label"),
            "model": (last_provider or {}).get("model"),
            "meals_generated": valid_meals,
            "skipped": skipped,
        }
        return plan, info

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur sauvegarde plan IA: {e} — fallback classique")
        return _classic_fallback(user, num_days, foods_by_name, f"db_error: {str(e)[:200]}")
