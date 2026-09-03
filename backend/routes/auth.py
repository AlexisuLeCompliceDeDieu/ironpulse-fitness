from flask import Blueprint, request, jsonify, session
from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Champs requis manquants"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Nom d'utilisateur déjà pris"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email déjà utilisé"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    user.goal = data.get("goal", "prise_masse")
    user.level = data.get("level", "debutant")
    if data.get("weight") is not None:
        user.weight = data["weight"]
    if data.get("target_weight") is not None:
        user.target_weight = data["target_weight"]
    if data.get("height") is not None:
        user.height = data["height"]
    if data.get("age") is not None:
        user.age = data["age"]
    if data.get("daily_calories") is not None:
        user.daily_calories = int(data["daily_calories"])
    if data.get("split_type") is not None:
        user.split_type = data["split_type"] or None
    if data.get("sessions_per_week") is not None:
        val = data.get("sessions_per_week")
        user.sessions_per_week = int(val) if val else None

    db.session.add(user)
    db.session.flush()  # matérialise les valeurs par défaut (poids, taille, âge)

    # Calories : par défaut calculées automatiquement depuis le profil renseigné.
    # Si l'utilisateur a fourni explicitement une valeur (ou désactivé l'auto),
    # on garde sa saisie manuelle.
    from services.nutrition import compute_daily_calories
    daily_calories_provided = data.get("daily_calories") is not None
    calories_auto = data.get("calories_auto", not daily_calories_provided)
    user.calories_auto = bool(calories_auto)
    if calories_auto:
        user.daily_calories = compute_daily_calories(user)

    db.session.commit()

    # Connexion directe après l'inscription (pas de 2FA)
    session["user_id"] = user.id
    return jsonify({"message": "Inscription réussie", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Identifiants invalides"}), 401

    session["user_id"] = user.id
    return jsonify({"message": "Connexion réussie", "user": user.to_dict()}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Déconnexion réussie"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Non authentifié"}), 401
    user = db.session.get(User, user_id)
    return jsonify({"user": user.to_dict()}), 200
