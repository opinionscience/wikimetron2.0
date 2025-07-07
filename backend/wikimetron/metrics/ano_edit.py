#!/usr/bin/env python3
"""
Score d'éditions anonymes sur Wikipedia.
Renvoie une pd.Series : +0.1 par édition IP (max 1.0) pour chaque page.
"""

from typing import List
import pandas as pd
import requests
import time

UA = "AnonEditScoreBot/mini"
BASE_DELAY = 0.1

def get_anon_edit_score_series(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "en"
) -> pd.Series:
    """
    Pour chaque page : score = 0.1 * nb_anon, max 1.0
    """
    results = {}
    for title in pages:
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "titles": title,
            "rvstart": f"{end}T23:59:59Z",
            "rvend": f"{start}T00:00:00Z",
            "rvprop": "user|flags",
            "rvlimit": "max",
            "formatversion": "2"
        }
        nb_anon = nb_total = 0
        cont = True
        while cont:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            data = r.json()
            pages_json = data.get("query", {}).get("pages", [])
            for page in pages_json:
                for rev in page.get("revisions", []):
                    nb_total += 1
                    if "anon" in rev:
                        nb_anon += 1
            cont = data.get("continue")
            if cont:
                params.update(cont)
                time.sleep(BASE_DELAY)
            else:
                break
        score = min(nb_anon * 0.1, 1.0) if nb_total > 0 else 0.0
        results[title] = round(score, 3)
    return pd.Series(results, name="anon_edit_score")

# CLI minimaliste
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Score d'éditions anonymes Wikipédia (pipeline)")
    parser.add_argument("pages", nargs="+", help="Titres des pages Wikipédia")
    parser.add_argument("--start", default="2024-01-01", help="Début (YYYY-MM-DD)")
    parser.add_argument("--end",   default="2024-12-31", help="Fin (YYYY-MM-DD)")
    parser.add_argument("--lang",  default="fr", help="Langue Wikipedia (fr, en...)")
    args = parser.parse_args()

    series = get_anon_edit_score_series(args.pages, args.start, args.end, args.lang)
    print(series.round(3).to_markdown())
