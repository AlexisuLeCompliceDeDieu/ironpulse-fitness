import os
import sys

# Configurer la base en mémoire AVANT l'import des modules de l'app
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db


@pytest.fixture()
def app():
    app = create_app()
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _register(client, username="user1", email="user1@test.fr", password="secret123"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )


@pytest.fixture()
def auth_client(client):
    """Client connecté avec un utilisateur frais."""
    _register(client)
    return client


@pytest.fixture()
def registered_client(client):
    """Client sans session, avec l'utilisateur déjà créé."""
    _register(client)
    return client
