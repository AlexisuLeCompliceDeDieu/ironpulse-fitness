from flask import Blueprint, request, jsonify, session
from models import db, Food, MealPlan, ShoppingList
from services import meal_generator, nutrition as nutrition_service

nutrition_bp = Blueprint("nutrition", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    from models import User
    return db.session.get(User, user_id)


def foods_by_name():
    return {f.name: f for f in Food.query.all()}


@nutrition_bp.route("/foods", methods=["GET"])
def list_foods():
    foods = Food.query.order_by(Food.name).all()
    return jsonify({"foods": [f.to_dict() for f in foods]}), 200


@nutrition_bp.route("/plan/generate", methods=["POST"])
def generate_plan():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json(silent=True) or {}
    num_days = int(data.get("num_days", 7))
    num_days = max(1, min(num_days, 14))

    if user.daily_calories and "daily_calories" not in data:
        pass  # on garde l'objectif actuel

    foods = foods_by_name()
    if not foods:
        return jsonify({"error": "Base d'aliments vide"}), 500

    plan = meal_generator.generate_meal_plan(user, num_days, foods)

    # Supprimer les anciens plans sauf celui-ci
    meal_generator.remove_old_plans(user.id, plan.id)

    return jsonify({"message": "Plan généré", "plan": plan.to_dict()}), 201


@nutrition_bp.route("/target", methods=["GET"])
def calorie_target():
    """Objectif calorique : valeur suggérée (calculée) et valeur utilisée."""
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    suggested = nutrition_service.compute_daily_calories(user)
    return jsonify({
        "suggested": suggested,
        "current": nutrition_service.current_calories(user),
        "calories_auto": bool(user.calories_auto),
    }), 200


@nutrition_bp.route("/shopping-list/generate", methods=["POST"])
def generate_shopping_list():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json(silent=True) or {}
    plan_id = data.get("meal_plan_id")
    if plan_id:
        plan = MealPlan.query.filter_by(id=plan_id, user_id=user.id).first()
    else:
        plan = MealPlan.query.filter_by(user_id=user.id).order_by(MealPlan.id.desc()).first()

    if not plan:
        return jsonify({"error": "Aucun plan trouvé"}), 404

    foods = foods_by_name()
    shopping_list = meal_generator.build_shopping_list(plan, foods)
    return jsonify({"message": "Liste générée", "shopping_list": shopping_list.to_dict()}), 201


@nutrition_bp.route("/plan/latest", methods=["GET"])
def latest_plan():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    plan = MealPlan.query.filter_by(user_id=user.id).order_by(MealPlan.id.desc()).first()
    if not plan:
        return jsonify({"message": "Aucun plan"}), 404
    return jsonify({"plan": plan.to_dict()}), 200


@nutrition_bp.route("/shopping-list/latest", methods=["GET"])
def latest_shopping_list():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    sl = ShoppingList.query.filter_by(user_id=user.id).order_by(ShoppingList.id.desc()).first()
    if not sl:
        return jsonify({"message": "Aucune liste"}), 404
    return jsonify({"shopping_list": sl.to_dict()}), 200
