#!/usr/bin/env python3
"""
Métrique de déséquilibre ajouts/suppressions Wikipédia
(Pipeline-ready, multilingue)
"""

import requests
import pandas as pd
import logging
from datetime import datetime
from typing import Optional, List, Dict

def get_api_url(lang="fr"):
    """Construit l’URL de l’API MediaWiki pour une langue donnée."""
    return f"https://{lang}.wikipedia.org/w/api.php"

def fetch_revisions_with_size(title: str,
                              start: Optional[datetime] = None,
                              end: Optional[datetime] = None,
                              lang: str = "fr") -> List[Dict]:
    """
    Récupère toutes les révisions d'une page Wikipédia (multilingue).
    Args:
        title (str): Titre de la page.
        start (datetime, optionnel): Date de début.
        end (datetime, optionnel): Date de fin.
        lang (str): Code langue Wikipédia (ex: 'fr', 'en').
    Returns:
        List[Dict]: Liste de révisions (dict contenant timestamp, size, etc.).
    """
    API_URL = get_api_url(lang)
    HEADERS = {"User-Agent": f"WikiBalanceSimple/1.1 ({lang}@opsci.com)"}
    revs = []
    start_ts = start.strftime('%Y-%m-%dT%H:%M:%SZ') if start else None
    end_ts = end.strftime('%Y-%m-%dT%H:%M:%SZ') if end else None

    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "ids|timestamp|size|user|comment",
        "rvlimit": "max",
        "format": "json",
        "formatversion": "2",
        "rvdir": "newer"
    }
    if start_ts:
        params["rvstart"] = start_ts
    if end_ts:
        params["rvend"] = end_ts

    cont = {}
    while True:
        req = {**params, **cont}
        try:
            r = requests.get(API_URL, params=req, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                break
            pages = data.get("query", {}).get("pages", [])
            if pages and "revisions" in pages[0]:
                revs.extend(pages[0]["revisions"])
            if "continue" in data:
                cont = data["continue"]
            else:
                break
        except requests.RequestException:
            break
    return revs

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

def get_event_imbalance(pages: List[str],
                        start: Optional[str] = None,
                        end: Optional[str] = None,
                        lang: str = "fr") -> pd.DataFrame:
    """
    Calcule les métriques de déséquilibre pour une liste de pages Wikipédia, pour la langue choisie.
    Args:
        pages (List[str]): Titres des pages Wikipédia.
        start (str, optionnel): Date de début (YYYY-MM-DD).
        end (str, optionnel): Date de fin (YYYY-MM-DD).
        lang (str): Code langue Wikipédia (ex: 'fr', 'en').
    Returns:
        pd.DataFrame: Table avec les scores de déséquilibre pour chaque page.
    """
    results = []
    start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
    end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None

    for page in pages:
        revs = fetch_revisions_with_size(page, start_dt, end_dt, lang=lang)
        metrics = compute_simple_metrics(revs)
        imbalances = calculate_imbalances(metrics)
        res = {"page": page, **imbalances}
        results.append(res)
    return pd.DataFrame(results).set_index("page")


def get_event_imbalance_events_only(pages, start=None, end=None, lang="fr"):
    """
    Renvoie uniquement le score de déséquilibre des événements (imbalance_events)
    sous forme de pd.Series indexée par page.
    """
    df = get_event_imbalance(pages, start, end, lang)
    return df["imbalance_events"]

# Utilisation pipeline (exemple) :
if __name__ == "__main__":
    # Exemple : calculer pour 2 pages
    df = get_event_imbalance(["Emmanuel Macron"], start="2025-06-01", end="2025-07-01", lang="it")
    print(df)
