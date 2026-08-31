from flask import Flask
from flask_cors import CORS
from config import Config, CORS_ORIGINS
from models import db


def create_app():
    app = Flask(__name__)
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

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(profile_bp, url_prefix="/api/profile")
        app.register_blueprint(training_bp, url_prefix="/api/training")
        app.register_blueprint(exercises_bp, url_prefix="/api/exercises")
        app.register_blueprint(tracking_bp, url_prefix="/api/tracking")
        app.register_blueprint(progress_bp, url_prefix="/api/progress")
        app.register_blueprint(nutrition_bp, url_prefix="/api/nutrition")

        db.create_all()
        _migrate_columns()
        seed_exercises()
        seed_foods()
        _run_backup()

    return app


def _run_backup():
    from services import backup
    backup.run_backup()


def _migrate_columns():
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    columns_u = [c["name"] for c in inspector.get_columns("users")]
    if "dietary_preferences" not in columns_u:
        db.session.execute(text('ALTER TABLE users ADD COLUMN dietary_preferences TEXT DEFAULT "[]"'))
        db.session.commit()
    columns_f = [c["name"] for c in inspector.get_columns("foods")]
    if "tags" not in columns_f:
        db.session.execute(text('ALTER TABLE foods ADD COLUMN tags TEXT DEFAULT "[]"'))
        db.session.commit()


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

    if Food.query.count() > 0:
        data_path = os.path.join(os.path.dirname(__file__), "data", "foods.json")
        with open(data_path, "r", encoding="utf-8") as f:
            foods = json.load(f)
        existing = {f.name: f for f in Food.query.all()}
        for fd in foods:
            if fd["name"] in existing:
                obj = existing[fd["name"]]
                if not getattr(obj, "tags", None):
                    obj.tags = fd.get("tags", "[]")
        db.session.commit()
        return

    data_path = os.path.join(os.path.dirname(__file__), "data", "foods.json")
    with open(data_path, "r", encoding="utf-8") as f:
        foods = json.load(f)

    for food in foods:
        db.session.add(Food(**food))
    db.session.commit()
    print(f"Loaded {len(foods)} foods into database.")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
