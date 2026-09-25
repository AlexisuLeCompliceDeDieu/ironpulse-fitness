import logging

from flask import Blueprint, jsonify, session, request
from datetime import date, timedelta
from models import (
    TrainingProgram, Session, SessionSet, Exercise, db,
)
from services import program_generator, adaptation, ai_program

training_bp = Blueprint("training", __name__)

logger = logging.getLogger(__name__)


def _echec_generation(e):
    """500 lisible : le frontend affiche un message, le serveur garde la trace.

    Sans cela, une exception non gérée renvoie la page d'erreur HTML de Flask et
    l'interface affiche un « Erreur » vide.
    """
    logger.exception("Échec de la génération du programme : %r", e)
    return jsonify({
        "error": "La génération du programme a échoué.",
        "detail": f"{type(e).__name__}: {str(e)[:200]}",
        "programme_conserve": True,
    }), 500


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    from models import User
    return db.session.get(User, user_id)


@training_bp.route("/presets", methods=["GET"])
def presets():
    return jsonify({"presets": program_generator.get_presets()}), 200


def _contexte_generation(data):
    """Normalise les paramètres de génération (split, séances, source IA, consigne)."""
    explicit_goal = bool(data.get("goal"))
    goal = data.get("goal")
    split_type = data.get("split_type")
    # Un split "par objectif" choisi en page : on applique le split par défaut
    # de l'objectif, sans laisser le split du profil l'écraser.
    if not split_type and explicit_goal:
        split_type = goal
    days_per_week = data.get("days_per_week")
    if days_per_week:
        days_per_week = int(days_per_week)
    source = data.get("source") or "auto"
    if source not in ("auto", "ia", "algorithme"):
        source = "auto"
    consigne = (data.get("consigne") or "").strip() or None
    return {
        "goal": goal,
        "split_type": split_type,
        "days_per_week": days_per_week,
        "source": source,
        "consigne": consigne,
    }


@training_bp.route("/program/generate", methods=["POST"])
def generate():
    """Génère un programme : par IA si possible, sinon par l'algorithme.

    Paramètres : goal, split_type, days_per_week, source (auto|ia|algorithme),
    consigne (ex. « plus de jambes », « séances plus courtes »).
    """
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    ctx = _contexte_generation(request.get_json(silent=True) or {})
    try:
        program, meta = ai_program.generer_programme(
            user,
            user.equipment_list(),
            goal=ctx["goal"],
            split_type=ctx["split_type"],
            days_per_week=ctx["days_per_week"],
            consigne=ctx["consigne"],
            source=ctx["source"],
        )
    except ai_program.ErreurIAProgram as e:
        return jsonify({
            "error": "Génération IA indisponible pour le moment.",
            "raison": e.raison,
            "raison_fr": ai_program.raison_lisible(e.raison),
            "reinitialiser_ia": True,
            "programme_algorithme_disponible": True,
        }), 503
    except Exception as e:  # noqa: BLE001
        return _echec_generation(e)

    message = "Programme généré par l'IA 🧠" if meta["source"] == "ia" else "Programme généré ⚙️"
    return jsonify({"message": message, "program": program.to_dict(), "meta": meta}), 201


def _split_du_programme(program):
    """Retrouve le split d'un programme existant d'après les noms de ses jours.

    Permet de régénérer à l'identique (même structure) même si le profil a changé
    depuis la génération initiale.
    """
    noms = [d.name.strip().lower() for d in sorted(program.days, key=lambda d: d.day_number)]
    if not noms:
        return None
    for key, spec in list(program_generator.SPLIT_TEMPLATES.items()) + list(program_generator.SPLITS.items()):
        base = [d["name"].strip().lower() for d in spec["days"]]
        # Les jours peuvent être recyclés (« Push 2 ») : on compare au gabarit cyclé.
        if all(noms[i].startswith(base[i % len(base)]) for i in range(len(noms))):
            return key
    return None


@training_bp.route("/program/regenerate", methods=["POST"])
def regenerate():
    """Régénère le programme actif en variant la sélection IA.

    L'historique des séances réalisées est conservé : seul le programme actif est
    remplacé, les séances passées restent rattachées à leur programme d'origine.
    """
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    data = request.get_json(silent=True) or {}
    actif = TrainingProgram.query.filter_by(user_id=user.id, is_active=True).order_by(TrainingProgram.id.desc()).first()
    if not actif:
        return jsonify({"error": "Aucun programme actif à régénérer"}), 404

    ctx = _contexte_generation({
        "goal": data.get("goal") or actif.goal,
        "split_type": data.get("split_type") or _split_du_programme(actif) or user.split_type,
        "days_per_week": data.get("days_per_week") or len(actif.days),
        "source": data.get("source") or "auto",
        "consigne": data.get("consigne"),
    })
    try:
        program, meta = ai_program.generer_programme(
            user,
            user.equipment_list(),
            goal=ctx["goal"],
            split_type=ctx["split_type"],
            days_per_week=ctx["days_per_week"],
            consigne=ctx["consigne"],
            source=ctx["source"],
        )
    except ai_program.ErreurIAProgram as e:
        return jsonify({
            "error": "Régénération IA indisponible pour le moment.",
            "raison": e.raison,
            "raison_fr": ai_program.raison_lisible(e.raison),
            "reinitialiser_ia": True,
            "programme_actif_conserve": True,
        }), 503
    except Exception as e:  # noqa: BLE001
        return _echec_generation(e)

    message = "Programme régénéré par l'IA 🧠" if meta["source"] == "ia" else "Programme régénéré ⚙️"
    return jsonify({"message": message, "program": program.to_dict(), "meta": meta}), 201


@training_bp.route("/program/current", methods=["GET"])
def current_program():
    user = current_user()
    if not user:
        return jsonify({"error": "Non authentifié"}), 401

    program = TrainingProgram.query.filter_by(user_id=user.id, is_active=True).order_by(TrainingProgram.id.desc()).first()
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
    exercise = db.session.get(Exercise, exercise_id)
    if not exercise:
        return jsonify({"error": "Exercice introuvable"}), 404

    alternative = adaptation.get_alternative_for(exercise, available_equipment)
    if not alternative:
        return jsonify({"error": "Aucune alternative trouvée"}), 404
    return jsonify({"alternative": alternative.to_dict()}), 200
