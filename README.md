# Wikipedia Sensitivity Meter (WSM)
### Wikipedia Content Intelligence Platform

![Status](https://img.shields.io/badge/status-production-green)
![Version](https://img.shields.io/badge/version-1.0.0-blue)

Wikimetron is an intelligent analysis platform for Wikipedia content. It calculates sensitivity, quality, and risk scores for Wikipedia pages by analyzing multiple dimensions through the Wikimedia API.

## Table of Contents

- [Pipeline Architecture](#pipeline-architecture)
- [Wikimedia API](#wikimedia-api)
- [Available Metrics](#available-metrics)
- [Project Structure](#project-structure)
- [Documentation](#documentation)

## Pipeline Architecture

The core of Wikimetron is a **modular analysis pipeline** that orchestrates the computation of 27 metrics by querying the Wikimedia API.

### How the Pipeline Works

```
┌─────────────────┐
│  Article Title  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Wikimedia API (MediaWiki)     │
│  - Page content                 │
│  - Revision history             │
│  - Metadata                     │
│  - Talk pages                   │
│  - View statistics              │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│      Wikimetron Pipeline        │
│   (pipeline.py)                 │
│                                 │
│  Sequential orchestration       │
│  of metric modules              │
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
│   Aggregated Scores             │
│  - Heat Risk /15                │
│  - Quality Risk /28             │
│  - Behaviour Risk /21           │
│  → Total Score /64              │
└─────────────────────────────────┘
```

### Pipeline Features

- **Modular**: Each metric is an independent Python module
- **Optimized**: API call caching to avoid redundancy
- **Batch processing**: Parallel processing of multiple articles
- **Error handling**: Graceful recovery when a metric fails
- **Traceability**: Detailed logging at each step

## Wikimedia API

Wikimetron relies entirely on the **MediaWiki API** (Action API) from Wikimedia to collect data.

### Endpoints Used

| MediaWiki API Endpoint | Module(s) | Extracted Data |
|----------------------|-----------|------------------|
| `action=query&prop=revisions&rvprop=ids\|timestamp\|user` | edit.py, balance.py, monopol.py, domination.py | Revision history, timestamps, contributors |
| **Wikimedia Inference API** `/models/revertrisk-language-agnostic:predict` | revert_risk.py | Revert probability (ML model) |
| **Wikimedia REST API** `/metrics/pageviews/per-article` | pageviews.py | Daily page view statistics |
| `action=query&prop=info&inprop=protection` | protection.py | Page protection level |
| `action=query&prop=revisions&rvprop=content` | ref.py, taille_talk.py, adq.py | Raw wikitext (talk page, content) |
| `action=query&list=usercontribs` | faux_nez.py | List of contributions per user |
| **Local database** `blacklist.csv` | blacklist_metric.py | List of suspicious sources/contributors |
| **Local database** `faux_nez.csv` | faux_nez.py | List of known sockpuppets |

### API Call Example

```python
import requests

# Retrieve revision history
params = {
    'action': 'query',
    'format': 'json',
    'titles': 'Python (programming language)',
    'prop': 'revisions',
    'rvprop': 'ids|timestamp|user|comment|size',
    'rvlimit': 500
}

response = requests.get('https://fr.wikipedia.org/w/api.php', params=params)
data = response.json()
```

### Optimizations

- **Batching**: Grouped requests for multiple pages (`titles=Page1|Page2|Page3`)
- **Pagination**: Automatic continuation handling for long histories
- **Rate limiting**: Compliance with Wikimedia quotas (200 requests/second max)
- **User-Agent**: Clear identification in headers

### Full Documentation

[MediaWiki - Action API](https://www.mediawiki.org/wiki/API:Action_API)

## Available Metrics

The system computes metrics across 3 risk categories. Each metric specifically queries the Wikimedia API to extract relevant data.

### Heat Risk /15

Measures the intensity of activity and controversy surrounding an article.

| Metric | Module | API Used | Description |
|----------|--------|--------------|-------------|
| **View spikes** | `pageviews.py` | Wikimedia REST API `/pageviews` | View spikes, indicator of media attention |
| **Edit spikes** | `edit.py` | `prop=revisions&rvprop=timestamp` | Edit spikes, sign of intense activity |
| **Edit revert probability** | `revert_risk.py` | Wikimedia Inference API `/revertrisk` | ML-based revert probability (edit wars) |
| **Protection** | `protection.py` | `prop=info&inprop=protection` | Page protection level (open → full) |
| **Discussion intensity** | `taille_talk.py` | `prop=revisions&rvprop=content` (Talk:) | Volume of debates on the talk page |

### Quality Risk /28

Assesses the reliability and editorial quality of the article.

| Metric | Module | API Used | Description |
|----------|--------|--------------|-------------|
| **Featured article** | `adq.py` | `prop=revisions&rvprop=content` (Talk:) | Detection of Featured/Good Article labels via assessment banners |
| **Suspicious sources** | `blacklist_metric.py` | `blacklist.csv` (local) | Sources present in the watchlist |
| **Citation gaps** | `ref.py` | `prop=revisions&rvprop=content` | Count of {{citation needed}} templates |
| **Staleness** | `last_edit.py` | `prop=revisions&rvprop=timestamp` (limit=1) | Age of the last edit |
| **Source concentration** | `domination.py` | `prop=revisions&rvprop=user` | Contributor concentration (top N%) |
| **Minor edits?** | `minor_edits.py` | `prop=revisions&rvprop=flags` | Proportion of minor edits (over last 100) |
| **Add/delete ratio** | `balance.py` | `prop=revisions&rvprop=size` | Content addition/deletion ratio |

### Behaviour Risk /21

Detects suspicious or problematic editorial behaviours.

| Metric | Module | API Used | Description |
|----------|--------|--------------|-------------|
| **Sockpuppets** | `faux_nez.py` | `faux_nez.csv` + `list=usercontribs` | Detection of multiple accounts via patterns |
| **Good contrib?** | - | `prop=revisions&rvprop=user` | Quality of recent contributions |
| **Anonymity** | `ano_edit.py` | `prop=revisions&rvprop=user` | Proportion of anonymous (IP) edits |
| **Contributors concentration** | `monopol.py` | `prop=revisions&rvprop=user` | Editorial monopoly (top 5 contributors) |
| **Sporadicity** | `quantity.py` | `prop=revisions&rvprop=timestamp` | Irregularity of editing frequency |
| **Contributor add/delete ratio** | `user_balance_metric.py` | `prop=revisions&rvprop=user,size` | Addition/deletion balance per user |

### Score Aggregation

Individual metrics are aggregated into 3 risk scores:

```
Heat Risk (15 points max)     = f(view_spikes, edit_spikes, revert_prob, protection, discussion)
Quality Risk (28 points max)  = f(featured, suspicious_sources, citation_gaps, staleness, concentration)
Behaviour Risk (21 points max) = f(sockpuppets, anonymity, monopole, sporadicity, contributor_ratio)
```

**Total score = 64 points maximum**

**Detailed documentation**: [Full explanatory spreadsheet](https://docs.google.com/spreadsheets/d/1NRJf8x0Em-Wmmxi0iRTGNz3DVLYShJhe5kNXUUxRCHQ/edit?gid=912672517#gid=912672517)

## Project Structure

```
wikimetron2.0/
├── backend/
│   └── wikimetron/
│       ├── metrics/                    # Core system
│       │   ├── pipeline.py             # Main orchestrator
│       │   │
│       │   ├── pageviews.py            # Heat Risk: View spikes
│       │   ├── edit.py                # Heat Risk: Edit spikes
│       │   ├── revert_risk.py         # Heat Risk: Edit revert probability
│       │   ├── protection.py          # Heat Risk: Protection
│       │   ├── taille_talk.py         # Heat Risk: Discussion intensity
│       │   │
│       │   ├── adq.py                 # Quality Risk: Featured article
│       │   ├── blacklist_metric.py    # Quality Risk: Suspicious sources
│       │   ├── ref.py                 # Quality Risk: Citation gaps
│       │   ├── last_edit.py           # Quality Risk: Staleness
│       │   ├── domination.py          # Quality Risk: Source concentration
│       │   ├── minor_edits.py         # Quality Risk: Minor edits (not yet integrated)
│       │   ├── balance.py             # Quality Risk: Add/delete ratio
│       │   │
│       │   ├── faux_nez.py            # Behaviour Risk: Sockpuppets
│       │   ├── ano_edit.py            # Behaviour Risk: Anonymity
│       │   ├── monopol.py             # Behaviour Risk: Contributors concentration
│       │   ├── quantity.py            # Behaviour Risk: Sporadicity
│       │   ├── user_balance_metric.py # Behaviour Risk: Contributor add/delete ratio
│       │   │
│       │   ├── blacklist.csv           # Local database
│       │   └── faux_nez.csv            # Sockpuppets list
│       │
│       ├── api/                        # FastAPI REST API
│       ├── models/                     # Data models
│       └── utils/                      # Utilities
│
├── frontend/                           # React interface
└── docker-compose.yml                  # Service orchestration
```

### Key File: `pipeline.py`

The `pipeline.py` file orchestrates the sequential execution of all metric modules:

```python
# Simplified pseudo-code
def analyze_page(title: str) -> dict:
    """
    Main analysis pipeline for a Wikipedia page
    """
    results = {}

    # 1. Fetch base data via Wikimedia API
    page_data = fetch_from_wikimedia(title)

    # 2. Execute each metric
    results['adq_score'] = adq.calculate(page_data)
    results['protection'] = protection.calculate(page_data)
    results['domination'] = domination.calculate(page_data)
    # ... (27 metrics total)

    # 3. Aggregate scores
    results['sensitivity_score'] = aggregate_sensitivity(results)
    results['quality_score'] = aggregate_quality(results)
    results['risk_score'] = aggregate_risk(results)

    return results
```

## Documentation

- **Wikimedia API**: [MediaWiki Action API](https://www.mediawiki.org/wiki/API:Action_API)
- **Detailed metrics**: [Google Sheets spreadsheet](https://docs.google.com/spreadsheets/d/1NRJf8x0Em-Wmmxi0iRTGNz3DVLYShJhe5kNXUUxRCHQ/edit?gid=912672517#gid=912672517)

---

**Status**: Project finalized and operational
**Team**: Opsci Team
**Version**: 1.0.0

