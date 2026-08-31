"""Sauvegardes automatiques de la base de données.

Au démarrage de l'application, une copie de la base est créée dans le dossier
`backups/` si elle n'existe pas déjà pour le jour courant. Cela répond à
l'exigence du cahier des charges sur la conservation et les sauvegardes des
données (RGPD / robustesse).
"""

import os
import shutil
from datetime import date

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backups")


def run_backup():
    """Crée une sauvegarde quotidienne de la base SQLite si nécessaire."""
    from flask import current_app
    import sqlite3

    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri.startswith("sqlite:///"):
        return "skipped"

    db_path = db_uri.replace("sqlite:///", "", 1)
    db_path = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", db_path
    ) if not os.path.isabs(db_path) else db_path)

    if not os.path.exists(db_path):
        return "no-db"

    os.makedirs(BACKUP_DIR, exist_ok=True)
    today = date.today().isoformat()
    backup_path = os.path.join(BACKUP_DIR, f"backup-{today}.db")

    if os.path.exists(backup_path):
        return "exists"

    try:
        conn = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path)
        conn.backup(dest)
        dest.close()
        conn.close()
        return "created"
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning("Sauvegarde impossible : %s", exc)
        return "error"
