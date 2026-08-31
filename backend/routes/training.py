from flask import Blueprint, jsonify, session
from datetime import date, timedelta
from models import (
    TrainingProgram, Session, SessionSet, db,
)
from services import program_generator, adaptation

training_bp = Blueprint("training", __name__)


from flask import request

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    from models import User
    return User.query.get(user_id)


@training_bp.route("/program/generate", methods=["POST"])
def generate():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    program = program_generator.generate_program(user)
    return jsonify({"message": "Programme généré", "program": program.to_dict()}), 201


@training_bp.route("/program/current", methods=["GET"])
def current_program():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    program = TrainingProgram.query.filter_by(user_id=user.id, is_active=True).first()
    if not program:
        return jsonify({"message": "Aucun programme actif"}), 404
    return jsonify({"program": program.to_dict()}), 200


@training_bp.route("/program/<int:program_id>", methods=["GET"])
def get_program(program_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    program = TrainingProgram.query.filter_by(id=program_id, user_id=user.id).first()
    if not program:
        return jsonify({"error": "Programme introuvable"}), 404
    return jsonify({"program": program.to_dict()}), 200


@training_bp.route("/exercises/<int:exercise_id>/alternative", methods=["POST"])
def replace_exercise(exercise_id):
    """Remplace un exercice par une alternative compatible avec le matériel."""
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json(silent=True) or {}
    available_equipment = data.get("available_equipment", [])

    from models import Exercise
    exercise = Exercise.query.get(exercise_id)
    if not exercise:
        return jsonify({"error": "Exercice introuvable"}), 404

    alternative = adaptation.get_alternative_for(exercise, available_equipment)
    if not alternative:
        return jsonify({"error": "Aucune alternative trouvée"}), 404
    return jsonify({"alternative": alternative.to_dict()}), 200
