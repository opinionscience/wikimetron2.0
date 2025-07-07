#!/usr/bin/env python3
"""
Calcule la moyenne du déséquilibre ajouts/suppressions des X derniers contributeurs pour chaque page Wikipédia.
Usage :
    python user_balance_metric.py "Page1" "Page2" --lang fr --users 10 --contribs 100
"""

import requests
import pandas as pd
import argparse
import time

HEADERS = {"User-Agent": "UserBalanceAnalyzer/1.0 (pipeline@example.com)"}

def get_user_contributions(user, lang="fr", limit=100):
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
    try:
        r = requests.get(api_url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("query", {}).get("usercontribs", [])
    except Exception:
        return []

def get_recent_editors(page, lang="fr", limit=10):
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": page,
        "prop": "revisions",
        "rvprop": "user",
        "rvlimit": min(limit*3, 500),
        "formatversion": "2"
    }
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
            if user and user not in seen:
                seen.add(user)
                users.append(user)
            if len(users) >= limit:
                break
        return users
    except Exception:
        return []

def get_mean_contributor_balance(pages, lang="fr", num_users=10, num_contributions=100):
    results = {}
    for page in pages:
        editors = get_recent_editors(page, lang, num_users)
        scores = []
        for user in editors:
            contribs = get_user_contributions(user, lang, num_contributions)
            adds = sum(1 for c in contribs if c.get("sizediff", 0) > 0)
            dels = sum(1 for c in contribs if c.get("sizediff", 0) < 0)
            total = adds + dels
            score = abs(adds - dels) / total if total > 0 else 0.0
            scores.append(score)
            time.sleep(0.1)  # Retire si tu veux aller + vite
        results[page] = float(pd.Series(scores).mean()) if scores else 0.0
    return pd.Series(results, name="mean_contributor_balance")

# ==== CLI minimaliste ====

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score moyen de balance contributeurs Wikipedia")
    parser.add_argument("pages", nargs="+", help="Titres des pages Wikipedia")
    parser.add_argument("--lang", default="fr", help="Langue (fr, en, ...)")
    parser.add_argument("--users", type=int, default=10, help="Nb contributeurs à analyser")
    parser.add_argument("--contribs", type=int, default=100, help="Nb contributions par contributeur")
    args = parser.parse_args()

    res = get_mean_contributor_balance(args.pages, args.lang, args.users, args.contribs)
    for page, val in res.items():
        print(f"{page}: {val:.3f}")
