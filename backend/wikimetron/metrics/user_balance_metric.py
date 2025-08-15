#!/usr/bin/env python3
"""
Calcule la moyenne du déséquilibre ajouts/suppressions des X derniers contributeurs pour chaque page Wikipédia.
Usage :
    python user_balance_metric.py "Page1" "Page2" --lang fr --users 10 --contribs 100 --end "2024-01-01"
"""
import requests
import pandas as pd
import argparse
import time
from datetime import datetime

HEADERS = {"User-Agent": "UserBalanceAnalyzer/1.0 (pipeline@example.com)"}

def get_user_contributions(user, lang="fr", limit=100, end=None):
    """Récupère les contributions d'un utilisateur, optionnellement depuis une date donnée."""
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "usercontribs",
        "ucuser": user,
        "ucprop": "sizediff",
        "uclimit": limit,
        "formatversion": "2"
    }

    # Ajouter la date de début si spécifiée (les contributions jusqu'à cette date)
    if end:
        params["ucstart"] = end

    try:
        r = requests.get(api_url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("query", {}).get("usercontribs", [])
    except Exception:
        return []

def get_recent_editors(page, lang="fr", limit=10, end=None):
    """Récupère les derniers éditeurs d'une page, optionnellement avant une date donnée."""
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": page,
        "prop": "revisions",
        "rvprop": "user|timestamp",
        "rvlimit": min(limit*3, 500),
        "formatversion": "2"
    }

    # Ajouter la date de début si spécifiée (les révisions jusqu'à cette date)
    if end:
        params["rvstart"] = end  # Fixed: should be 'rvstart' not 'rstart'

    try:
        r = requests.get(api_url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", [])
        if not pages or "revisions" not in pages[0]:
            return []

        users = []
        seen = set()
        for rev in pages[0]["revisions"]:
            user = rev.get("user")
            # Fixed: Proper date comparison using datetime objects
            if end and rev.get("timestamp"):
                try:
                    rev_date = datetime.fromisoformat(rev["timestamp"].replace('Z', '+00:00'))
                    end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    if rev_date > end_date:
                        continue
                except (ValueError, AttributeError):
                    # If date parsing fails, skip this revision
                    continue

            if user and user not in seen:
                seen.add(user)
                users.append(user)
            if len(users) >= limit:
                break
        return users
    except Exception as e:
        print(f"Error in get_recent_editors: {e}")
        return []

def parse_date(date_str):
    """Parse une date au format YYYY-MM-DD."""
    if not date_str:
        return None

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # Convertir en format ISO pour l'API Wikipedia
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise ValueError(f"Format de date invalide. Utilisez YYYY-MM-DD (ex: 2024-01-01)")

def get_mean_contributor_balance(pages, lang="fr", num_users=10, num_contributions=100, end=None):
    """Calcule la moyenne du déséquilibre des contributeurs pour chaque page."""
    results = {}

    # Si aucune date n'est spécifiée, utiliser aujourd'hui
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    # Parser la date
    try:
        parsed_date = parse_date(end)
        print(f"Analyse des contributions avant le {parsed_date}")
    except ValueError as e:
        print(f"Erreur: {e}")
        return pd.Series(dtype=float)

    for page in pages:
        print(f"Analyse de la page: {page}")
        editors = get_recent_editors(page, lang, num_users, parsed_date)
        print(f"  Éditeurs trouvés: {len(editors)}")

        scores = []
        for i, user in enumerate(editors):
            print(f"  Analyse utilisateur {i+1}/{len(editors)}: {user}")
            contribs = get_user_contributions(user, lang, num_contributions, parsed_date)

            adds = sum(1 for c in contribs if c.get("sizediff", 0) > 0)
            dels = sum(1 for c in contribs if c.get("sizediff", 0) < 0)
            total = adds + dels
            score = abs(adds - dels) / total if total > 0 else 0.0
            scores.append(score)
            print(f"    Contributions: {len(contribs)}, Ajouts: {adds}, Suppressions: {dels}, Score: {score:.3f}")
            time.sleep(0.1)  # Retire si tu veux aller + vite

        results[page] = float(pd.Series(scores).mean()) if scores else 0.0
        print(f"  Score moyen pour {page}: {results[page]:.3f}\n")

    return pd.Series(results, name="mean_contributor_balance")

# ==== CLI minimaliste ====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score moyen de balance contributeurs Wikipedia")
    parser.add_argument("pages", nargs="+", help="Titres des pages Wikipedia")
    parser.add_argument("--lang", default="fr", help="Langue (fr, en, ...)")
    parser.add_argument("--users", type=int, default=10, help="Nb contributeurs à analyser")
    parser.add_argument("--contribs", type=int, default=10, help="Nb contributions par contributeur")
    parser.add_argument("--end", help="Date de fin au format YYYY-MM-DD (défaut: aujourd'hui)")

    args = parser.parse_args()
    res = get_mean_contributor_balance(args.pages, args.lang, args.users, args.contribs, args.end)

    print("=== RÉSULTATS FINAUX ===")
    for page, val in res.items():
        print(f"{page}: {val:.3f}")