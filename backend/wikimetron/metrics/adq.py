
"""
Calcule le score de qualité "officiel" (bannière d'évaluation) d'un article Wikipédia.
Supporte français et anglais (d'autres langues peuvent être ajoutées facilement).

Usage CLI :
    python quality_score_pipe.py "Emmanuel Macron" "ChatGPT" --lang en
    python quality_score_pipe.py "Emmanuel Macron" --lang fr
"""

import requests
import pandas as pd
import re
import argparse

HEADERS = {"User-Agent": "WikiScoreSimple/1.1"}

LEVEL_SCORES_FR = {
    "adq": 0,
    "ba": 0.2,
    "a": 0.4,
    "b": 0.6,
    "bd": 0.8,
    "ébauche": 1
}
LEVEL_SCORES_EN = {
    "fa": 0,           # Featured Article
    "a": 0.2,
    "ga": 0.3,         # Good Article
    "b": 0.5,
    "c": 0.7,
    "start": 0.85,
    "stub": 1
}
TALK_PREFIXES = {
    "fr": "Discussion:",
    "en": "Talk:",
    "de": "Diskussion:"
}

def get_talk_wikicode(title: str, lang="fr") -> str:
    prefix = TALK_PREFIXES.get(lang, "Talk:")
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": f"{prefix}{title}",
        "prop": "revisions",
        "rvprop": "content",
        "formatversion": "2"
    }
    r = requests.get(api_url, headers={"User-Agent": HEADERS["User-Agent"]}, params=params, timeout=10)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return ""
    return pages[0].get("revisions", [{}])[0].get("content", "")

def extract_level(wikicode: str, lang="fr") -> str:
    """
    Extrait le niveau de qualité depuis le wikicode de la page de discussion,
    adapté pour fr (avancement=...) et en (class=...).
    """
    if lang == "en":
        # Ex : {{WikiProject ... |class=FA|...}}
        match = re.search(r"\|\s*class\s*=\s*([^\s|}]+)", wikicode, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    else:
        # Ex : {{Wikiprojet ... |avancement=ADQ|...}}
        match = re.search(r"avancement\s*=\s*([^|}]+)", wikicode, re.IGNORECASE)
        if match:
            lvl = match.group(1).strip().lower()
            return {
                'article de qualité':'adq', 'bon article':'ba', 'avancé':'a',
                'bien construit':'b', 'bon début':'bd', 'ébauche':'ébauche',
                'adq':'adq','ba':'ba','a':'a','b':'b','bd':'bd','e':'ébauche'
            }.get(lvl, lvl)
    return ""

def get_score_for_article(title: str, lang="fr") -> float:
    """
    Retourne le score officiel (ou 0.0 si non évalué) pour un article,
    pour la langue voulue (fr, en...).
    """
    wikicode = get_talk_wikicode(title, lang=lang)
    level = extract_level(wikicode, lang=lang)
    if lang == "en":
        return LEVEL_SCORES_EN.get(level, 0.0)
    else:
        return LEVEL_SCORES_FR.get(level, 0.0)

def get_official_quality_score(pages, lang="fr"):
    """
    Fonction prête pour le pipeline :
    Retourne une Series indexée par titre, valeur entre 0 (excellence) et 1 (ébauche).
    """
    scores = {}
    for title in pages:
        try:
            scores[title] = get_score_for_article(title, lang=lang)
        except Exception:
            scores[title] = 0.0
    return pd.Series(scores, name="official_quality_score")
def get_adq_score(pages, lang="fr"):
    """
    Version pipeline : retourne une Series indexée par page,
    valeur entre 0 (ADQ) et 1 (ébauche ou non évalué).
    """
    
    scores = {}
    for title in pages:
        try:
            scores[title] = get_score_for_article(title, lang=lang)
        except Exception:
            scores[title] = 0.0
    return pd.Series(scores, name="adq_score")
# ========== CLI de test rapide ==========

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score de qualité Wikipedia (pipeline ready)")
    parser.add_argument("pages", nargs="+", help="Titres d'articles Wikipédia")
    parser.add_argument("--lang", default="fr", help="Langue Wikipedia (fr, en...)")
    args = parser.parse_args()

    print(f"Test du score de qualité officiel sur {len(args.pages)} article(s) [lang={args.lang}]\n")

    t0 = pd.Timestamp.now()
    res = get_official_quality_score(args.pages, lang=args.lang)
    t1 = pd.Timestamp.now()

    for title, score in res.items():
        print(f"{title:30s} : {score:.2f}")

    print(f"\n✅ Terminé en {t1-t0}\n")
