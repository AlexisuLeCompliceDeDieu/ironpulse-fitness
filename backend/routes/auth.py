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
    db.session.add(user)
    db.session.commit()

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
    user = User.query.get(user_id)
    return jsonify({"user": user.to_dict()}), 200
