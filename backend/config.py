import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Origen(s) du frontend autorisée(s) en CORS (ex: http://localhost:5173, https://monfront.vercel.app)
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if o.strip()
]

# En production, défini à "https://monsite.vercel.app"
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fitness-agent-secret-change-in-prod")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = "filesystem"

    # Cookies de session pour le multi-origine en production
    SESSION_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
    SESSION_COOKIE_SECURE = COOKIE_SECURE
    SESSION_COOKIE_HTTPONLY = True
