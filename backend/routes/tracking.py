from flask import Blueprint, request, jsonify, session
from datetime import date
from models import db, Session, SessionSet
from services import anti_cheat

tracking_bp = Blueprint("tracking", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    from models import User
    return db.session.get(User, user_id)


@tracking_bp.route("/sessions", methods=["POST"])
def create_session():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json()
    program_day_id = data.get("program_day_id")
    session_date = date.fromisoformat(data["date"]) if data.get("date") else date.today()
    feeling = data.get("feeling", 3)
    notes = data.get("notes", "")

    session_obj = Session(
        user_id=user.id,
        program_day_id=program_day_id,
        date=session_date,
        feeling=feeling,
        notes=notes,
        completed=True,
    )
    db.session.add(session_obj)
    db.session.flush()

    # data["sets"] est une liste de {exercise_id, set_number, weight, reps, [difficulty]}
    for set_data in data.get("sets", []):
        db.session.add(SessionSet(
            session_id=session_obj.id,
            exercise_id=set_data["exercise_id"],
            set_number=set_data.get("set_number", 1),
            weight=set_data.get("weight", 0.0),
            reps=set_data.get("reps", 0),
            completed=set_data.get("completed", True),
            difficulty=set_data.get("difficulty", ""),
        ))

    # Anti-triche : signale les séances suspectes (volume/rythme anormaux)
    session_obj.flagged = anti_cheat.flag_suspicious(user, session_obj, data)

    db.session.commit()
    return jsonify({"message": "Séance enregistrée", "session": session_obj.to_dict()}), 201


@tracking_bp.route("/sessions", methods=["GET"])
def list_sessions():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    sessions = Session.query.filter_by(user_id=user.id).order_by(Session.date.desc()).all()
    return jsonify({"sessions": [s.to_dict() for s in sessions]}), 200


@tracking_bp.route("/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    session_obj = Session.query.filter_by(id=session_id, user_id=user.id).first()
    if not session_obj:
        return jsonify({"error": "Séance introuvable"}), 404
    return jsonify({"session": session_obj.to_dict()}), 200


@tracking_bp.route("/sessions/<int:session_id>", methods=["PUT"])
def update_session(session_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    session_obj = Session.query.filter_by(id=session_id, user_id=user.id).first()
    if not session_obj:
        return jsonify({"error": "Séance introuvable"}), 404

    data = request.get_json()
    if "feeling" in data:
        session_obj.feeling = data["feeling"]
    if "notes" in data:
        session_obj.notes = data["notes"]
    if "sets" in data:
        session_obj.sets.clear()
        for set_data in data["sets"]:
            db.session.add(SessionSet(
                session_id=session_obj.id,
                exercise_id=set_data["exercise_id"],
                set_number=set_data.get("set_number", 1),
                weight=set_data.get("weight", 0.0),
                reps=set_data.get("reps", 0),
                completed=set_data.get("completed", True),
                difficulty=set_data.get("difficulty", ""),
            ))

    db.session.commit()
    return jsonify({"message": "Séance mise à jour", "session": session_obj.to_dict()}), 200
