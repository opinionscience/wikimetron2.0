#!/bin/bash
# Script de démarrage développement

echo "🚀 Démarrage de Wikimetron en mode développement..."

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

# Lancer les services
docker-compose up -d postgres redis

echo "⏳ Attente du démarrage des services..."
sleep 5

# Démarrer le backend
echo "🐍 Démarrage du backend..."
cd backend && python -m uvicorn wikimetron.api.main:app --reload --host 0.0.0.0 --port 8000 &

# Démarrer le frontend
echo "⚛️ Démarrage du frontend..."
cd frontend && npm start &

echo "✅ Wikimetron démarré!"
echo "📱 Frontend: http://localhost:8300"
echo "🔧 Backend: http://localhost:8200"
echo "📚 API Docs: http://localhost:8200/docs"

wait
