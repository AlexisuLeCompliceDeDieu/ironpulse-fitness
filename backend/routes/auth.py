from flask import Blueprint, request, jsonify, session
from models import db, User
from services.mailer import send_email
import logging, os, secrets, time

auth_bp = Blueprint("auth", __name__)

# Anti-spam : un email de réinitialisation max toutes les 2 minutes
RESET_COOLDOWN_SECONDS = 120
_reset_cooldown = {}


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


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Génère un nouveau mot de passe et l'envoie par email.

    Le mot de passe n'est modifié qu'après un envoi réussi, pour ne jamais
    bloquer un utilisateur dont l'email ne partirait pas.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Email invalide"}), 400

    user = User.query.filter(db.func.lower(User.email) == email).first()

    # Même réponse que le compte existe ou non (on ne révèle pas les emails inscrits)
    if not user:
        return jsonify({"message": "Si un compte existe pour cet email, un nouveau mot de passe vient d'être envoyé."}), 200

    now = time.time()
    if now - _reset_cooldown.get(email, 0) < RESET_COOLDOWN_SECONDS:
        return jsonify({"message": "Une demande a déjà été faite récemment. Réessayez dans quelques minutes."}), 429

    new_password = secrets.token_urlsafe(9)
    debug = os.environ.get("MAIL_DEBUG", "false").lower() == "true"

    ok = send_email(
        user.email,
        "IRONPULSE — Réinitialisation de votre mot de passe",
        (
            f"Bonjour {user.username},\n\n"
            "Vous (ou quelqu'un utilisant cet email) avez demandé la réinitialisation "
            "de votre mot de passe IRONPULSE.\n\n"
            f"Voici votre nouveau mot de passe : {new_password}\n\n"
            "Connectez-vous avec ce mot de passe, puis changez-le depuis votre profil "
            "(Profil > Changer mon mot de passe).\n\n"
            "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.\n\n"
            "— L'équipe IRONPULSE"
        ),
    )

    if not ok:
        if debug:
            # Mode développement : on applique quand même le nouveau mot de passe
            # et on le renvoie au client (SMTP non configuré)
            user.set_password(new_password)
            db.session.commit()
            _reset_cooldown[email] = now
            return jsonify({
                "message": "Nouveau mot de passe généré (mode debug : SMTP non configuré).",
                "debug_password": new_password,
            }), 200
        return jsonify({"error": "Impossible d'envoyer l'email. Contactez l'administrateur."}), 500

    user.set_password(new_password)
    db.session.commit()
    _reset_cooldown[email] = now
    return jsonify({"message": "Un nouveau mot de passe a été envoyé par email."}), 200


@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    """Change le mot de passe d'un utilisateur connecté (mot de passe actuel requis)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Non authentifié"}), 401

    user = db.session.get(User, user_id)
    data = request.get_json(silent=True) or {}
    current = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not user or not user.check_password(current):
        return jsonify({"error": "Mot de passe actuel incorrect"}), 400
    if len(new_password) < 8:
        return jsonify({"error": "Le nouveau mot de passe doit contenir au moins 8 caractères"}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({"message": "Mot de passe modifié"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Non authentifié"}), 401
    user = db.session.get(User, user_id)
    return jsonify({"user": user.to_dict()}), 200
