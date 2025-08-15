#!/usr/bin/env python3
"""
Score d'éditions anonymes sur Wikipedia.
Pour chaque page : +0.1 par édition IP **ou par compte temporaire** (max = 1.0).

Un « compte temporaire » est identifié par un nom d’utilisateur commençant par
un tilde (~) suivi :
  • de l’année sur 4 chiffres  
  • puis d’un ou plusieurs groupes de 1 à 5 chiffres séparés par des tirets.

Exemples valides : ~2024-0000 ; ~2025-00000-000 ; ~2025-00000-00000-0.
"""

from typing import List
import re
import time
import requests
import pandas as pd

UA = "AnonEditScoreBot/mini"
BASE_DELAY = 0.1

# --- Détection des comptes temporaires --------------------------------------
_TEMP_USER_RE = re.compile(r"^~\d{4}(?:-\d{1,5})+$")


def _is_temp_user(username: str) -> bool:
    """Renvoie True si *username* correspond au format d’un compte temporaire."""
    return bool(_TEMP_USER_RE.match(username))


# --- Fonction principale -----------------------------------------------------
def get_anon_edit_score_series(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "en",
) -> pd.Series:
    """
    Calcule, pour chaque page, un score = 0.1 × nb_éditions_anonymes (IP ou temporaires),
    plafonné à 1.0.
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
            "formatversion": "2",
        }

        nb_anon = nb_total = 0

        while True:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            data = r.json()

            for page in data.get("query", {}).get("pages", []):
                for rev in page.get("revisions", []):
                    nb_total += 1
                    user = rev.get("user", "")
                    if "anon" in rev or _is_temp_user(user):
                        nb_anon += 1

            if "continue" in data:
                params.update(data["continue"])
                time.sleep(BASE_DELAY)
            else:
                break

        results[title] = round(min(nb_anon * 0.1, 1.0) if nb_total else 0.0, 3)

    return pd.Series(results, name="anon_edit_score")


# --- CLI minimaliste ---------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Score d'éditions anonymes Wikipédia (pipeline)"
    )
    parser.add_argument("pages", nargs="+", help="Titres des pages Wikipédia")
    parser.add_argument("--start", default="2025-07-15", help="Début (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-07-31", help="Fin (YYYY-MM-DD)")
    parser.add_argument("--lang", default="fr", help="Langue Wikipedia (fr, en...)")
    args = parser.parse_args()

    series = get_anon_edit_score_series(args.pages, args.start, args.end, args.lang)
    print(series.round(3).to_markdown())
