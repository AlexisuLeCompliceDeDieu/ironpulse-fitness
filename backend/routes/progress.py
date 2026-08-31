from flask import Blueprint, jsonify, session
from models import Session, SessionSet, WeightEntry

progress_bp = Blueprint("progress", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    from models import User
    return User.query.get(user_id)


@progress_bp.route("/weights", methods=["GET"])
def weight_progress():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    entries = WeightEntry.query.filter_by(user_id=user.id).order_by(WeightEntry.date).all()
    return jsonify({"entries": [e.to_dict() for e in entries]}), 200


@progress_bp.route("/exercises/<int:exercise_id>", methods=["GET"])
def exercise_progress(exercise_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    session_ids = [s.id for s in Session.query.filter_by(user_id=user.id).all()]
    if not session_ids:
        return jsonify({"data": []}), 200

    records = (
        SessionSet.query
        .join(Session)
        .filter(SessionSet.exercise_id == exercise_id)
        .filter(Session.id.in_(session_ids))
        .order_by(Session.date)
        .all()
    )

    data = {}
    for record in records:
        session = Session.query.get(record.session_id)
        key = session.date.isoformat()
        if key not in data:
            data[key] = {"date": key, "max_weight": 0, "total_volume": 0, "sets": 0}
        data[key]["max_weight"] = max(data[key]["max_weight"], record.weight or 0)
        data[key]["total_volume"] += (record.weight or 0) * (record.reps or 0)
        data[key]["sets"] += 1

    return jsonify({"data": list(data.values())}), 200


@progress_bp.route("/stats", methods=["GET"])
def session_stats():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401
    sessions = Session.query.filter_by(user_id=user.id).all()
    total_sessions = len(sessions)
    total_volume = 0
    avg_feeling = 0
    for s in sessions:
        for set_obj in s.sets:
            total_volume += (set_obj.weight or 0) * (set_obj.reps or 0)
        avg_feeling += s.feeling
    avg_feeling = avg_feeling / total_sessions if total_sessions else 0
    return jsonify({
        "total_sessions": total_sessions,
        "total_volume": total_volume,
        "avg_feeling": round(avg_feeling, 1),
    }), 200


@progress_bp.route("/advice", methods=["GET"])
def advice():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    sessions = Session.query.filter_by(user_id=user.id).all()
    total_sessions = len(sessions)
    total_volume = 0
    avg_feeling = 0
    for s in sessions:
        for set_obj in s.sets:
            total_volume += (set_obj.weight or 0) * (set_obj.reps or 0)
        avg_feeling += s.feeling
    avg_feeling = avg_feeling / total_sessions if total_sessions else 0

    stats = {
        "total_sessions": total_sessions,
        "total_volume": total_volume,
        "avg_feeling": round(avg_feeling, 1),
    }

    from services import advice as advice_service
    return jsonify({"advice": advice_service.generate_advice(user, stats)}), 200
