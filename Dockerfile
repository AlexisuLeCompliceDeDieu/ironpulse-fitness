# ========= Étape 1 : build du frontend React (Node) =========
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ========= Étape 2 : image finale (Python + frontend buildé) =========
FROM python:3.12-slim
WORKDIR /app

# Dépendances système
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Backend
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Code backend
COPY backend/ ./backend/

# Frontend buildé (servi par Flask à la racine)
COPY --from=frontend-build /build/dist ./frontend/dist

# Port exposé
EXPOSE 10000

# Démarrage gunicorn sur le port fourni par l'environnement (Render injecte PORT)
CMD gunicorn --chdir /app/backend wsgi:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120
