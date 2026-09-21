FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# En production, définir DATABASE_URL (ex: postgresql://...) et CORS_ORIGINS.
# gunicorn en mode gthread (threads) : indispensable pour le streaming du chat IA
# sans bloquer les autres requêtes.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--threads", "8", "--timeout", "120", "app:create_app()"]
