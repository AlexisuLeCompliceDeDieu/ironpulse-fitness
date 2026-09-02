from flask import Blueprint, request, jsonify, session
from datetime import date, timedelta
from models import db, User, Friendship, Session
from services import anti_cheat

social_bp = Blueprint("social", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def _user_light(u):
    return {
        "id": u.id,
        "username": u.username,
        "goal": u.goal,
        "level": u.level,
    }


def _friend_ids(user):
    """Ids des amis validés (statut 'accepted'), dans les deux sens."""
    rows_a = Friendship.query.filter_by(user_id=user.id, status="accepted").all()
    rows_b = Friendship.query.filter_by(friend_id=user.id, status="accepted").all()
    ids = {r.friend_id for r in rows_a} | {r.user_id for r in rows_b}
    ids.discard(user.id)
    return ids


def _find_request(sender_id, user_id):
    """Demande en attente envoyée par sender_id vers user_id."""
    return Friendship.query.filter_by(
        user_id=sender_id, friend_id=user_id, status="pending"
    ).first()


@social_bp.route("/friends", methods=["GET"])
def list_friends():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    friends = []
    ids = _friend_ids(user)
    for uid in ids:
        u = db.session.get(User, uid)
        if u:
            stats = _stats_between(u.id, date.today() - timedelta(days=7), date.today())
            friends.append({**_user_light(u), **stats})
    friends.sort(key=lambda f: f.get("volume_7d", 0), reverse=True)
    return jsonify({"friends": friends}), 200


@social_bp.route("/friends", methods=["POST"])
def add_friend():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json() or {}
    email = data.get("email") or data.get("username")
    if not email:
        return jsonify({"error": "Email ou nom d'utilisateur requis"}), 400

    friend = User.query.filter(
        (User.email == email) | (User.username == email)
    ).first()
    if not friend:
        return jsonify({"error": "Aucun compte trouvé avec cet identifiant"}), 404
    if friend.id == user.id:
        return jsonify({"error": "Impossible de vous ajouter vous-même"}), 400

    existing = Friendship.query.filter_by(user_id=user.id, friend_id=friend.id).first()
    if existing:
        if existing.status == "accepted":
            return jsonify({"error": "Déjà amis !"}), 409
        return jsonify({"error": "Demande déjà envoyée, en attente de réponse"}), 409

    # Demande inverse déjà en attente : l'ajout devient une acceptation mutuelle.
    paired = Friendship.query.filter_by(user_id=friend.id, friend_id=user.id).first()
    if paired:
        if paired.status == "accepted":
            return jsonify({"error": "Déjà amis !"}), 409
        paired.status = "accepted"
        reverse = Friendship.query.filter_by(user_id=user.id, friend_id=friend.id).first()
        if reverse:
            reverse.status = "accepted"
        db.session.commit()
        return jsonify({"message": f"{friend.username} attendait ta demande : vous êtes amis !", "friend": _user_light(friend)}), 201

    db.session.add(Friendship(user_id=user.id, friend_id=friend.id, status="pending"))
    db.session.commit()
    return jsonify({"message": f"Demande envoyée à {friend.username} ! En attente de sa validation.", "friend": _user_light(friend)}), 201


@social_bp.route("/friends/requests", methods=["GET"])
def list_requests():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    incoming = Friendship.query.filter_by(friend_id=user.id, status="pending").all()
    outgoing = Friendship.query.filter_by(user_id=user.id, status="pending").all()

    def to_light(row, side):
        other = db.session.get(User, row.user_id if side == "incoming" else row.friend_id)
        if not other:
            return None
        return {"friendship_id": row.id, "user": _user_light(other)}

    return jsonify({
        "incoming": [x["user"] for x in (to_light(r, "incoming") for r in incoming) if x],
        "outgoing": [x["user"] for x in (to_light(r, "outgoing") for r in outgoing) if x],
        "incoming_ids": [r.id for r in incoming],
        "outgoing_ids": [r.id for r in outgoing],
    }), 200


@social_bp.route("/friends/accept", methods=["POST"])
def accept_friend():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json() or {}
    sender_id = data.get("friend_id") or data.get("user_id")
    if not sender_id:
        return jsonify({"error": "friend_id requis"}), 400

    req = _find_request(int(sender_id), user.id)
    if not req:
        return jsonify({"error": "Aucune demande en attente de cet utilisateur"}), 404

    req.status = "accepted"
    reverse = Friendship.query.filter_by(user_id=user.id, friend_id=int(sender_id), status="pending").first()
    if reverse:
        reverse.status = "accepted"
    db.session.commit()
    sender = db.session.get(User, int(sender_id))
    return jsonify({"message": f"{sender.username if sender else 'Le compte'} est maintenant votre ami !", "friend": _user_light(sender) if sender else None}), 200


@social_bp.route("/friends/decline", methods=["POST"])
def decline_friend():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json() or {}
    sender_id = data.get("friend_id") or data.get("user_id")
    if not sender_id:
        return jsonify({"error": "friend_id requis"}), 400

    req = _find_request(int(sender_id), user.id)
    if not req:
        return jsonify({"error": "Aucune demande en attente de cet utilisateur"}), 404

    db.session.delete(req)
    reverse = Friendship.query.filter_by(user_id=user.id, friend_id=int(sender_id), status="pending").first()
    if reverse:
        db.session.delete(reverse)
    db.session.commit()
    return jsonify({"message": "Demande refusée"}), 200


@social_bp.route("/friends/<int:friend_id>", methods=["DELETE"])
def remove_friend(friend_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    Friendship.query.filter_by(user_id=user.id, friend_id=friend_id).delete()
    Friendship.query.filter_by(user_id=friend_id, friend_id=user.id).delete()
    db.session.commit()
    return jsonify({"message": "Ami retiré"}), 200


def _stats_between(user_id, start, end):
    sessions = Session.query.filter(
        Session.user_id == user_id,
        Session.date >= start,
        Session.date <= end,
        Session.flagged.is_(False),
    ).all()
    volume = 0.0
    total_sets = 0
    for s in sessions:
        volume += anti_cheat.session_volume(s)
        total_sets += sum(1 for x in s.sets if x.completed and x.reps and x.reps > 0)
    return {"volume_7d": round(volume), "sessions_7d": len(sessions), "sets_7d": total_sets}


@social_bp.route("/leaderboard", methods=["GET"])
def leaderboard():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    today = date.today()
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)

    # Classement hebdo : joueur + amis
    members = [user] + [db.session.get(User, uid) for uid in _friend_ids(user) if db.session.get(User, uid)]
    rows = []
    for u in members:
        if not u:
            continue
        w7 = _stats_between(u.id, week_start, today)
        w30 = _stats_between(u.id, month_start, today)
        rows.append({
            "user": _user_light(u),
            **{f"week_{k}": v for k, v in w7.items()},
            **{f"month_{k}": v for k, v in w30.items()},
            "me": u.id == user.id,
        })
    rows.sort(key=lambda r: r["week_volume_7d"], reverse=True)

    # Anti-triche : compteur de séances signalées
    flagged_count = Session.query.filter(
        Session.user_id == user.id, Session.flagged.is_(True)
    ).count()

    return jsonify({"leaderboard": rows, "my_flagged_sessions": flagged_count}), 200