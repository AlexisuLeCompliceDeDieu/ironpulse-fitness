from flask import Flask
from flask_cors import CORS
from config import Config
from models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, supports_credentials=True)

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
        seed_exercises()
        seed_foods()

    return app


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
