from flask import Flask, send_from_directory
from flask_cors import CORS
from config import Config, CORS_ORIGINS
from models import db


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    CORS(
        app,
        supports_credentials=True,
        origins=CORS_ORIGINS,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    db.init_app(app)

    with app.app_context():
        from routes.auth import auth_bp
        from routes.profile import profile_bp
        from routes.training import training_bp
        from routes.exercises import exercises_bp
        from routes.tracking import tracking_bp
        from routes.progress import progress_bp
        from routes.nutrition import nutrition_bp
        from routes.social import social_bp
        from routes.machines import machines_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(profile_bp, url_prefix="/api/profile")
        app.register_blueprint(training_bp, url_prefix="/api/training")
        app.register_blueprint(exercises_bp, url_prefix="/api/exercises")
        app.register_blueprint(tracking_bp, url_prefix="/api/tracking")
        app.register_blueprint(progress_bp, url_prefix="/api/progress")
        app.register_blueprint(nutrition_bp, url_prefix="/api/nutrition")
        app.register_blueprint(social_bp, url_prefix="/api/social")
        app.register_blueprint(machines_bp, url_prefix="/api/machines")

        db.create_all()
        _migrate_columns()
        _ensure_machine_image_text()
        _ensure_calories_auto()
        seed_exercises()
        seed_foods()
        seed_machines()
        _run_backup()

        # Sert le frontend React buildé (si présent) à la racine.
        # Active le fallback SPA afin que les routes type /login, /friends...
        # soient résolues par BrowserRouter de React (mode production Render).
        _register_frontend(app)
        _register_diag(app)

    return app


def _register_diag(app):
    """Endpoint public d'aide au diagnostic (sans secrets), pour vérifier à distance
    que la base a bien la colonne `calories_auto` (cause des 500 sur /login et /register)."""
    import traceback as _tb
    from sqlalchemy import inspect
    from models import User

    @app.route("/healthz/db", methods=["GET"])
    def _healthz_db():
        from sqlalchemy import text as _t
        is_pg = db.engine.url.drivername.startswith("postgres")
        schema_info = {}
        try:
            inspector = inspect(db.engine)
            cols_users = [c["name"] for c in inspector.get_columns("users")]
            if is_pg:
                with db.engine.connect() as conn:
                    cur_schema = conn.execute(_t("SELECT current_schema()")).scalar()
                    search_path = conn.execute(_t("SHOW search_path")).scalar()
                    in_cur = conn.execute(
                        _t("SELECT column_name FROM information_schema.columns WHERE table_schema=:s AND table_name='users' AND column_name='calories_auto'"),
                        {"s": cur_schema},
                    ).first() is not None
                    in_pub = conn.execute(
                        _t("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='calories_auto'"),
                    ).first() is not None
                    pub_cols = [r[0] for r in conn.execute(
                        _t("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users' ORDER BY ordinal_position")
                    )]
                schema_info = {
                    "current_schema": cur_schema,
                    "search_path": search_path,
                    "calories_auto_in_current_schema": in_cur,
                    "calories_auto_in_public": in_pub,
                    "public_users_columns": pub_cols,
                }
            return {
                "dialect": db.engine.url.drivername,
                "has_calories_auto": "calories_auto" in cols_users,
                "user_columns_divergence": cols_users,
                **schema_info,
            }
        except Exception as e:
            return {"error": repr(e)}, 500

    @app.route("/healthz/probe", methods=["GET"])
    def _healthz_probe():
        """Rejoue le chemin exact de /login pour capturer l'exception réelle."""
        try:
            user = User.query.filter_by(email="__probe_does_not_exist__@nowhere").first()
            ok = bool(user)
            return {"login_query_ok": True, "found": ok}
        except Exception as e:
            fmt = _tb.format_exc()
            # isole le message d'erreur principal (ligne de l'exception)
            headline = [l for l in fmt.splitlines() if "Error" in l or "error" in l or l.startswith("sqlalchemy")]
            return {
                "login_query_ok": False,
                "exc_type": type(e).__name__,
                "message": str(e),
                "headline": headline[-3:],
            }, 500


def _register_frontend(app):
    """Sert le build Vite (frontend/dist) à la racine de l'application.

    En mode production (déploiement Render), on regroupe le frontend et le
    backend dans une seule application HTTP : plus de souci de CORS et une
    seule instance à garder éveillée.
    """
    import os
    from flask import request

    dist = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist"
    )
    if not os.path.isdir(dist):
        return  # pas de build frontend : on ne sert que l'API

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def _spa(path):
        # Ne jamais faire tomber les requêtes API dans le fallback SPA
        if path.startswith("api/"):
            from flask import jsonify
            return jsonify({"error": "Not found"}), 404
        full = os.path.join(dist, path)
        if path and os.path.isfile(full):
            return send_from_directory(dist, path)
        return send_from_directory(dist, "index.html")


def _run_backup():
    from services import backup
    backup.run_backup()


def _migrate_columns():
    """Migrations manuelles destinées au développement local (SQLite).

    Sur PostgreSQL/Supabase, `db.create_all()` crée directement le schéma
    complet à jour, donc aucune ALTER TABLE n'est nécessaire.
    """
    from sqlalchemy import inspect, text

    # Ne migre que les bases locales SQLite (développement)
    if not db.engine.url.drivername.startswith("sqlite"):
        return

    inspector = inspect(db.engine)
    columns_u = [c["name"] for c in inspector.get_columns("users")]
    if "dietary_preferences" not in columns_u:
        db.session.execute(text('ALTER TABLE users ADD COLUMN dietary_preferences TEXT'))
        db.session.commit()
    if "split_type" not in columns_u:
        db.session.execute(text("ALTER TABLE users ADD COLUMN split_type VARCHAR(30) DEFAULT NULL"))
        db.session.commit()
    if "sessions_per_week" not in columns_u:
        db.session.execute(text("ALTER TABLE users ADD COLUMN sessions_per_week INTEGER DEFAULT NULL"))
        db.session.commit()
    db.session.commit()
    columns_f = [c["name"] for c in inspector.get_columns("foods")]
    if "tags" not in columns_f:
        db.session.execute(text('ALTER TABLE foods ADD COLUMN tags TEXT'))
        db.session.commit()

    columns_ss = [c["name"] for c in inspector.get_columns("session_sets")]
    if "difficulty" not in columns_ss:
        db.session.execute(text('ALTER TABLE session_sets ADD COLUMN difficulty VARCHAR(20) DEFAULT ""'))
        db.session.commit()

    # tables sûres (créées par db.create_all sur les bases neuves)
    try:
        columns_s = [c["name"] for c in inspector.get_columns("sessions")]
        if "flagged" not in columns_s:
            db.session.execute(text("ALTER TABLE sessions ADD COLUMN flagged BOOLEAN DEFAULT 0"))
            db.session.commit()
    except Exception:
        pass

    # Colonne status sur friendships : les amitiés existantes deviennent définitives,
    # les nouvelles demandes démarrent en "pending" (à valider par l'autre).
    cols_fr = [c["name"] for c in inspector.get_columns("friendships")]
    if "status" not in cols_fr:
        db.session.execute(
            text("ALTER TABLE friendships ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'")
        )
        db.session.commit()
        db.session.execute(text("UPDATE friendships SET status = 'accepted'"))
        db.session.commit()


def _ensure_machine_image_text():
    """Élargit `machines.image_url` en TEXT pour stocker les data-URI SVG.

    Les icônes SVG « machine seule » sont encodées en base64 et dépassent
    largement le VARCHAR(200) d'origine → PostgreSQL doit basculer la colonne
    en TEXT (idempotent, ré-exécuté à chaque démarrage).
    """
    import sys
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(db.engine)
        col_type = None
        for c in inspector.get_columns("machines"):
            if c["name"] == "image_url":
                col_type = str(c["type"].__class__.__name__)
        if col_type in ("Text",):
            return
        db.session.execute(text("ALTER TABLE machines ALTER COLUMN image_url TYPE TEXT"))
        db.session.commit()
        print("machines.image_url widened to TEXT.", file=sys.stderr)
    except Exception as e:  # pragma: no cover - sécurité de démarrage
        print(f"machines.image_url migration FAILED: {e}", file=sys.stderr)
        try:
            db.session.rollback()
        except Exception:
            pass


def _ensure_calories_auto():
    """Ajoute la colonne `calories_auto` sur toutes les bases (Postgres inclus).

    `db.create_all()` ne modifie pas les tables existantes : pour les bases fixes
    (ex. Supabase) il faut un ALTER TABLE idempotent ré-exécuté à chaque démarrage.

    On cible explicitement le schéma `public` (le pooler Supabase peut exécuter les
    requêtes non qualifiées dans un autre schéma), on vérifie ensuite par une vraie
    requête `information_schema`, et on retente en cas de latence du DDL. On
    journalise en stderr pour pouvoir diagnostiquer via les logs Render.
    """
    import sys
    import time
    from sqlalchemy import inspect, text

    schemas = ["public"]
    if db.engine.url.drivername.startswith("sqlite"):
        schemas = None  # pas de notion de schéma sur SQLite

    def column_in_public():
        with db.engine.connect() as conn:
            cur_schema = conn.execute(text("SELECT current_schema()")).scalar()
            if schemas is None:
                cols = [c["name"] for c in inspect(db.engine).get_columns("users")]
                return "calories_auto" in cols
            # on vérifie dans le schéma réel de la table (public attendu)
            row = conn.execute(
                text(
                    "SELECT table_schema FROM information_schema.columns "
                    "WHERE column_name='calories_auto' AND table_name='users' "
                    "ORDER BY (table_schema = current_schema()) DESC LIMIT 1"
                )
            ).first()
            _ = cur_schema
            return row is not None

    stmt = "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS calories_auto BOOLEAN DEFAULT TRUE"
    try:
        if column_in_public():
            print("calories_auto column already present.", file=sys.stderr)
            return
        # Le pooler Supabase (transaction mode) peut échouer à persister du DDL
        # dans `db.session` : on passe par une connexion brute en AUTOCOMMIT.
        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(stmt))
            time.sleep(0.5)
        if column_in_public():
            print("calories_auto column added via AUTOCOMMIT ALTER.", file=sys.stderr)
            return
        # dernier recours : via la session (bases non-pooler, ex. SQLite local)
        db.session.execute(text(stmt))
        db.session.commit()
        if column_in_public():
            print("calories_auto column added via session ALTER.", file=sys.stderr)
            return
        print("calories_auto ALTER done but column not visible yet; will retry next boot.", file=sys.stderr)
    except Exception as e:  # pragma: no cover - sécurité de démarrage
        print(f"calories_auto migration FAILED: {repr(e)}", file=sys.stderr)
        try:
            db.session.rollback()
        except Exception:
            pass


def seed_machines():
    from models import Machine
    import json
    import os

    data_path = os.path.join(os.path.dirname(__file__), "data", "machines.json")
    with open(data_path, "r", encoding="utf-8") as f:
        machines = json.load(f)

    existing = {m.code: m for m in Machine.query.all()}
    added = 0
    updated = 0
    for m in machines:
        row = existing.get(m["code"])
        if row is None:
            db.session.add(Machine(**m))
            added += 1
        else:
            changed = False
            for field in ("brand", "model", "category", "location", "image_url", "setup_tips"):
                if getattr(row, field) != m.get(field):
                    setattr(row, field, m.get(field))
                    changed = True
            if changed:
                updated += 1
    if added or updated:
        db.session.commit()
        print(f"Loaded {added} new machines, updated {updated} existing.")


def seed_exercises():
    from models import Exercise
    import json
    import os

    if Exercise.query.count() > 0:
        return

    data_path = os.path.join(os.path.dirname(__file__), "data", "exercises.json")
    with open(data_path, "r", encoding="utf-8") as f:
        exercises = json.load(f)

    for ex in exercises:
        db.session.add(Exercise(**ex))
    db.session.commit()
    print(f"Loaded {len(exercises)} exercises into database.")


def seed_foods():
    from models import Food
    import json
    import os

    data_path = os.path.join(os.path.dirname(__file__), "data", "foods.json")
    with open(data_path, "r", encoding="utf-8") as f:
        foods = json.load(f)

    if Food.query.count() > 0:
        # Upsert : ajoute les nouveaux aliments manquants, met à jour les tags des existants
        existing = {f.name: f for f in Food.query.all()}
        added = 0
        for fd in foods:
            if fd["name"] in existing:
                obj = existing[fd["name"]]
                if getattr(obj, "tags", None) != fd.get("tags", "[]") and (not getattr(obj, "tags", None) or fd.get("tags")):
                    obj.tags = fd.get("tags", "[]")
            else:
                db.session.add(Food(**fd))
                added += 1
        db.session.commit()
        if added:
            print(f"Added {added} new foods to database.")
        return

    for food in foods:
        db.session.add(Food(**food))
    db.session.commit()
    print(f"Loaded {len(foods)} foods into database.")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
