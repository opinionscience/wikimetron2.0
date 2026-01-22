# Wikipedia Sensitivity Meter (WSM) 🛡
### Wikipedia Content Intelligence Platform

![Status](https://img.shields.io/badge/status-production-green)
![Version](https://img.shields.io/badge/version-1.0.0-blue)

Wikimetron est une plateforme d'analyse intelligente des contenus Wikipedia. Elle calcule des scores de sensibilité, de qualité et de risque pour les pages Wikipedia en analysant de multiples dimensions via l'API Wikimedia.

## 📋 Table des matières

- [Architecture du Pipeline](#architecture-du-pipeline)
- [API Wikimedia](#api-wikimedia)
- [Métriques disponibles](#métriques-disponibles)
- [Structure du projet](#structure-du-projet)
- [Documentation](#documentation)

## 🏗️ Architecture du Pipeline

Le cœur de Wikimetron est un **pipeline d'analyse modulaire** qui orchestre le calcul de 27 métriques en interrogeant l'API Wikimedia.

### Fonctionnement du Pipeline

```
┌─────────────────┐
│  Titre d'article│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   API Wikimedia (MediaWiki)     │
│  - Contenu de la page           │
│  - Historique des révisions     │
│  - Métadonnées                  │
│  - Pages de discussion          │
│  - Statistiques de vues         │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│      Pipeline Wikimetron        │
│   (pipeline.py)                 │
│                                 │
│  Orchestration séquentielle     │
│  des modules de métriques       │
└────────┬────────────────────────┘
         │
         ├──▶ pageviews.py           → View spikes (Heat Risk)
         ├──▶ edit.py                → Edit spikes (Heat Risk)
         ├──▶ revert_risk.py         → Edit revert probability (Heat Risk)
         ├──▶ protection.py          → Protection (Heat Risk)
         ├──▶ taille_talk.py         → Discussion intensity (Heat Risk)
         │
         ├──▶ adq.py                 → Featured article (Quality Risk)
         ├──▶ blacklist_metric.py    → Suspicious sources (Quality Risk)
         ├──▶ ref.py                 → Citation gaps (Quality Risk)
         ├──▶ last_edit.py           → Staleness (Quality Risk)
         ├──▶ domination.py          → Source concentration (Quality Risk)
         ├──▶ balance.py             → Add/delete ratio (Quality Risk)
         │
         ├──▶ faux_nez.py            → Sockpuppets (Behaviour Risk)
         ├──▶ ano_edit.py            → Anonymity (Behaviour Risk)
         ├──▶ monopol.py             → Contributors concentration (Behaviour Risk)
         ├──▶ quantity.py            → Sporadicity (Behaviour Risk)
         └──▶ user_balance_metric.py → Contributor add/delete ratio (Behaviour Risk)

         │
         ▼
┌─────────────────────────────────┐
│   Scores agrégés                │
│  - Heat Risk /15                │
│  - Quality Risk /28             │
│  - Behaviour Risk /21           │
│  → Score total /64              │
└─────────────────────────────────┘
```

### Caractéristiques du Pipeline

- **Modulaire** : Chaque métrique est un module Python indépendant
- **Optimisé** : Mise en cache des appels API pour éviter les redondances
- **Batch processing** : Traitement de plusieurs articles en parallèle
- **Gestion d'erreurs** : Récupération gracieuse en cas d'échec d'une métrique
- **Traçabilité** : Logging détaillé de chaque étape

## 🔌 API Wikimedia

Wikimetron s'appuie entièrement sur l'**API MediaWiki** (Action API) de Wikimedia pour collecter les données.

### Endpoints utilisés

| Endpoint MediaWiki API | Module(s) | Données extraites |
|----------------------|-----------|------------------|
| `action=query&prop=revisions&rvprop=ids\|timestamp\|user` | edit.py, balance.py, monopol.py, domination.py | Historique des révisions, timestamps, contributeurs |
| **Wikimedia Inference API** `/models/revertrisk-language-agnostic:predict` | revert_risk.py | Probabilité de réversion (ML model) |
| **Wikimedia REST API** `/metrics/pageviews/per-article` | pageviews.py | Statistiques quotidiennes de consultations |
| `action=query&prop=info&inprop=protection` | protection.py | Niveau de protection de la page |
| `action=query&prop=revisions&rvprop=content` | ref.py, taille_talk.py, adq.py | Wikitext brut (page de discussion, contenu) |
| `action=query&list=usercontribs` | faux_nez.py | Liste des contributions par utilisateur |
| **Base de données locale** `blacklist.csv` | blacklist_metric.py | Liste de sources/contributeurs suspects |
| **Base de données locale** `faux_nez.csv` | faux_nez.py | Liste de sockpuppets connus |

### Exemple d'appel API

```python
import requests

# Récupérer l'historique des révisions
params = {
    'action': 'query',
    'format': 'json',
    'titles': 'Python (langage)',
    'prop': 'revisions',
    'rvprop': 'ids|timestamp|user|comment|size',
    'rvlimit': 500
}

response = requests.get('https://fr.wikipedia.org/w/api.php', params=params)
data = response.json()
```

### Optimisations

- **Batching** : Requêtes groupées pour plusieurs pages (`titles=Page1|Page2|Page3`)
- **Pagination** : Gestion automatique des continuations pour historiques longs
- **Rate limiting** : Respect des quotas Wikimedia (200 requêtes/seconde max)
- **User-Agent** : Identification claire dans les headers

### Documentation complète

📘 [API MediaWiki - Action API](https://www.mediawiki.org/wiki/API:Action_API/fr)

## 📊 Métriques disponibles

Le système calcule des métriques réparties en 3 catégories de risque. Chaque métrique interroge spécifiquement l'API Wikimedia pour extraire les données pertinentes.

### Heat Risk /15

Mesure l'intensité de l'activité et des controverses autour d'un article.

| Métrique | Module | API utilisée | Description |
|----------|--------|--------------|-------------|
| **View spikes** | `pageviews.py` | Wikimedia REST API `/pageviews` | Pics de consultation, indicateur d'attention médiatique |
| **Edit spikes** | `edit.py` | `prop=revisions&rvprop=timestamp` | Pics d'éditions, signe d'activité intense |
| **Edit revert probability** | `revert_risk.py` | Wikimedia Inference API `/revertrisk` | Probabilité de révocation par ML (guerres d'édition) |
| **Protection** | `protection.py` | `prop=info&inprop=protection` | Niveau de protection de la page (libre → plein) |
| **Discussion intensity** | `taille_talk.py` | `prop=revisions&rvprop=content` (Talk:) | Volume des débats en page de discussion |

### Quality Risk /28

Évalue la fiabilité et la qualité éditoriale de l'article.

| Métrique | Module | API utilisée | Description |
|----------|--------|--------------|-------------|
| **Featured article** | `adq.py` | `prop=revisions&rvprop=content` (Talk:) | Détection label ADQ/BA via bannière d'évaluation |
| **Suspicious sources** | `blacklist_metric.py` | `blacklist.csv` (local) | Sources présentes dans la liste de surveillance |
| **Citation gaps** | `ref.py` | `prop=revisions&rvprop=content` | Comptage des templates {{citation needed}} |
| **Staleness** | `last_edit.py` | `prop=revisions&rvprop=timestamp` (limit=1) | Ancienneté de la dernière modification |
| **Source concentration** | `domination.py` | `prop=revisions&rvprop=user` | Concentration des contributeurs (top N%) |
| **Modifs mineures ?** | `minor_edits.py` | `prop=revisions&rvprop=flags` | Proportion de modifications mineures (sur 100 dernières) |
| **Add/delete ratio** | `balance.py` | `prop=revisions&rvprop=size` | Ratio ajouts/suppressions de contenu |

### Behaviour Risk /21

Détecte les comportements éditoriaux suspects ou problématiques.

| Métrique | Module | API utilisée | Description |
|----------|--------|--------------|-------------|
| **Sockpuppets** | `faux_nez.py` | `faux_nez.csv` + `list=usercontribs` | Détection de comptes multiples via patterns |
| **Good contrib ?** | - | `prop=revisions&rvprop=user` | Qualité des contributions récentes |
| **Anonymity** | `ano_edit.py` | `prop=revisions&rvprop=user` | Proportion d'éditions anonymes (IP) |
| **Contributors concentration** | `monopol.py` | `prop=revisions&rvprop=user` | Monopole éditorial (top 5 contributeurs) |
| **Sporadicity** | `quantity.py` | `prop=revisions&rvprop=timestamp` | Irrégularité du rythme d'édition |
| **Contributor add/delete ratio** | `user_balance_metric.py` | `prop=revisions&rvprop=user,size` | Balance ajouts/suppressions par utilisateur |

### Agrégation des scores

Les métriques individuelles sont agrégées en 3 scores de risque :

```
Heat Risk (15 points max)     = f(view_spikes, edit_spikes, revert_prob, protection, discussion)
Quality Risk (28 points max)  = f(featured, suspicious_sources, citation_gaps, staleness, concentration)
Behaviour Risk (21 points max) = f(sockpuppets, anonymity, monopole, sporadicity, contributor_ratio)
```

**Score total = 64 points maximum**

📚 **Documentation détaillée** : [Tableau explicatif complet](https://docs.google.com/spreadsheets/d/1NRJf8x0Em-Wmmxi0iRTGNz3DVLYShJhe5kNXUUxRCHQ/edit?gid=912672517#gid=912672517)

## 📦 Structure du projet

```
wikimetron2.0/
├── backend/
│   └── wikimetron/
│       ├── metrics/                    # 🎯 Cœur du système
│       │   ├── pipeline.py             # Orchestrateur principal
│       │   │
│       │   ├── pageviews.py            # Heat Risk : View spikes
│       │   ├── edit.py                # Heat Risk : Edit spikes
│       │   ├── revert_risk.py         # Heat Risk : Edit revert probability
│       │   ├── protection.py          # Heat Risk : Protection
│       │   ├── taille_talk.py         # Heat Risk : Discussion intensity
│       │   │
│       │   ├── adq.py                 # Quality Risk : Featured article
│       │   ├── blacklist_metric.py    # Quality Risk : Suspicious sources
│       │   ├── ref.py                 # Quality Risk : Citation gaps
│       │   ├── last_edit.py           # Quality Risk : Staleness
│       │   ├── domination.py          # Quality Risk : Source concentration
│       │   ├── minor_edits.py         # Quality Risk : Modifs mineures (⏸️ non intégré)
│       │   ├── balance.py             # Quality Risk : Add/delete ratio
│       │   │
│       │   ├── faux_nez.py            # Behaviour Risk : Sockpuppets
│       │   ├── ano_edit.py            # Behaviour Risk : Anonymity
│       │   ├── monopol.py             # Behaviour Risk : Contributors concentration
│       │   ├── quantity.py            # Behaviour Risk : Sporadicity
│       │   ├── user_balance_metric.py # Behaviour Risk : Contributor add/delete ratio
│       │   │
│       │   ├── blacklist.csv           # Base de données locale
│       │   └── faux_nez.csv            # Liste sockpuppets
│       │
│       ├── api/                        # API REST FastAPI
│       ├── models/                     # Modèles de données
│       └── utils/                      # Utilitaires
│
├── frontend/                           # Interface React
└── docker-compose.yml                  # Orchestration services
```

### Fichier clé : `pipeline.py`

Le fichier `pipeline.py` orchestre l'exécution séquentielle de tous les modules de métriques :

```python
# Pseudo-code simplifié
def analyze_page(title: str) -> dict:
    """
    Pipeline principal d'analyse d'une page Wikipedia
    """
    results = {}

    # 1. Récupération données de base via API Wikimedia
    page_data = fetch_from_wikimedia(title)

    # 2. Exécution de chaque métrique
    results['adq_score'] = adq.calculate(page_data)
    results['protection'] = protection.calculate(page_data)
    results['domination'] = domination.calculate(page_data)
    # ... (27 métriques au total)

    # 3. Agrégation des scores
    results['sensitivity_score'] = aggregate_sensitivity(results)
    results['quality_score'] = aggregate_quality(results)
    results['risk_score'] = aggregate_risk(results)

    return results
```

## 📚 Documentation

- **API Wikimedia** : [MediaWiki Action API](https://www.mediawiki.org/wiki/API:Action_API/fr)
- **Métriques détaillées** : [Tableau Google Sheets](https://docs.google.com/spreadsheets/d/1NRJf8x0Em-Wmmxi0iRTGNz3DVLYShJhe5kNXUUxRCHQ/edit?gid=912672517#gid=912672517)

---

**Statut** : ✅ Projet finalisé et opérationnel
**Équipe** : Opsci Team
**Version** : 1.0.0
