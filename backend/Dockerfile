FROM python:3.11-slim

WORKDIR /app

# Installer seulement le strict nécessaire
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Installer dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# 🔐 sécurité : user non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "wikimetron.api.main:app", "--host", "0.0.0.0", "--port", "8000"]