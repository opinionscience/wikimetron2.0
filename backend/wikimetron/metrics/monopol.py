#!/usr/bin/env python3
""" 
Script simplifié pour analyser la monopolisation d'une page Wikipedia.
Renvoie la proportion de contributions du contributeur le plus actif parmi les N dernières révisions.
Ajout de logs pour mesurer le temps d'exécution.
"""
import requests
import argparse
import time
from collections import Counter
import pandas as pd
from datetime import datetime

HEADERS = {"User-Agent": "MonopolizationSimple/1.0"}

def parse_date(date_str):
    if not date_str:
        return None
    
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise ValueError(f"Format de date invalide. Utilisez YYYY-MM-DD (ex: 2024-01-01)")

def get_monopolization_score(title: str, lang: str = "fr", limit: int = 10, end=None):
    """
    Récupère les dernières `limit` révisions de la page `title` et calcule la proportion
    de contributions du contributeur le plus actif.
    Retourne (top_user, top_count, total_count, proportion_float).
    """
    api_start = time.time()
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "revisions",
        "rvprop": "user",
        "rvlimit": limit,
        "formatversion": "2"
    }
    
    if end:
        params["rvstart"] = end
    
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    data = resp.json()
    api_elapsed = time.time() - api_start
    print(f"[LOG] Requête API pour '{title}' exécutée en {api_elapsed:.2f}s")

    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        raise ValueError(f"Page '{title}' introuvable.")

    revisions = pages[0].get("revisions", [])
    if not revisions:
        raise ValueError(f"Aucune révision trouvée pour '{title}'.")

    # Comptage des contributions par utilisateur
    counts = Counter(rev.get("user") for rev in revisions if rev.get("user"))
    total = sum(counts.values())
    if total == 0:
        return None, 0, 0, 0.0

    top_user, top_count = counts.most_common(1)[0]
    proportion = top_count / total
    return top_user, top_count, total, proportion

def get_monopolization_scores(pages, lang="fr", limit=10, end=None):
    """
    Version pipeline : retourne une Series indexée par page,
    valeur = proportion du top contributeur sur les N dernières révisions.
    """
    # Parser la date seulement si elle est fournie
    parsed_date = None
    if end:
        parsed_date = parse_date(end)
    
    results = {}
    for page in pages:
        try:
            _, _, _, proportion = get_monopolization_score(page, lang, limit, parsed_date)
            results[page] = proportion
        except Exception:
            results[page] = 0.0
    return pd.Series(results, name="monopolization_score")

def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(
        description="Analyse la monopolisation d'une page Wikipedia."
    )
    parser.add_argument("title", help="Titre de la page Wikipedia à analyser")
    parser.add_argument("--lang", default="fr", help="Code langue (défaut: fr)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Nombre de révisions à analyser (défaut: 100)")
    parser.add_argument("--end", help="Date de fin au format YYYY-MM-DD")
    args = parser.parse_args()

    # Parser la date seulement si elle est fournie
    parsed_date = None
    if args.end:
        try:
            parsed_date = parse_date(args.end)
        except ValueError as e:
            print(f"Erreur: {e}")
            return

    try:
        user, count, total, score = get_monopolization_score(
            args.title, args.lang, args.limit, parsed_date
        )
        if user is None:
            print(f"Aucune contribution valide pour '{args.title}'.")
        else:
            pct = round(score * 100, 1)
            print(f"Page : {args.title}")
            print(f"Total révisions : {total}")
            print(f"Contributeur dominant : {user} ({count} contribs, {pct}% du total)")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        elapsed = time.time() - start_time
        print(f"⏱️ Temps total d'exécution : {elapsed:.2f}s")

if __name__ == "__main__":
    main()