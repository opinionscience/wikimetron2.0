#!/usr/bin/env python3
# ref.py

"""
Citation Gap Metric for Wikipedia Articles
=========================================

Ce module calcule un score de "citation gap" (écart de sourçage) pour un ensemble de pages Wikipédia.
Le score mesure le nombre de citations manquantes (templates "Citation needed" ou {{cn}}) selon un barème :
    - 1 citation manquante = 0.02
    - 2 citations manquantes = 0.04
    - etc., jusqu’à un maximum de 1.0
Si la page ne contient aucune référence, le score est fixé à 1.0 (manque total de sourçage).

Fonction principale à utiliser dans un pipeline :
    get_citation_gap(pages: list[str]) -> pandas.Series

Exemple d'utilisation :
    >>> from ref import get_citation_gap
    >>> get_citation_gap(["Emmanuel Macron", "Guerre d’Algérie"])


"""

from __future__ import annotations
from typing import List
import pandas as pd
import requests
import re
import time

API = "https://fr.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "CitationGapBot/1.0 (contact: opsci)"}

# Regex pour repérer les templates de citation manquante (ex : {{refnec}})
_PATTERN_CIT_NEEDED = re.compile(r'refnec', re.I)
# Regex pour repérer les balises de référence
_PATTERN_REF = re.compile(r"<ref[ >]", re.I)

def _fetch_wikitext(title: str) -> str:
    """
    Récupère le wikitext brut d’une page Wikipédia.

    Args:
        title (str): Titre de la page Wikipédia.

    Returns:
        str: Wikitext de la page (ou chaîne vide en cas d’erreur).
    """
    start_time = time.perf_counter()
    print(f"[TIMING] Début récupération wikitext pour '{title}'...")

    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": title,
        "rvslots": "main",
        "rvprop": "content",
        "redirects": 1,
    }
    try:
        r = requests.get(API, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        page = next(iter(data["query"]["pages"].values()))
        if "revisions" not in page:
            elapsed = time.perf_counter() - start_time
            print(f"[TIMING] Récupération wikitext pour '{title}' terminée en {elapsed:.3f}s (aucune révision)")
            return ""
        result = page["revisions"][0]["slots"]["main"].get("*", "")
        elapsed = time.perf_counter() - start_time
        print(f"[TIMING] Récupération wikitext pour '{title}' terminée en {elapsed:.3f}s ({len(result)} caractères)")
        return result
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        print(f"[TIMING] Erreur lors de la récupération wikitext pour '{title}' après {elapsed:.3f}s: {e}")
        return ""

def _citation_gap_from_text(wikitext: str) -> float:
    """
    Calcule le score de citation gap à partir du wikitext.

    Le score augmente de 0.02 pour chaque citation manquante
    (template "Citation needed" ou "{{refnec}}"), jusqu’à 1.0 max.
    Si aucune référence présente, retourne 1.0.

    Args:
        wikitext (str): Texte brut de la page Wikipédia.

    Returns:
        float: Score citation gap (entre 0 et 1).
    """
    start_time = time.perf_counter()
    print(f"[TIMING] Début calcul citation gap sur texte de {len(wikitext)} caractères...")

    refs = len(_PATTERN_REF.findall(wikitext))
    needs = len(_PATTERN_CIT_NEEDED.findall(wikitext))
    if refs == 0:
        elapsed = time.perf_counter() - start_time
        print(f"[TIMING] Calcul citation gap terminé en {elapsed:.3f}s (aucune ref)")
        return 1.0  # Aucun ref = gap maximal

    # Score progressif : 0.02 par citation manquante, max 1.0
    result = min(1.0, needs * 0.1)
    elapsed = time.perf_counter() - start_time
    print(f"[TIMING] Calcul citation gap terminé en {elapsed:.3f}s")
    return result

def get_citation_gap(pages: List[str]) -> pd.Series:
    """
    Calcule le score de citation gap pour une liste de pages Wikipédia.

    Args:
        pages (List[str]): Liste des titres de pages Wikipédia.

    Returns:
        pandas.Series: Série indexée par titre, avec le score de chaque page.
    """
    start_time = time.perf_counter()
    print(f"[TIMING] Début traitement de {len(pages)} page(s)...")

    data = {}
    for i, p in enumerate(pages, 1):
        page_start_time = time.perf_counter()
        print(f"[TIMING] Traitement page {i}/{len(pages)}: '{p}'")

        wikitext = _fetch_wikitext(p)
        citation_gap = _citation_gap_from_text(wikitext)
        refs = len(_PATTERN_REF.findall(wikitext))
        needs = len(_PATTERN_CIT_NEEDED.findall(wikitext))

        page_elapsed = time.perf_counter() - page_start_time
        print(f"Sur la page '{p}', il y a {needs} citations manquantes pour {refs} citations au total.")
        print(f"[TIMING] Page '{p}' traitée en {page_elapsed:.3f}s")

        data[p] = citation_gap

    total_elapsed = time.perf_counter() - start_time
    print(f"[TIMING] Traitement total terminé en {total_elapsed:.3f}s pour {len(pages)} page(s)")
    print(f"[TIMING] Temps moyen par page: {total_elapsed/len(pages):.3f}s")

    return pd.Series(data, name="citation_gap")

if __name__ == "__main__":
    import sys
    pages = sys.argv[1:] or ["Kupa"]

    script_start_time = time.perf_counter()
    print(f"[TIMING] Démarrage du script...")

    result = get_citation_gap(pages)
    print(result)

    script_elapsed = time.perf_counter() - script_start_time
    print(f"[TIMING] Script terminé en {script_elapsed:.3f}s")
