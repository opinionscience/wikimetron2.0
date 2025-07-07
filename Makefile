# Wikimetron Makefile

.PHONY: help install start stop clean test

help:
	@echo "Wikimetron - Commandes disponibles:"
	@echo "  make install    - Installer les dépendances"
	@echo "  make start      - Démarrer l'application"
	@echo "  make stop       - Arrêter l'application"  
	@echo "  make clean      - Nettoyer les containers"
	@echo "  make test       - Lancer les tests"
	@echo "  make logs       - Voir les logs"

install:
	@echo "📦 Installation des dépendances..."
	cd frontend && npm install
	cd backend && pip install -r requirements.txt

start:
	@echo "🚀 Démarrage de Wikimetron..."
	docker-compose up -d

stop:
	@echo "🛑 Arrêt de Wikimetron..."
	docker-compose down

clean:
	@echo "🧹 Nettoyage..."
	docker-compose down -v
	docker system prune -f

test:
	@echo "🧪 Lancement des tests..."
	cd backend && python -m pytest
	cd frontend && npm test

logs:
	@echo "📋 Logs de l'application..."
	docker-compose logs -f
