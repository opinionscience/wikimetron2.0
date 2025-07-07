# protection.py
"""
Module pour évaluer la sévérité de la protection de pages Wikipédia.
Version adaptée pour le pipeline avec fonction normalisée.
"""

from __future__ import annotations
from typing import List
import requests
import sys
import time
import logging
import pandas as pd

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "ProtectionRating/1.2 (pipeline@opsci.com)"}

LEVEL_SCORE = {
    "": 0,
    "autoconfirmed": 0.25,
    "editautopatrolprotected": 0.25,
    "editextendedsemiprotected": 0.5,
    "extendedconfirmed": 0.5,
    "templateeditor": 0.75,
    "editautoreviewprotected": 0.75,
    "sysop": 1,
}

LABEL = {
    0: "libre", 
    0.25: "semi", 
    0.5: "extended",
    0.75: "spécialisé", 
    1: "plein"
}

def _score(level: str) -> float:
    """Convertit un niveau de protection en score numérique."""
    return LEVEL_SCORE.get(level, 2)

def _fetch_edit_protection(title: str, lang: str) -> tuple[str, float]:
    """
    Récupère les informations de protection d'édition pour une page.
    
    Args:
        title: Titre de la page
        lang: Code langue
    
    Returns:
        Tuple (description, score_max)
    """
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "info",
        "inprop": "protection",
        "format": "json",
        "formatversion": "2",
    }

    t0 = time.perf_counter()
    r = requests.get(api, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    
    pdata = r.json()["query"]["pages"][0]
    elapsed = time.perf_counter() - t0
    logger.info(f"API {lang}.wikipedia.org → '{title}' en {elapsed:.3f}s")

    # Vérifier si la page existe
    if "missing" in pdata:
        logger.warning(f"Page '{title}' introuvable")
        return "page introuvable", 0.0

    prot_edit = [p for p in pdata.get("protection", []) if p["type"] == "edit"]
    if not prot_edit:
        return "aucune protection (edit)", 0.0

    desc = ", ".join(f"{p['type']}:{p['level']}" for p in prot_edit)
    max_score = max(_score(p["level"]) for p in prot_edit)
    return desc, max_score

def get_protection_scores(pages: List[str], lang: str = "fr") -> pd.Series:
    """
    Retourne les scores de protection normalisés pour le pipeline.
    
    Args:
        pages: Liste des titres de pages
        lang: Code langue
    
    Returns:
        pd.Series avec les scores de protection (0-1) par page
    """
    logger.info(f"Calcul des scores de protection pour {len(pages)} page(s)")
    
    results = {}
    
    for i, page in enumerate(pages, 1):
        logger.info(f"Traitement page {i}/{len(pages)}: {page}")
        
        try:
            desc, score = _fetch_edit_protection(page, lang)
            results[page] = score
            
            severity = LABEL.get(score, "?")
            logger.info(f"'{page}': protection={severity} (score={score:.2f}) - {desc}")
            
        except Exception as e:
            logger.error(f"Erreur pour la page '{page}': {e}")
            results[page] = 0.0
        
        # Pause pour ne pas surcharger l'API
        time.sleep(0.3)
    
    return pd.Series(results)

def protection_rating(pages: List[str], lang: str = "fr") -> pd.DataFrame:
    """
    Version complète qui retourne toutes les informations de protection.
    Compatible avec le script original.
    
    Args:
        pages: Liste des titres de pages
        lang: Code langue
    
    Returns:
        DataFrame avec colonnes: Page, Protection (edit), Score, Sévérité
    """
    logger.info(f"Analyse complète de protection pour {len(pages)} page(s) en [{lang}]")
    
    rows = []
    for pg in pages:
        try:
            desc, score = _fetch_edit_protection(pg, lang)
        except Exception as e:
            desc, score = f"erreur ({e})", -1
            logger.error(f"Erreur sur '{pg}': {e}")
        
        rows.append({
            "Page": pg,
            "Protection (edit)": desc,
            "Score": score,
            "Sévérité": LABEL.get(score, "?")
        })
        
        # Pause pour ne pas surcharger l'API
        time.sleep(0.3)
    
    return pd.DataFrame(rows).set_index("Page")

# Test CLI si exécuté directement
if __name__ == "__main__":
    import argparse
    
    # Maintenir la compatibilité avec l'ancien script
    if len(sys.argv) >= 3 and not sys.argv[1].startswith('-'):
        # Mode legacy : python protection.py fr "Page1" "Page2"
        t_start = time.perf_counter()
        lang, *titles = sys.argv[1:]
        logger.info(f"Mode legacy - Démarrage pour {len(titles)} page(s) en [{lang}]")
        df = protection_rating(titles, lang)
        print(df.to_markdown())
        total = time.perf_counter() - t_start
        logger.info(f"Terminé en {total:.3f} secondes")
    else:
        # Mode avec arguments nommés
        parser = argparse.ArgumentParser(description="Test du module protection.py")
        parser.add_argument("pages", nargs="+", help="Titres des pages")
        parser.add_argument("--lang", default="fr", help="Code langue")
        parser.add_argument("--scores-only", "-s", action="store_true", 
                           help="Afficher seulement les scores pour le pipeline")
        args = parser.parse_args()
        
        if args.scores_only:
            # Test de la fonction pour le pipeline
            print("Scores de protection (normalisés):")
            scores = get_protection_scores(args.pages, args.lang)
            print(scores.to_markdown())
        else:
            # Test de la version complète
            print("Analyse complète de protection:")
            detail = protection_rating(args.pages, args.lang)
            print(detail.to_markdown())