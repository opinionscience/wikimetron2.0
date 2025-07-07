# Wikimetron 🛡️

**Wikipedia Content Intelligence Platform**

Wikimetron est une plateforme d'analyse et de surveillance intelligente des contenus Wikipedia. Elle calcule des scores de sensibilité, qualité et risque pour les pages Wikipedia.

## 🚀 Démarrage rapide

```bash
# Cloner le projet
git clone <votre-repo>
cd wikimetron

# Lancer avec Docker
docker-compose up -d

# Accéder à l'application
# Frontend: http://localhost:8300
# Backend API: http://localhost:8200
# API Docs: http://localhost:8200/docs
```

## 📁 Structure du projet (Simplifiée)

```
wikimetron/
├── backend/           # API Python FastAPI
│   └── wikimetron/
│       ├── api/       # Endpoints FastAPI
│       ├── metrics/   # Pipeline + Métriques (unifié)
│       ├── models/    # Modèles de données
│       └── utils/     # Utilitaires
├── frontend/          # Interface React
├── data/              # Données et cache
├── config/            # Configuration
├── docs/              # Documentation
└── scripts/           # Scripts utilitaires
```

## 📦 Intégration de votre pipeline

1. **Copiez votre pipeline principal** dans `backend/wikimetron/metrics/pipeline.py`
2. **Ajoutez vos modules de métriques** dans `backend/wikimetron/metrics/`
3. **Adaptez les imports** pour utiliser la nouvelle structure

Exemple :
```python
# Dans metrics/pipeline.py
from .quality_metrics import calculate_quality_score
from .sensitivity_metrics import calculate_sensitivity_score
from .risk_metrics import calculate_risk_score
```

## 🛠️ Technologies

- **Backend:** Python, FastAPI, PostgreSQL, Redis
- **Frontend:** React, Tailwind CSS, Recharts
- **Infrastructure:** Docker, Docker Compose

## 📖 Documentation

Voir le dossier `docs/` pour la documentation complète.

## 🤝 Contribution

Voir `CONTRIBUTING.md` pour les guidelines de contribution.

## 📄 Licence

MIT License - voir `LICENSE` pour plus de détails.
