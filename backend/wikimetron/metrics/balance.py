#!/usr/bin/env python3
"""
Métrique de déséquilibre ajouts/suppressions Wikipédia
(Pipeline-ready, multilingue) - Version modifiée avec date de fin uniquement
"""

import requests
import pandas as pd
import logging
from datetime import datetime
from typing import Optional, List, Dict

def get_api_url(lang="fr"):
    """Construit l'URL de l'API MediaWiki pour une langue donnée."""
    return f"https://{lang}.wikipedia.org/w/api.php"

def fetch_last_revisions_with_size(title: str,
                                  end: Optional[datetime] = None,
                                  limit: int = 10,
                                  lang: str = "fr") -> List[Dict]:
    """
    Récupère les dernières révisions d'une page Wikipédia avant une date donnée.
    Args:
        title (str): Titre de la page.
        end (datetime, optionnel): Date de fin.
        limit (int): Nombre de révisions à récupérer (défaut: 10).
        lang (str): Code langue Wikipédia (ex: 'fr', 'en').
    Returns:
        List[Dict]: Liste de révisions (dict contenant timestamp, size, etc.).
    """
    API_URL = get_api_url(lang)
    HEADERS = {"User-Agent": f"WikiBalanceSimple/1.1 ({lang}@opsci.com)"}
    
    end_ts = end.strftime('%Y-%m-%dT%H:%M:%SZ') if end else None

    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "ids|timestamp|size|user|comment",
        "rvlimit": limit,
        "format": "json",
        "formatversion": "2",
        "rvdir": "older"  # Du plus récent au plus ancien
    }
    if end_ts:
        params["rvstart"] = end_ts

    try:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            return []
        pages = data.get("query", {}).get("pages", [])
        if pages and "revisions" in pages[0]:
            return pages[0]["revisions"]
    except requests.RequestException:
        pass
    return []

def compute_simple_metrics(revisions: List[Dict]) -> Dict:
    """Calcule les métriques basiques (ajouts/suppressions) sur la liste des révisions."""
    if len(revisions) < 2:
        return {
            'total_bytes_added': 0, 'total_bytes_removed': 0,
            'count_add_events': 0, 'count_del_events': 0, 'count_neutral_events': 0,
            'total_revisions': len(revisions), 'changes_analyzed': 0,
        }
    revs = sorted(revisions, key=lambda r: r["timestamp"])
    total_bytes_added = total_bytes_removed = 0
    count_add_events = count_del_events = count_neutral_events = 0

    for i in range(1, len(revs)):
        prev_size = revs[i-1].get("size", 0)
        curr_size = revs[i].get("size", 0)
        if prev_size is None or curr_size is None:
            continue
        size_change = curr_size - prev_size
        if size_change > 0:
            total_bytes_added += size_change
            count_add_events += 1
        elif size_change < 0:
            total_bytes_removed += abs(size_change)
            count_del_events += 1
        else:
            count_neutral_events += 1
    return {
        'total_bytes_added': total_bytes_added,
        'total_bytes_removed': total_bytes_removed,
        'count_add_events': count_add_events,
        'count_del_events': count_del_events,
        'count_neutral_events': count_neutral_events,
        'total_revisions': len(revs),
        'changes_analyzed': len(revs) - 1,
    }

def calculate_imbalances(metrics: Dict) -> Dict:
    """Calcule les déséquilibres (événements et bytes) à partir des métriques brutes."""
    bytes_total = metrics['total_bytes_added'] + metrics['total_bytes_removed']
    events_total = metrics['count_add_events'] + metrics['count_del_events']
    imbalance_bytes = (
        abs(metrics['total_bytes_added'] - metrics['total_bytes_removed']) / bytes_total
        if bytes_total > 0 else 0.0
    )
    imbalance_events = (
        abs(metrics['count_add_events'] - metrics['count_del_events']) / events_total
        if events_total > 0 else 0.0
    )
    return {
        'imbalance_events': imbalance_events,
        'imbalance_bytes': imbalance_bytes,
        'count_add_events': metrics['count_add_events'],
        'count_del_events': metrics['count_del_events'],
        'total_bytes_added': metrics['total_bytes_added'],
        'total_bytes_removed': metrics['total_bytes_removed'],
        'total_revisions': metrics['total_revisions']
    }

def parse_date(date_str):
    """Parse une date au format YYYY-MM-DD ou ISO."""
    if not date_str:
        return None
    try:
        # Essayer d'abord le format YYYY-MM-DD
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            # Si ça échoue, essayer le format ISO (depuis le pipeline)
            if 'T' in date_str:
                # Format ISO: 2025-05-21T00:00:00Z
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            else:
                raise ValueError()
        except ValueError:
            raise ValueError(f"Format de date invalide. Utilisez YYYY-MM-DD (ex: 2024-01-01) ou format ISO")

# Ou plus simple, adapter directement get_event_imbalance pour accepter les deux:
def get_event_imbalance(pages: List[str],
                        end: Optional[str] = None,
                        limit: int = 10,
                        lang: str = "fr") -> pd.DataFrame:
    """
    Calcule les métriques de déséquilibre pour une liste de pages Wikipédia.
    Args:
        pages (List[str]): Titres des pages Wikipédia.
        end (str, optionnel): Date de fin (YYYY-MM-DD ou format ISO).
        limit (int): Nombre de révisions à récupérer (défaut: 10).
        lang (str): Code langue Wikipédia (ex: 'fr', 'en').
    Returns:
        pd.DataFrame: Table avec les scores de déséquilibre pour chaque page.
    """
    results = []
    
    # Parsing flexible de la date
    end_dt = None
    if end:
        try:
            # Essayer YYYY-MM-DD d'abord
            end_dt = datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            try:
                # Essayer le format ISO ensuite
                if 'T' in end:
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).replace(tzinfo=None)
                else:
                    raise ValueError()
            except ValueError:
                raise ValueError(f"Format de date invalide: {end}. Utilisez YYYY-MM-DD ou format ISO")

    for page in pages:
        revs = fetch_last_revisions_with_size(page, end_dt, limit, lang=lang)
        metrics = compute_simple_metrics(revs)
        imbalances = calculate_imbalances(metrics)
        res = {"page": page, **imbalances}
        results.append(res)
    return pd.DataFrame(results).set_index("page")

def get_event_imbalance_events_only(pages, end=None, limit=10, lang="fr"):
    """
    Renvoie uniquement le score de déséquilibre des événements (imbalance_events)
    sous forme de pd.Series indexée par page.
    """
    df = get_event_imbalance(pages, end, limit, lang)
    return df["imbalance_events"]

# Utilisation pipeline (exemple) :
if __name__ == "__main__":
    # Exemple : calculer pour 1 page avec les 10 dernières révisions avant le 27 août 2025
    df = get_event_imbalance(["Franciaország"], end="2025-08-29", limit=10, lang="hu")
    print(df)