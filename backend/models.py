from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    goal = db.Column(db.String(20), default="prise_masse")  # prise_masse, perte_poids, force, endurance
    level = db.Column(db.String(20), default="debutant")    # debutant, intermediaire, avance
    weight = db.Column(db.Float, default=70.0)
    target_weight = db.Column(db.Float, default=75.0)
    height = db.Column(db.Float, default=175.0)
    age = db.Column(db.Integer, default=25)
    daily_calories = db.Column(db.Integer, default=2500)
    available_equipment = db.Column(db.Text, default="[]")  # JSON list of equipment names
    dietary_preferences = db.Column(db.Text, default="[]")  # JSON list: vegetarien, vegan, sans_lactose, sans_gluten, sans_noix

    programs = db.relationship("TrainingProgram", backref="user", lazy=True)
    sessions = db.relationship("Session", backref="user", lazy=True)
    weight_entries = db.relationship("WeightEntry", backref="user", lazy=True)

    def equipment_list(self):
        import json
        try:
            return json.loads(self.available_equipment or "[]")
        except (ValueError, TypeError):
            return []

    def preferences_list(self):
        import json
        try:
            return json.loads(self.dietary_preferences or "[]")
        except (ValueError, TypeError):
            return []

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "goal": self.goal,
            "level": self.level,
            "weight": self.weight,
            "target_weight": self.target_weight,
            "height": self.height,
            "age": self.age,
            "daily_calories": self.daily_calories,
            "available_equipment": self.equipment_list(),
            "dietary_preferences": self.preferences_list(),
            "created_at": self.created_at.isoformat(),
        }


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)     # dos, pectoraux, jambes, epaules, bras, core
    muscle_group = db.Column(db.String(50), nullable=False)  # grand_dorsal, biceps, quadriceps, etc.
    equipment_needed = db.Column(db.String(100), default="barre")
    description = db.Column(db.Text, default="")
    is_compound = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "muscle_group": self.muscle_group,
            "equipment_needed": self.equipment_needed,
            "description": self.description,
            "is_compound": self.is_compound,
        }


class TrainingProgram(db.Model):
    __tablename__ = "training_programs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    goal = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)

    days = db.relationship("ProgramDay", backref="program", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "goal": self.goal,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": self.is_active,
            "days": [d.to_dict() for d in self.days],
        }


class ProgramDay(db.Model):
    __tablename__ = "program_days"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("training_programs.id"), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)  # 1-4 ou 1-5 selon le split
    name = db.Column(db.String(50), nullable=False)     # Push, Pull, Jambes, etc.

    exercises = db.relationship("ProgramExercise", backref="day", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "day_number": self.day_number,
            "name": self.name,
            "exercises": [e.to_dict() for e in self.exercises],
        }


class ProgramExercise(db.Model):
    __tablename__ = "program_exercises"

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("program_days.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    sets = db.Column(db.Integer, default=3)
    reps = db.Column(db.Integer, default=10)
    rest_seconds = db.Column(db.Integer, default=90)
    target_weight = db.Column(db.Float, default=0.0)
    order = db.Column(db.Integer, default=0)

    exercise = db.relationship("Exercise", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "exercise": self.exercise.to_dict() if self.exercise else None,
            "sets": self.sets,
            "reps": self.reps,
            "rest_seconds": self.rest_seconds,
            "target_weight": self.target_weight,
            "order": self.order,
        }


class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    program_day_id = db.Column(db.Integer, db.ForeignKey("program_days.id"), nullable=True)
    date = db.Column(db.Date, default=date.today)
    completed = db.Column(db.Boolean, default=False)
    feeling = db.Column(db.Integer, default=3)  # 1-5
    notes = db.Column(db.Text, default="")

    sets = db.relationship("SessionSet", backref="session", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "program_day_id": self.program_day_id,
            "date": self.date.isoformat(),
            "completed": self.completed,
            "feeling": self.feeling,
            "notes": self.notes,
            "sets": [s.to_dict() for s in self.sets],
        }


class SessionSet(db.Model):
    __tablename__ = "session_sets"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    set_number = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, default=0.0)
    reps = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=True)

    exercise = db.relationship("Exercise", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise.name if self.exercise else None,
            "set_number": self.set_number,
            "weight": self.weight,
            "reps": self.reps,
            "completed": self.completed,
        }


class WeightEntry(db.Model):
    __tablename__ = "weight_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)

    def to_dict(self):
        return {
            "id": self.id,
            "weight": self.weight,
            "date": self.date.isoformat(),
        }


class Food(db.Model):
    __tablename__ = "foods"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), default="autre")  # proteine, glucide, lipide, legume, fruit, autre
    kcal = db.Column(db.Float, default=0)      # par 100g
    protein = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    tags = db.Column(db.Text, default="[]")  # JSON list: viande, poisson, lactier, gluten, noix, oeuf

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "kcal": self.kcal,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
            "tags": self.tags_list(),
        }

    def tags_list(self):
        import json
        try:
            return json.loads(self.tags or "[]")
        except (ValueError, TypeError):
            return []


class MealPlan(db.Model):
    __tablename__ = "meal_plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    num_days = db.Column(db.Integer, default=7)
    target_calories = db.Column(db.Integer, default=2500)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    meals = db.relationship("Meal", backref="plan", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "num_days": self.num_days,
            "target_calories": self.target_calories,
            "created_at": self.created_at.isoformat(),
            "meals": [m.to_dict() for m in self.meals],
        }


class Meal(db.Model):
    __tablename__ = "meals"

    id = db.Column(db.Integer, primary_key=True)
    meal_plan_id = db.Column(db.Integer, db.ForeignKey("meal_plans.id"), nullable=False)
    day = db.Column(db.Integer, nullable=False)       # 1..num_days
    meal_type = db.Column(db.String(30), nullable=False)  # Petit-déjeuner, Déjeuner, Collation, Dîner
    name = db.Column(db.String(150), nullable=False)

    items = db.relationship("MealItem", backref="meal", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        items = self.items
        total = {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0}
        for it in items:
            food = it.food
            factor = it.quantity / 100.0
            total["kcal"] += food.kcal * factor
            total["protein"] += food.protein * factor
            total["carbs"] += food.carbs * factor
            total["fat"] += food.fat * factor
        return {
            "id": self.id,
            "day": self.day,
            "meal_type": self.meal_type,
            "name": self.name,
            "items": [it.to_dict() for it in items],
            "totals": {k: round(v, 1) for k, v in total.items()},
        }


class MealItem(db.Model):
    __tablename__ = "meal_items"

    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey("meals.id"), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey("foods.id"), nullable=False)
    quantity = db.Column(db.Float, default=0)  # en grammes

    food = db.relationship("Food", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "food_id": self.food_id,
            "food_name": self.food.name if self.food else None,
            "quantity": self.quantity,
        }


class ShoppingList(db.Model):
    __tablename__ = "shopping_lists"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    meal_plan_id = db.Column(db.Integer, db.ForeignKey("meal_plans.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.Column(db.Text, default="[]")  # JSON: [{name, qty_grams}]

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "meal_plan_id": self.meal_plan_id,
            "created_at": self.created_at.isoformat(),
            "items": json.loads(self.items),
        }
