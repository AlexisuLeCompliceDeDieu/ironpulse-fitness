from flask import Blueprint, request, jsonify, session
from models import db, Exercise

exercises_bp = Blueprint("exercises", __name__)


@exercises_bp.route("/", methods=["GET"])
def list_exercises():
    category = request.args.get("category")
    equipment = request.args.get("equipment")
    muscle = request.args.get("muscle_group")

    query = Exercise.query
    if category:
        query = query.filter_by(category=category)
    if equipment:
        query = query.filter(Exercise.equipment_needed == equipment)
    if muscle:
        query = query.filter_by(muscle_group=muscle)

    exercises = query.order_by(Exercise.name).all()
    return jsonify({"exercises": [e.to_dict() for e in exercises]}), 200


@exercises_bp.route("/<int:exercise_id>", methods=["GET"])
def get_exercise(exercise_id):
    exercise = Exercise.query.get(exercise_id)
    if not exercise:
        return jsonify({"error": "Exercice introuvable"}), 404
    return jsonify({"exercise": exercise.to_dict()}), 200


@exercises_bp.route("/<int:exercise_id>/alternatives", methods=["GET"])
def get_alternatives(exercise_id):
    exercise = Exercise.query.get(exercise_id)
    if not exercise:
        return jsonify({"error": "Exercice introuvable"}), 404

    alternatives = (
        Exercise.query
        .filter(Exercise.muscle_group == exercise.muscle_group)
        .filter(Exercise.id != exercise.id)
        .all()
    )
    return jsonify({"alternatives": [a.to_dict() for a in alternatives]}), 200
