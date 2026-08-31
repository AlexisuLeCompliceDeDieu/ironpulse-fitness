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

## Préparation au déploiement

### Variables d'environnement (backend)

Copier `backend/.env.example` en `.env` et adapter les valeurs :
- `SECRET_KEY` : clé secrète longue et aléatoire
- `CORS_ORIGINS` : origines du frontend (ex: `https://monfront.vercel.app,http://localhost:5173`)
- `DATABASE_URL` : `sqlite:////app/database.db` en SQLite, ou une URL PostgreSQL en production
- `SESSION_COOKIE_SAMESITE` / `COOKIE_SECURE` : sécuriser les cookies de session

### Docker

```bash
# Backend
cd backend
docker build -t fitness-backend .
docker run -p 8000:8000 \
  -e SECRET_KEY=... \
  -e CORS_ORIGINS=https://monfront.vercel.app \
  -e DATABASE_URL=postgresql://user:pass@host:5432/fitnessdb \
  fitness-backend

# Frontend (construire + servir via Nginx)
cd frontend
docker build -t fitness-frontend .
docker run -p 8080:80 fitness-frontend
```

### Hébergement recommandé
- **Frontend** : Vercel ou Netlify (build `npm run build`, dossier `dist`)
- **Backend** : Render ou Railway (commande `gunicorn --bind 0.0.0.0:$PORT app:create_app()`)
- **Base de données** : PostgreSQL managé (Render, Railway ou Neon)
- Après hébergement, éditer `frontend/nginx.conf` (ou la config du frontend) pour pointer `/api/` vers l'URL réelle du backend, puis définir `CORS_ORIGINS` côté backend sur l'URL du frontend.

## Notes

- Base de données SQLite générée automatiquement au premier lancement (`backend/database.db`)
- 40 exercices et 14 aliments prédéfinis chargés automatiquement
- En production, préférer PostgreSQL en définissant `DATABASE_URL`
