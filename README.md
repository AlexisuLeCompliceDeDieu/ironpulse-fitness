# IA Fitness

Agent IA d'accompagnement fitness : nutrition, entraînement et suivi de progression.

## Stack technique

- **Backend** : Python Flask + SQLAlchemy + SQLite
- **Frontend** : React + Vite + Chart.js
- **IA** : Logique locale / prompt engineering (génération de programmes et menus)

## Prérequis

- Python 3.10+
- Node.js 18+ (pour le frontend)

## Démarrage

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Le serveur tourne sur `http://localhost:5000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Le site est accessible sur `http://localhost:5173`. Le proxy Vite redirige les appels `/api` vers le backend Flask.

## Fonctionnalités

- **Authentification** : inscription, connexion, déconnexion (sessions Flask + bcrypt)
- **Profil** : objectif (prise de masse, perte de poids, force, endurance), niveau, poids, taille, calories
- **Entraînement** : génération d'un programme mensuel selon l'objectif et le niveau
- **Suivi de séances** : saisie des charges, répétitions, ressenti, historique
- **Nutrition** : planification de menus et liste de courses selon l'objectif calorique
- **Progression** : graphiques d'évolution du poids et des performances par exercice
- **Adaptation** : remplacement d'équipement par des exercices alternatifs

## API principale (backend)

| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/api/auth/register` | Inscription |
| POST | `/api/auth/login` | Connexion |
| GET | `/api/auth/me` | Utilisateur courant |
| PUT | `/api/profile/` | Mise à jour du profil |
| POST | `/api/profile/weight` | Ajouter une entrée de poids |
| GET | `/api/exercises/` | Liste des exercices |
| POST | `/api/training/program/generate` | Générer un programme |
| GET | `/api/training/program/current` | Programme actif |
| POST | `/api/tracking/sessions` | Enregistrer une séance |
| GET | `/api/tracking/sessions` | Historique des séances |
| GET | `/api/progress/weights` | Historique du poids |
| GET | `/api/progress/exercises/:id` | Progression d'un exercice |

## Notes

- Base de données SQLite générée automatiquement au premier lancement (`backend/database.db`)
- 40 exercices prédéfinis chargés automatiquement depuis `backend/data/exercises.json`
- Migrer vers PostgreSQL : modifier `SQLALCHEMY_DATABASE_URI` dans `backend/config.py`
