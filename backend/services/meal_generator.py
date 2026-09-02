"""Logique de génération de repas et listes de courses.

Algorithme:
  - Répartition des macronutriments selon l'objectif calorique
  - Recettes variées à partir d'une base d'aliments
  - Agrégation des ingrédients en liste de courses
"""

import json

# Recettes: nom -> liste (food_name, quantite_grammes)
# Basées sur les aliments présents dans foods.json
RECIPES = [
    # ------- Petit-déjeuner -------
    {"name": "Omelette aux épinards", "meal_type": "Petit-déjeuner", "items": [["Œufs", 160], ["Épinards", 80], ["Tomates", 60]]},
    {"name": "Porridge avoine et banane", "meal_type": "Petit-déjeuner", "items": [["Avoine", 80], ["Banane", 100], ["Myrtilles", 40]]},
    {"name": "Omelette et avoine", "meal_type": "Petit-déjeuner", "items": [["Œufs", 140], ["Avoine", 60], ["Avocat", 40]]},
    {"name": "Omelette et patates douces", "meal_type": "Petit-déjeuner", "items": [["Œufs", 160], ["Patates douces", 250], ["Avocat", 50]]},
    {"name": "Bowl de fromage blanc et fruits", "meal_type": "Petit-déjeuner", "items": [["Fromage blanc", 200], ["Fraise", 80], ["Avoine", 30]]},
    {"name": "Tartines au beurre de cacahuète", "meal_type": "Petit-déjeuner", "items": [["Pain complet", 90], ["Beurre de cacahuète", 30], ["Banane", 60]]},
    {"name": "Porridge protéiné au beurre de cacahuète", "meal_type": "Petit-déjeuner", "items": [["Avoine", 70], ["Beurre de cacahuète", 30], ["Banane", 80]]},
    {"name": "Cottage cheese et fruits rouges", "meal_type": "Petit-déjeuner", "items": [["Cottage cheese", 200], ["Myrtilles", 80], ["Amandes", 25]]},
    {"name": "Shake petit-déjeuner à la whey", "meal_type": "Petit-déjeuner", "items": [["Protéine en poudre (whey)", 40], ["Banane", 100], ["Avoine", 40]]},
    {"name": "Œufs brouillés et avocat", "meal_type": "Petit-déjeuner", "items": [["Œufs", 160], ["Avocat", 70], ["Pain complet", 60]]},
    {"name": "Bowl d'avoine aux amandes", "meal_type": "Petit-déjeuner", "items": [["Avoine", 80], ["Yaourt grec", 120], ["Amandes", 25]]},
    {"name": "Crêpes de banane aux œufs", "meal_type": "Petit-déjeuner", "items": [["Œufs", 140], ["Banane", 100], ["Avoine", 40]]},
    # ------- Déjeuner -------
    {"name": "Poulet, riz et brocoli", "meal_type": "Déjeuner", "items": [["Blanc de poulet", 200], ["Riz basmati cuit", 250], ["Brocoli", 150]]},
    {"name": "Haricots rouges et riz", "meal_type": "Déjeuner", "items": [["Haricots rouges", 200], ["Riz basmati cuit", 200], ["Avocat", 40]]},
    {"name": "Bœuf haché et riz complet", "meal_type": "Déjeuner", "items": [["Bœuf haché 5%", 180], ["Riz complet cuit", 250], ["Poivron rouge", 80]]},
    {"name": "Dinde, quinoa et courgettes", "meal_type": "Déjeuner", "items": [["Escalope de dinde", 180], ["Quinoa cuit", 200], ["Courgettes", 150]]},
    {"name": "Wok de crevettes et riz", "meal_type": "Déjeuner", "items": [["Crevettes", 180], ["Riz basmati cuit", 200], ["Poivron rouge", 80], ["Carottes", 60]]},
    {"name": "Poulet au curry et riz", "meal_type": "Déjeuner", "items": [["Blanc de poulet", 200], ["Riz basmati cuit", 220], ["Épinards", 80]]},
    {"name": "Pois chiches, semoule et légumes", "meal_type": "Déjeuner", "items": [["Pois chiches", 180], ["Semoule de blé cuite", 200], ["Tomates", 80]]},
    {"name": "Lentilles et riz", "meal_type": "Déjeuner", "items": [["Lentilles", 200], ["Riz complet cuit", 200], ["Carottes", 60]]},
    {"name": "Tofu sauté au quinoa", "meal_type": "Déjeuner", "items": [["Tofu", 180], ["Quinoa cuit", 200], ["Brocoli", 120]]},
    {"name": "Poulet, pâtes et tomates", "meal_type": "Déjeuner", "items": [["Blanc de poulet", 190], ["Pâtes complètes cuites", 220], ["Tomates", 80]]},
    {"name": "Couscous au poulet et légumes", "meal_type": "Déjeuner", "items": [["Blanc de poulet", 190], ["Couscous cuit", 220], ["Carottes", 60], ["Courgettes", 80]]},
    {"name": "Bowl thon, haricots et maïs", "meal_type": "Déjeuner", "items": [["Thon", 150], ["Haricots rouges", 150], ["Salade verte", 80]]},
    # ------- Dîner -------
    {"name": "Saumon et quinoa", "meal_type": "Dîner", "items": [["Saumon", 180], ["Quinoa cuit", 200], ["Brocoli", 120]]},
    {"name": "Saumon, riz et brocoli", "meal_type": "Dîner", "items": [["Saumon", 170], ["Riz basmati cuit", 220], ["Brocoli", 120]]},
    {"name": "Poulet grillé, patates et salade", "meal_type": "Dîner", "items": [["Blanc de poulet", 200], ["Patates douces", 250], ["Avocat", 40]]},
    {"name": "Poisson blanc, patates et haricots verts", "meal_type": "Dîner", "items": [["Thon", 180], ["Patates douces", 220], ["Haricots verts", 120]]},
    {"name": "Omelette aux légumes et quinoa", "meal_type": "Dîner", "items": [["Œufs", 160], ["Quinoa cuit", 180], ["Poivron rouge", 80]]},
    {"name": "Dinde, patates et courgettes", "meal_type": "Dîner", "items": [["Escalope de dinde", 180], ["Patates douces", 220], ["Courgettes", 130]]},
    {"name": "Crevettes, quinoa et épinards", "meal_type": "Dîner", "items": [["Crevettes", 180], ["Quinoa cuit", 180], ["Épinards", 100]]},
    {"name": "Poulet, patates douces et brocoli", "meal_type": "Dîner", "items": [["Blanc de poulet", 200], ["Patates douces", 240], ["Brocoli", 130]]},
    {"name": "Tofu, riz et légumes sautés", "meal_type": "Dîner", "items": [["Tofu", 180], ["Riz complet cuit", 200], ["Champignons", 100]]},
    {"name": "Bœuf haché, patates et haricots verts", "meal_type": "Dîner", "items": [["Bœuf haché 5%", 180], ["Patates douces", 220], ["Haricots verts", 120]]},
    {"name": "Saumon, couscous et courgettes", "meal_type": "Dîner", "items": [["Saumon", 170], ["Couscous cuit", 200], ["Courgettes", 120]]},
    {"name": "Soupe légumes et lentilles", "meal_type": "Dîner", "items": [["Lentilles", 150], ["Carottes", 80], ["Oignon", 50], ["Champignons", 60]]},
    # ------- Collation -------
    {"name": "Shake protéiné", "meal_type": "Collation", "items": [["Protéine en poudre (whey)", 40], ["Banane", 100], ["Avoine", 40]]},
    {"name": "Yaourt grec aux fruits", "meal_type": "Collation", "items": [["Yaourt grec", 200], ["Banane", 80], ["Amandes", 30]]},
    {"name": "Fromage blanc aux fruits rouges", "meal_type": "Collation", "items": [["Fromage blanc", 200], ["Fraise", 80], ["Graines de chia", 15]]},
    {"name": "Pomme et beurre de cacahuète", "meal_type": "Collation", "items": [["Pomme", 150], ["Beurre de cacahuète", 25]]},
    {"name": "Cottage cheese et noix de cajou", "meal_type": "Collation", "items": [["Cottage cheese", 180], ["Noix de cajou", 25]]},
    {"name": "Œufs durs et orange", "meal_type": "Collation", "items": [["Œufs", 110], ["Orange", 150]]},
    {"name": "Yaourt grec et graines de chia", "meal_type": "Collation", "items": [["Yaourt grec", 200], ["Graines de chia", 15], ["Myrtilles", 60]]},
    {"name": "Banane et amandes", "meal_type": "Collation", "items": [["Banane", 120], ["Amandes", 25]]},
    {"name": "Edam et pomme", "meal_type": "Collation", "items": [["Édam", 60], ["Pomme", 150]]},
    {"name": "Shake protéiné aux fruits rouges", "meal_type": "Collation", "items": [["Protéine en poudre (whey)", 35], ["Fraise", 80], ["Avoine", 30]]},
    {"name": "Tartines d'avocat et œuf", "meal_type": "Collation", "items": [["Pain complet", 60], ["Avocat", 50], ["Œufs", 55]]},
    {"name": "Yaourt grec, pomme et noix de cajou", "meal_type": "Collation", "items": [["Yaourt grec", 180], ["Pomme", 100], ["Noix de cajou", 20]]},
]

MEAL_TYPES_PER_DAY = ["Petit-déjeuner", "Déjeuner", "Collation", "Dîner"]

EXCLUDED_TAGS = {
    "vegetarien": {"viande", "poisson"},
    "vegan": {"viande", "poisson", "oeuf", "lactier"},
    "sans_lactose": {"lactier"},
    "sans_gluten": {"gluten"},
    "sans_noix": {"noix"},
}


def _recipe_is_compatible(recipe, user_preferences, foods_by_name):
    excluded = set()
    for pref in user_preferences:
        excluded |= EXCLUDED_TAGS.get(pref, set())
    if not excluded:
        return True
    for food_name, _ in recipe["items"]:
        food = foods_by_name.get(food_name)
        if food is None:
            continue
        food_tags = food.tags_list()
        if excluded & set(food_tags):
            return False
    return True


def generate_meal_plan(user, num_days, foods_by_name):
    """Génère un plan alimentaire pour `num_days` jours avec un objectif calorique."""
    from models import MealPlan, Meal, MealItem, db

    target_calories = user.daily_calories or 2500
    preferences = user.preferences_list() if hasattr(user, "preferences_list") else []

    plan = MealPlan(
        user_id=user.id,
        num_days=num_days,
        target_calories=target_calories,
    )
    db.session.add(plan)
    db.session.flush()

    # Rotation des recettes pour varier les menus
    used = {}  # recette -> compteur

    def pick_for(type_):
        pool = [r for r in RECIPES if r["meal_type"] == type_]
        if not pool:
            pool = RECIPES
        pool = [r for r in pool if _recipe_is_compatible(r, preferences, foods_by_name)]
        if not pool:
            pool = [r for r in RECIPES if _recipe_is_compatible(r, preferences, foods_by_name)]
        if not pool:
            pool = RECIPES
        pool_sorted = sorted(pool, key=lambda r: used.get(r["name"], 0))
        chosen = pool_sorted[0]
        used[chosen["name"]] = used.get(chosen["name"], 0) + 1
        return chosen

    for day in range(1, num_days + 1):
        for type_ in MEAL_TYPES_PER_DAY:
            recipe = pick_for(type_)
            meal = Meal(
                meal_plan_id=plan.id,
                day=day,
                meal_type=type_,
                name=recipe["name"],
            )
            db.session.add(meal)
            db.session.flush()
            for food_name, qty in recipe["items"]:
                food = foods_by_name.get(food_name)
                if food is None:
                    continue
                db.session.add(MealItem(meal_id=meal.id, food_id=food.id, quantity=qty))

    db.session.commit()
    return plan


def build_shopping_list(plan, foods_by_name):
    """Agrège tous les ingrédients du plan en une liste de courses (grammes)."""
    from models import ShoppingList, db

    aggregate = {}
    for meal in plan.meals:
        for item in meal.items:
            aggregate[item.food.name] = aggregate.get(item.food.name, 0) + item.quantity

    items = [{"name": name, "qty_grams": round(qty, 1)} for name, qty in aggregate.items()]
    list_obj = ShoppingList(user_id=plan.user_id, meal_plan_id=plan.id, items=json.dumps(items))
    db.session.add(list_obj)
    db.session.commit()
    return list_obj


def remove_old_plans(user_id, keep_id):
    """Supprime les anciens plans du même utilisateur sauf celui gardé."""
    from models import MealPlan, db
    MealPlan.query.filter(MealPlan.user_id == user_id, MealPlan.id != keep_id).delete()
    db.session.commit()
