# pageviews.py - Version corrigée avec fonction normalisée pour le pipeline
"""
Module pageviews avec fonction get_pageview_spikes_normalized pour le pipeline.
Cette version ajoute la fonction normalisée nécessaire au pipeline.
"""

from __future__ import annotations
from typing import List, Dict
import pandas as pd
import requests
from datetime import datetime, timedelta
import argparse
import time
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

API_ROOT = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
UA = {"User-Agent": "PageviewSpike/1.3 (opsci)"}

# ─────────────────────────── helpers ────────────────────────────

def _date_fmt(date: str | datetime) -> str:
    """YYYYMMDD pour l'API REST."""
    if isinstance(date, datetime):
        return date.strftime("%Y%m%d")
    return date.replace("-", "")


def _fetch_series(title: str, start: str, end: str, lang: str) -> pd.Series:
    """Série quotidienne de pages vues (index : datetime, valeur : int)."""
    start_time = time.time()
    logger.info(f"Début récupération données pour '{title}' ({lang})")
    
    title_enc = requests.utils.quote(title.replace(" ", "_"), safe="")
    url = (
        f"{API_ROOT}/{lang}.wikipedia/all-access/user/"
        f"{title_enc}/daily/{_date_fmt(start)}/{_date_fmt(end)}"
    )
    
    try:
        request_start = time.time()
        r = requests.get(url, headers=UA, timeout=20)
        request_duration = time.time() - request_start
        logger.info(f"Requête API pour '{title}': {request_duration:.3f}s")
        
        r.raise_for_status()
        
        parse_start = time.time()
        items = r.json().get("items", [])
        data = {pd.to_datetime(i["timestamp"][:8]): i["views"] for i in items}
        serie = pd.Series(data, name=title).sort_index()
        parse_duration = time.time() - parse_start
        
        total_duration = time.time() - start_time
        logger.info(f"'{title}': {len(serie)} points récupérés - "
                   f"parsing: {parse_duration:.3f}s, total: {total_duration:.3f}s")
        
        return serie
        
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"Erreur pour '{title}' après {total_duration:.3f}s: {e}")
        return pd.Series(name=title)

# ─────────────────────────── API publiques ─────────────────────

def get_pageviews_timeseries(pages: List[str], start: str, end: str, lang: str = "en") -> Dict[str, pd.Series]:
    """Renvoie un dict {title: Series} pour debug ou graphiques."""
    start_time = time.time()
    logger.info(f"Début récupération des séries temporelles pour {len(pages)} page(s)")
    
    result = {}
    for i, page in enumerate(pages, 1):
        page_start = time.time()
        result[page] = _fetch_series(page, start, end, lang)
        page_duration = time.time() - page_start
        logger.info(f"Page {i}/{len(pages)} traitée en {page_duration:.3f}s")
    
    total_duration = time.time() - start_time
    logger.info(f"Toutes les séries temporelles récupérées en {total_duration:.3f}s")
    
    return result


def get_pageview_spikes(pages: List[str], start: str, end: str, lang: str = "en") -> pd.Series:
    """Score "spike" seul (float) - VERSION NON NORMALISÉE."""
    start_time = time.time()
    logger.info("Calcul des scores spike uniquement")
    
    result = get_pageview_spike_detail(pages, start, end, lang)["spike"]
    
    duration = time.time() - start_time
    logger.info(f"Scores spike calculés en {duration:.3f}s")
    
    return result


def get_pageview_spikes_normalized(pages: List[str], start: str, end: str, lang: str = "en") -> pd.Series:
    """
    Score "spike" normalisé pour le pipeline (référence = 37.2002).
    
    Args:
        pages: Liste des titres de pages
        start: Date de début au format "YYYY-MM-DD" 
        end: Date de fin au format "YYYY-MM-DD"
        lang: Code langue
    
    Returns:
        pd.Series avec les spikes normalisés par page
    """
    start_time = time.time()
    logger.info("Calcul des scores spike NORMALISÉS pour le pipeline")
    
    detail_df = get_pageview_spike_detail(pages, start, end, lang)
    result = detail_df["spike_normalized"]
    
    duration = time.time() - start_time
    logger.info(f"Scores spike normalisés calculés en {duration:.3f}s")
    
    return result


def get_pageview_spike_detail(
    pages: List[str], start: str, end: str, lang: str = "en"
) -> pd.DataFrame:
    """DataFrame `[spike, peak_day, peak_views, spike_normalized]` par article."""
    overall_start = time.time()
    logger.info(f"Début analyse détaillée des spikes pour {len(pages)} page(s)")
    logger.info(f"Période: {start} à {end}, langue: {lang}")
    
    # Récupération des données
    fetch_start = time.time()
    timeseries_data = get_pageviews_timeseries(pages, start, end, lang)
    fetch_duration = time.time() - fetch_start
    logger.info(f"Données récupérées en {fetch_duration:.3f}s")
    
    # Calcul des spikes
    calc_start = time.time()
    rows: Dict[str, Dict[str, object]] = {}
    
    for title, serie in timeseries_data.items():
        page_calc_start = time.time()
        
        if serie.empty:
            logger.warning(f"Aucune donnée pour '{title}'")
            rows[title] = {
                "spike": 0.0, 
                "peak_day": None, 
                "peak_views": 0,
                "spike_normalized": 0.0
            }
            continue

        med = serie.median()            # trafic médian (filtre les outliers)
        mx  = serie.max()               # trafic maximum (jour du pic)
        spike = (mx - med) / (med + 1)  # normalisation (voir docstring)
        peak_day = serie.idxmax().date().isoformat()

        # Spike normalisé avec référence
        SPIKE_REFERENCE = 37.2002
        spike_normalized = min(1.0, spike / SPIKE_REFERENCE)


        rows[title] = {
            "spike": round(spike, 4),
            "peak_day": peak_day,
            "peak_views": int(mx),
            "spike_normalized": round(spike_normalized, 4),
        }
        
        page_calc_duration = time.time() - page_calc_start
        logger.info(f"'{title}': spike={spike:.4f}, spike_norm={spike_normalized:.4f}, "
                   f"pic={mx} vues le {peak_day} (médiane={med:.0f}) - "
                   f"calculé en {page_calc_duration:.3f}s")

    calc_duration = time.time() - calc_start
    overall_duration = time.time() - overall_start
    
    result_df = pd.DataFrame.from_dict(rows, orient="index")
    
    logger.info(f"Calculs terminés en {calc_duration:.3f}s")
    logger.info(f"Temps total d'exécution: {overall_duration:.3f}s")
    logger.info(f"Temps moyen par page: {overall_duration/len(pages):.3f}s")
    
    return result_df

# ───────────────────────────  CLI ──────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Spike score + date + vues max des pages Wikipédia.")
    ap.add_argument("pages", nargs="+", help="Titres d'articles")
    ap.add_argument("--start", help="YYYY-MM-DD (défaut = aujourd'hui -30j)")
    ap.add_argument("--end",   help="YYYY-MM-DD (défaut = aujourd'hui)")
    ap.add_argument("--lang",  default="fr", help="Code langue (en, fr, …)")
    ap.add_argument("--verbose", "-v", action="store_true", help="Logs détaillés")
    ap.add_argument("--normalized", "-n", action="store_true", 
                    help="Afficher les scores normalisés pour le pipeline")
    ns = ap.parse_args()

    # Configuration du niveau de logging
    if ns.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Mode verbose activé")

    script_start = time.time()
    logger.info("=== DÉBUT DU SCRIPT ===")
    
    today = datetime.utcnow().date()
    end   = ns.end or today.isoformat()
    start = ns.start or (today - timedelta(days=30)).isoformat()

    logger.info(f"Paramètres: pages={ns.pages}, période={start} à {end}, lang={ns.lang}")

    try:
        if ns.normalized:
            # Test de la fonction normalisée
            print("\n" + "="*60)
            print("SCORES NORMALISÉS (pour pipeline):")
            print("="*60)
            
            spikes_norm = get_pageview_spikes_normalized(ns.pages, start, end, ns.lang)
            print(spikes_norm.to_markdown())
        
        else:
            # Affichage standard complet
            df = get_pageview_spike_detail(ns.pages, start, end, ns.lang)
            print("\n" + "="*60)
            print("RÉSULTATS COMPLETS:")
            print("="*60)
            print(df.to_markdown())
        
        script_duration = time.time() - script_start
        print(f"\n⏱️  Temps total d'exécution: {script_duration:.3f}s")
        logger.info(f"=== FIN DU SCRIPT - {script_duration:.3f}s ===")
        
    except Exception as e:
        script_duration = time.time() - script_start
        logger.error(f"Erreur fatale après {script_duration:.3f}s: {e}")
        raise