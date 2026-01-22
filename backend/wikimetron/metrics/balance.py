#!/usr/bin/env python3
"""
Métrique de déséquilibre ajouts/suppressions Wikipédia
(Pipeline-ready, multilingue) - Version avec compteur d'exclusions en mode verbose
"""

import requests
import pandas as pd
import logging
from datetime import datetime
from typing import Optional, List, Dict, Set


def get_api_url(lang="fr"):
    """Construit l'URL de l'API MediaWiki pour une langue donnée."""
    return f"https://{lang}.wikipedia.org/w/api.php"


def get_user_groups(usernames: List[str], lang: str = "fr") -> Dict[str, List[str]]:
    """Récupère les groupes d'utilisateurs via l'API MediaWiki."""
    API_URL = get_api_url(lang)
    HEADERS = {"User-Agent": f"WikiBalanceSimple/1.2 ({lang}@opsci.com)"}

    user_groups = {}
    BATCH_SIZE = 50
    for i in range(0, len(usernames), BATCH_SIZE):
        batch = usernames[i:i + BATCH_SIZE]
        params = {
            "action": "query", "list": "users", "ususers": "|".join(batch),
            "usprop": "groups", "format": "json", "formatversion": "2"
        }
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            users = data.get("query", {}).get("users", [])
            for user in users:
                user_groups[user.get("name", "")] = user.get("groups", [])
        except requests.RequestException as e:
            logging.warning(f"Erreur groupes utilisateurs: {e}")
            for username in batch:
                user_groups[username] = []
    return user_groups


def filter_non_admin_revisions(revisions: List[Dict], lang: str = "fr",
                               exclude_bots: bool = False) -> List[Dict]:
    """Filtre les révisions pour ne garder que celles des non-administrateurs."""
    if not revisions:
        return []

    usernames = list(set([
        rev.get("user", "") for rev in revisions
        if rev.get("user") and not rev.get("anon")
    ]))

    user_groups = get_user_groups(usernames, lang)
    excluded_users = set()

    for username, groups in user_groups.items():
        if "sysop" in groups or "bureaucrat" in groups or "rollbacker" in groups:
            excluded_users.add(username)
        if exclude_bots and "bot" in groups:
            excluded_users.add(username)

    filtered_revisions = [
        rev for rev in revisions
        if rev.get("anon") or rev.get("user", "") not in excluded_users
    ]
    return filtered_revisions


def fetch_last_revisions_with_size(title: str,
                                   end: Optional[datetime] = None,
                                   limit: int = 10,
                                   lang: str = "fr",
                                   exclude_admins: bool = False,
                                   exclude_bots: bool = False,
                                   verbose: bool = False) -> List[Dict]:
    """
    Récupère les dernières révisions.
    MODIFIÉ: Affiche le nombre d'exclus si verbose=True.
    """
    API_URL = get_api_url(lang)
    HEADERS = {"User-Agent": f"WikiBalanceSimple/1.2 ({lang}@opsci.com)"}
    end_ts = end.strftime('%Y-%m-%dT%H:%M:%SZ') if end else None

    params = {
        "action": "query", "titles": title, "prop": "revisions",
        "rvprop": "ids|timestamp|size|user|comment", "rvlimit": limit,
        "format": "json", "formatversion": "2", "rvdir": "older"
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
            revisions = pages[0]["revisions"]

            if exclude_admins or exclude_bots:
                count_before = len(revisions)
                revisions = filter_non_admin_revisions(revisions, lang, exclude_bots)
                count_after = len(revisions)

                if verbose:
                    diff = count_before - count_after
                    msg_type = "Admins"
                    if exclude_bots: msg_type += "/Bots"
                    print(f"--> [FILTRAGE] {diff} révision(s) exclue(s) ({msg_type}) sur {count_before} récupérées.")

            return revisions
    except requests.RequestException:
        pass
    return []


def compute_simple_metrics(revisions: List[Dict]) -> Dict:
    """Calcule les métriques basiques."""
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
        prev_size = revs[i - 1].get("size", 0)
        curr_size = revs[i].get("size", 0)
        if prev_size is None or curr_size is None: continue

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
    """Calcule les scores de déséquilibre."""
    bytes_total = metrics['total_bytes_added'] + metrics['total_bytes_removed']
    events_total = metrics['count_add_events'] + metrics['count_del_events']

    imbalance_bytes = (abs(
        metrics['total_bytes_added'] - metrics['total_bytes_removed']) / bytes_total) if bytes_total > 0 else 0.0
    imbalance_events = (abs(
        metrics['count_add_events'] - metrics['count_del_events']) / events_total) if events_total > 0 else 0.0

    return {
        'imbalance_events': imbalance_events,
        'imbalance_bytes': imbalance_bytes,
        **metrics
    }


def parse_date(date_str):
    if not date_str: return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            raise ValueError()
        except ValueError:
            raise ValueError(f"Format invalide (attendu YYYY-MM-DD ou ISO)")


def get_event_imbalance(pages: List[str], end: Optional[str] = None, limit: int = 10,
                        lang: str = "fr", exclude_admins: bool = True, exclude_bots: bool = False) -> pd.DataFrame:
    """Fonction pipeline principale."""
    results = []
    end_dt = None
    if end:
        try:
            end_dt = datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            if 'T' in end:
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).replace(tzinfo=None)

    for page in pages:
        revs = fetch_last_revisions_with_size(page, end_dt, limit, lang, exclude_admins, exclude_bots)
        metrics = compute_simple_metrics(revs)
        imbalances = calculate_imbalances(metrics)
        results.append({"page": page, **imbalances})
    return pd.DataFrame(results).set_index("page")


def get_event_imbalance_events_only(pages: List[str], end: Optional[str] = None, limit: int = 10,
                                    lang: str = "fr", exclude_admins: bool = True,
                                    exclude_bots: bool = False) -> pd.Series:
    """
    Renvoie uniquement le score de déséquilibre des événements (imbalance_events)
    sous forme de pd.Series indexée par page.

    Args:
        pages (List[str]): Titres des pages Wikipédia.
        end (str, optionnel): Date de fin (YYYY-MM-DD ou format ISO).
        limit (int): Nombre de révisions à récupérer (défaut: 10).
        lang (str): Code langue Wikipédia (ex: 'fr', 'en').
        exclude_admins (bool): Exclure les révisions des administrateurs (défaut: True).
        exclude_bots (bool): Exclure les révisions des bots (défaut: False).

    Returns:
        pd.Series: Scores imbalance_events indexés par page.
    """
    df = get_event_imbalance(pages, end, limit, lang, exclude_admins, exclude_bots)
    return df["imbalance_events"]


def display_revision_details(revisions: List[Dict]) -> None:
    if not revisions:
        print("Aucune révision trouvée.")
        return
    revs_sorted = sorted(revisions, key=lambda r: r["timestamp"])
    print(f"\n{'=' * 80}\nDÉTAILS DES RÉVISIONS ({len(revs_sorted)} retenues)\n{'=' * 80}\n")
    for i, rev in enumerate(revs_sorted, 1):
        size_change = ""
        if i > 1:
            change = rev.get("size", 0) - revs_sorted[i - 2].get("size", 0)
            prefix = "+" if change > 0 else ""
            size_change = f" ({prefix}{change} bytes)"
        print(f"Rev #{i} - {rev.get('timestamp')} | User: {rev.get('user')} | Size: {rev.get('size')}{size_change}")


def display_metrics_summary(metrics: Dict, imbalances: Dict) -> None:
    print(f"\n{'=' * 80}\nRÉSUMÉ DES MÉTRIQUES\n{'=' * 80}\n")
    print(f"Total révisions analysées: {metrics['total_revisions']}")
    print(f"Changements analysés: {metrics['changes_analyzed']}")
    print(f"Bytes ajoutés/supprimés: {metrics['total_bytes_added']} / {metrics['total_bytes_removed']}")
    print(f"Events ajout/suppression: {metrics['count_add_events']} / {metrics['count_del_events']}")
    print(
        f"\nSCORES FINAUX:\n  Déséquilibre événements: {imbalances['imbalance_events']:.4f}\n  Déséquilibre bytes:      {imbalances['imbalance_bytes']:.4f}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("page", help="Titre de la page")
    parser.add_argument("--lang", default="fr")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--end", help="Date fin (YYYY-MM-DD)")
    parser.add_argument("--no-exclude-admins", action="store_true")
    parser.add_argument("--exclude-bots", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    end_dt = parse_date(args.end) if args.end else None
    exclude_admins = not args.no_exclude_admins

    print(f"\nRécupération des {args.limit} dernières révisions pour '{args.page}'...")

    revisions = fetch_last_revisions_with_size(
        args.page, end_dt, args.limit, args.lang,
        exclude_admins=exclude_admins,
        exclude_bots=args.exclude_bots,
        verbose=args.verbose
    )

    if not revisions:
        print(f"\nAucune révision trouvée (ou toutes filtrées).")
        exit(1)

    if args.verbose:
        display_revision_details(revisions)

    metrics = compute_simple_metrics(revisions)
    imbalances = calculate_imbalances(metrics)
    display_metrics_summary(metrics, imbalances)