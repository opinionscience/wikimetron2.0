#!/usr/bin/env python3
# ref.py

"""
Citation Gap Metric for Wikipedia Articles (Multilingual)
========================================================

Ce module calcule un score de "citation gap" (écart de sourçage) pour un ensemble de pages Wikipédia
dans différentes langues. Le score mesure le nombre de citations manquantes selon un barème :
    - 1 citation manquante = 0.02
    - 2 citations manquantes = 0.04
    - etc., jusqu'à un maximum de 1.0
Si la page ne contient aucune référence, le score est fixé à 1.0 (manque total de sourçage).

Fonction principale à utiliser dans un pipeline :
    get_citation_gap(pages: list[str], lang: str = "fr") -> pandas.Series
"""

from __future__ import annotations
from typing import List, Dict, Pattern
import pandas as pd
import requests
import re
import time

# Configuration multilingue pour les templates de citation manquante
CITATION_TEMPLATES: Dict[str, List[str]] = {
    "fr": ["refnec", "référence nécessaire", "citation needed", "cn"],
    "en": ["citation needed", "cn", "fact", "verify", "clarification needed"],
    "de": ["belege fehlen", "quelle fehlt", "citation needed", "cn"],
    "es": ["cita requerida", "cr", "verificar"],
    "it": ["citazione necessaria", "citation needed", "cn", "senza fonte"],
    "pt": ["carece de fontes", "citation needed", "cn", "verificar"],
    "ru": ["нет источника", "citation needed", "источник", "cn"],
    "ja": ["要出典", "citation needed", "cn", "出典"],
    "zh": ["来源请求", "citation needed", "cn", "需要来源"],
    "ar": ["مصدر مطلوب", "citation needed", "cn", "بحاجة لمصدر"],
    "nl": ["bron", "citation needed", "cn", "verificatie"],
    "sv": ["källa behövs", "citation needed", "cn", "källa"],
    "no": ["referanse trengs", "citation needed", "cn", "kilde"],
    "da": ["kilde mangler", "citation needed", "cn", "kilde"],
    "fi": ["lähde", "citation needed", "cn", "tarkista"],
}

# Fallback pour les langues non listées
DEFAULT_TEMPLATES = ["citation needed", "cn", "refnec", "référence nécessaire"]

HEADERS = {"User-Agent": "CitationGapBot/1.0 (contact: opsci)"}

# Regex pour repérer les balises de référence (universelle)
_PATTERN_REF = re.compile(r"<ref[ >]", re.I)


def _get_citation_patterns(lang: str) -> Pattern[str]:
    """
    Retourne le pattern regex pour détecter les templates de citation manquante
    sous forme wikitext ({{template ...}}).
    """
    templates = CITATION_TEMPLATES.get(lang.lower(), DEFAULT_TEMPLATES)
    alternation = "|".join(re.escape(t) for t in templates)
    pattern_string = r"\{\{\s*(?:%s)\b[^}]*\}\}" % alternation
    return re.compile(pattern_string, re.IGNORECASE)


def find_missing_citation_templates(wikitext: str, lang: str = "fr") -> List[str]:
    """
    Retourne la liste des appels de templates 'citation manquante' trouvés
    dans le wikitext (ex: ['{{cita requerida}}', '{{référence nécessaire|date=...}}']).
    """
    citation_pattern = _get_citation_patterns(lang)
    return citation_pattern.findall(wikitext)


def _get_api_url(lang: str) -> str:
    return f"https://{lang.lower()}.wikipedia.org/w/api.php"


def _fetch_wikitext(title: str, lang: str = "fr") -> str:
    start_time = time.perf_counter()
    api_url = _get_api_url(lang)
    print(f"[TIMING] Début récupération wikitext pour '{title}' ({lang})...")

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
        r = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        page = next(iter(data["query"]["pages"].values()))
        if "revisions" not in page:
            elapsed = time.perf_counter() - start_time
            print(f"[TIMING] Aucun contenu trouvé pour '{title}' ({lang}) ({elapsed:.3f}s)")
            return ""
        result = page["revisions"][0]["slots"]["main"].get("*", "")
        elapsed = time.perf_counter() - start_time
        print(f"[TIMING] Wikitext récupéré pour '{title}' ({lang}) en {elapsed:.3f}s ({len(result)} caractères)")
        return result
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        print(f"[TIMING] Erreur '{title}' ({lang}) après {elapsed:.3f}s: {e}")
        return ""


def _citation_gap_from_text(wikitext: str, lang: str = "fr") -> float:
    start_time = time.perf_counter()
    print(f"[TIMING] Début calcul citation gap ({lang})...")

    refs = len(_PATTERN_REF.findall(wikitext))
    needs = len(find_missing_citation_templates(wikitext, lang))

    if refs == 0:
        elapsed = time.perf_counter() - start_time
        print(f"[TIMING] Calcul terminé ({lang}) en {elapsed:.3f}s (aucune ref)")
        return 1.0

    result = min(1.0, needs * 0.1)
    elapsed = time.perf_counter() - start_time
    print(f"[TIMING] Calcul terminé ({lang}) en {elapsed:.3f}s, score={result}")
    return result


def get_citation_gap(pages: List[str], lang: str = "fr") -> pd.Series:
    start_time = time.perf_counter()
    print(f"[TIMING] Début traitement de {len(pages)} page(s) en {lang.upper()}...")

    templates = CITATION_TEMPLATES.get(lang.lower(), DEFAULT_TEMPLATES)
    print(f"[INFO] Templates surveillés ({lang}): {templates}")

    data = {}
    for i, p in enumerate(pages, 1):
        page_start_time = time.perf_counter()
        print(f"[TIMING] Page {i}/{len(pages)}: '{p}' ({lang})")

        wikitext = _fetch_wikitext(p, lang)
        citation_gap = _citation_gap_from_text(wikitext, lang)

        refs = len(_PATTERN_REF.findall(wikitext))
        occurrences = find_missing_citation_templates(wikitext, lang)
        needs = len(occurrences)

        print(f"Sur '{p}' ({lang}): {needs} citation(s) manquante(s) pour {refs} référence(s).")
        if occurrences:
            preview = [o[:100].replace("\n", " ") + ("..." if len(o) > 100 else "") for o in occurrences[:3]]
            print("[DEBUG] Exemples:", preview)

        page_elapsed = time.perf_counter() - page_start_time
        print(f"[TIMING] Page '{p}' traitée en {page_elapsed:.3f}s")

        data[p] = citation_gap

    total_elapsed = time.perf_counter() - start_time
    print(f"[TIMING] Traitement terminé ({lang}), {len(pages)} page(s) en {total_elapsed:.3f}s")
    return pd.Series(data, name="citation_gap")


def get_supported_languages() -> List[str]:
    return list(CITATION_TEMPLATES.keys())


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    lang = "es"
    pages = []

    i = 0
    while i < len(args):
        if args[i] == "--lang" and i + 1 < len(args):
            lang = args[i + 1]
            i += 2
        elif args[i] == "--help":
            print("Usage: python ref.py [--lang LANG] [page1] [page2] ...")
            print(f"Langues supportées: {', '.join(get_supported_languages())}")
            sys.exit(0)
        else:
            pages.append(args[i])
            i += 1

    if not pages:
        if lang == "es":
            pages = ["Escocia"]
        elif lang == "en":
            pages = ["Python (programming language)"]
        elif lang == "de":
            pages = ["Deutschland"]
        else:
            pages = ["Main Page"]

    script_start_time = time.perf_counter()
    print(f"[TIMING] Script lancé ({lang.upper()})")
    print(f"[INFO] Langues supportées: {', '.join(get_supported_languages())}")

    result = get_citation_gap(pages, lang)
    print(f"\n=== RÉSULTATS ({lang.upper()}) ===")
    print(result)

    script_elapsed = time.perf_counter() - script_start_time
    print(f"\n[TIMING] Script terminé en {script_elapsed:.3f}s")
