from flask import Blueprint, request, jsonify, session
from models import db, User, WeightEntry
from datetime import date

profile_bp = Blueprint("profile", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


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

    entry = WeightEntry(user_id=user.id, weight=weight, date=weight_date)
    db.session.add(entry)
    if user.weight is None:
        user.weight = weight
    db.session.commit()
    return jsonify({"message": "Poids enregistré", "entry": entry.to_dict()}), 201


@profile_bp.route("/weight", methods=["GET"])
def get_weights():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    entries = WeightEntry.query.filter_by(user_id=user.id).order_by(WeightEntry.date).all()
    return jsonify({"entries": [e.to_dict() for e in entries]}), 200
