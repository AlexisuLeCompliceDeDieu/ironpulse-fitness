from flask import Blueprint, request, jsonify, session
from models import (
    db, User, WeightEntry, TrainingProgram, ProgramDay, Session, SessionSet,
    MealPlan, ShoppingList,
)
from datetime import date

profile_bp = Blueprint("profile", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


@profile_bp.route("/", methods=["GET"])
def get_profile():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    return jsonify({"user": user.to_dict()}), 200


@profile_bp.route("/", methods=["PUT"])
def update_profile():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json()
    editable = ["goal", "level", "weight", "target_weight", "height", "age", "daily_calories"]
    for field in editable:
        if field in data:
            setattr(user, field, data[field])

    # Calories : si on passe explicitement calories_auto, on l'applique.
    # Sinon, une saisie manuelle de daily_calories bascule en manuel.
    if "calories_auto" in data:
        user.calories_auto = bool(data["calories_auto"])
        if user.calories_auto:
            from services.nutrition import compute_daily_calories
            user.daily_calories = compute_daily_calories(user)
    elif "daily_calories" in data:
        user.calories_auto = False

    if "split_type" in data:
        user.split_type = data["split_type"] or None
    if "sessions_per_week" in data:
        val = data.get("sessions_per_week")
        user.sessions_per_week = int(val) if val else None

    if "available_equipment" in data:
        eq = data["available_equipment"]
        if isinstance(eq, list):
            import json
            user.available_equipment = json.dumps(list(dict.fromkeys(eq)))

    if "dietary_preferences" in data:
        prefs = data["dietary_preferences"]
        if isinstance(prefs, list):
            import json
            user.dietary_preferences = json.dumps(list(dict.fromkeys(prefs)))

    db.session.commit()
    return jsonify({"message": "Profil mis à jour", "user": user.to_dict()}), 200


@profile_bp.route("/weight", methods=["POST"])
def add_weight():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json()
    weight = data.get("weight")
    weight_date = date.fromisoformat(data.get("date")) if data.get("date") else date.today()

    # Un seul poids par jour : on remplace l'éventuelle valeur du même jour
    entry = WeightEntry.query.filter_by(user_id=user.id, date=weight_date).first()
    if entry:
        previous = entry.weight
        entry.weight = weight
        action = "replaced"
    else:
        entry = WeightEntry(user_id=user.id, weight=weight, date=weight_date)
        db.session.add(entry)
        previous = None
        action = "created"

    if user.weight is None:
        user.weight = weight
    db.session.commit()
    return jsonify(
        {"message": "Poids enregistré", "action": action, "previous": previous, "entry": entry.to_dict()}
    ), 201


@profile_bp.route("/weight", methods=["GET"])
def get_weights():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    entries = WeightEntry.query.filter_by(user_id=user.id).order_by(WeightEntry.date).all()
    return jsonify({"entries": [e.to_dict() for e in entries]}), 200


@profile_bp.route("/export", methods=["GET"])
def export_data():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    programs = TrainingProgram.query.filter_by(user_id=user.id).all()
    sessions = Session.query.filter_by(user_id=user.id).order_by(Session.date).all()
    meal_plans = MealPlan.query.filter_by(user_id=user.id).all()
    shopping_lists = ShoppingList.query.filter_by(user_id=user.id).all()

    def session_with_exercises(s):
        d = s.to_dict()
        d["sets"] = [
            {**set_obj.to_dict(),
             "exercise_name": set_obj.exercise.name if set_obj.exercise else None}
            for set_obj in s.sets
        ]
        return d

    payload = {
        "exporter": "Agent IA Fitness",
        "exported_at": date.today().isoformat(),
        "user": user.to_dict(),
        "weight_entries": [e.to_dict() for e in
                           WeightEntry.query.filter_by(user_id=user.id).order_by(WeightEntry.date).all()],
        "training_programs": [p.to_dict() for p in programs],
        "sessions": [session_with_exercises(s) for s in sessions],
        "meal_plans": [mp.to_dict() for mp in meal_plans],
        "shopping_lists": [sl.to_dict() for sl in shopping_lists],
    }
    return jsonify(payload), 200


@profile_bp.route("/account", methods=["DELETE"])
def delete_account():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    for mp in MealPlan.query.filter_by(user_id=user.id).all():
        db.session.delete(mp)
    for sl in ShoppingList.query.filter_by(user_id=user.id).all():
        db.session.delete(sl)
    for s in Session.query.filter_by(user_id=user.id).all():
        db.session.delete(s)
    for p in TrainingProgram.query.filter_by(user_id=user.id).all():
        db.session.delete(p)
    for e in WeightEntry.query.filter_by(user_id=user.id).all():
        db.session.delete(e)
    db.session.delete(user)
    db.session.commit()

    session.clear()
    return jsonify({"message": "Compte et données supprimés"}), 200
