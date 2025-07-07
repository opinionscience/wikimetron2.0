# revert_risk_metric_parallel.py
"""
Version parallélisée de la métrique revert_risk avec plusieurs niveaux d'optimisation
"""
from typing import List, Dict, Tuple, Optional
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import logging
from dataclasses import dataclass

# Configuration
INFERENCE_URL = (
    "https://api.wikimedia.org/service/lw/inference/v1/"
    "models/revertrisk-language-agnostic:predict"
)
HEADERS = {
    "User-Agent": "RevertRiskBot/1.0 (aurelien@opsci.ai)",
    "Content-Type": "application/json",
}

# Configuration de parallélisation
MAX_CONCURRENT_PAGES = 4      # Pages traitées simultanément
MAX_CONCURRENT_REVISIONS = 8  # Révisions par page traitées simultanément
RATE_LIMIT_DELAY = 0.05      # Réduit de 0.1 à 0.05s
REQUEST_TIMEOUT = 10         # Timeout plus court
MAX_RETRIES = 2              # Nombre de tentatives

logger = logging.getLogger(__name__)

@dataclass
class RevisionResult:
    rev_id: int
    probability: float
    success: bool = True
    error: Optional[str] = None

class RevisionProcessor:
    """Gestionnaire de traitement parallèle des révisions"""
    
    def __init__(self, lang: str, verbose: bool = False):
        self.lang = lang
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def process_single_revision(self, rev_id: int) -> RevisionResult:
        """Traite une seule révision avec gestion d'erreurs et retry"""
        for attempt in range(MAX_RETRIES + 1):
            try:
                payload = {"rev_id": rev_id, "lang": self.lang}
                
                response = self.session.post(
                    INFERENCE_URL, 
                    json=payload, 
                    timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                
                output = response.json().get("output", {})
                probability = output.get("probabilities", {}).get("true", 0.0)
                
                if self.verbose:
                    logger.info(f"rev_id: {rev_id} revert risk: {probability:.3f}")
                
                # Rate limiting adaptatif
                if attempt == 0:  # Pas de délai sur le premier essai réussi
                    time.sleep(RATE_LIMIT_DELAY)
                
                return RevisionResult(rev_id, probability, True)
                
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES:
                    wait_time = (attempt + 1) * 0.5  # Backoff exponentiel
                    logger.warning(f"Tentative {attempt + 1} échouée pour rev_id {rev_id}, retry dans {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Échec définitif pour rev_id {rev_id}: {e}")
                    return RevisionResult(rev_id, 0.0, False, str(e))
            except Exception as e:
                logger.error(f"Erreur inattendue pour rev_id {rev_id}: {e}")
                return RevisionResult(rev_id, 0.0, False, str(e))
        
        return RevisionResult(rev_id, 0.0, False, "Max retries exceeded")

def _fetch_rev_ids_optimized(title: str, start: str, end: str, lang: str) -> List[int]:
    """Version optimisée de la récupération des rev_ids avec session réutilisable"""
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "titles": title,
        "prop": "revisions",
        "rvprop": "ids",
        "rvstart": f"{end}T23:59:59Z",
        "rvend": f"{start}T00:00:00Z",
        "rvlimit": "max",
    }
    
    rev_ids: List[int] = []
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        while True:
            resp = session.get(api, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", [])
            
            for page in pages:
                for rev in page.get("revisions", []):
                    rev_ids.append(rev["revid"])
            
            cont = data.get("continue")
            if not cont:
                break
            params.update(cont)
            
        logger.info(f"Récupéré {len(rev_ids)} révisions pour {title}")
        return rev_ids
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des révisions pour {title}: {e}")
        return []
    finally:
        session.close()

def process_page_revisions_parallel(
    title: str, 
    rev_ids: List[int], 
    lang: str, 
    verbose: bool = False
) -> float:
    """Traite les révisions d'une page en parallèle"""
    if not rev_ids:
        return 0.0
    
    processor = RevisionProcessor(lang, verbose)
    results: List[RevisionResult] = []
    
    logger.info(f"Traitement de {len(rev_ids)} révisions pour {title} avec {MAX_CONCURRENT_REVISIONS} threads")
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REVISIONS) as executor:
        # Soumettre tous les jobs
        future_to_rev = {
            executor.submit(processor.process_single_revision, rev_id): rev_id 
            for rev_id in rev_ids
        }
        
        # Récupérer les résultats
        for future in as_completed(future_to_rev):
            try:
                result = future.result(timeout=REQUEST_TIMEOUT + 5)
                results.append(result)
            except Exception as e:
                rev_id = future_to_rev[future]
                logger.error(f"Erreur lors du traitement de la révision {rev_id}: {e}")
                results.append(RevisionResult(rev_id, 0.0, False, str(e)))
    
    # Calculer la moyenne des probabilités
    successful_results = [r for r in results if r.success]
    if not successful_results:
        logger.warning(f"Aucune révision traitée avec succès pour {title}")
        return 0.0
    
    avg_probability = sum(r.probability for r in successful_results) / len(successful_results)
    success_rate = len(successful_results) / len(results) * 100
    
    logger.info(f"{title}: {len(successful_results)}/{len(results)} révisions traitées ({success_rate:.1f}%), moyenne: {avg_probability:.3f}")
    
    return avg_probability

def process_single_page(
    page_data: Tuple[str, str, str, str, bool]
) -> Tuple[str, float]:
    """Traite une seule page (fonction pour la parallélisation des pages)"""
    title, start, end, lang, verbose = page_data
    
    logger.info(f"Début traitement de {title}")
    start_time = time.time()
    
    try:
        # 1. Récupérer les révisions
        rev_ids = _fetch_rev_ids_optimized(title, start, end, lang)
        
        if not rev_ids:
            logger.warning(f"Aucune révision trouvée pour {title}")
            return (title, 0.0)
        
        # 2. Traiter les révisions en parallèle
        avg_risk = process_page_revisions_parallel(title, rev_ids, lang, verbose)
        
        duration = time.time() - start_time
        logger.info(f"✅ {title} terminé en {duration:.2f}s - risque moyen: {avg_risk:.3f}")
        
        return (title, avg_risk)
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ Erreur pour {title} après {duration:.2f}s: {e}")
        return (title, 0.0)

def get_revert_risk_parallel(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr",
    verbose: bool = False,
    max_concurrent_pages: int = MAX_CONCURRENT_PAGES
) -> pd.Series:
    """
    Version parallélisée principale avec parallélisation à deux niveaux:
    1. Pages traitées en parallèle
    2. Révisions de chaque page traitées en parallèle
    """
    logger.info(f"Début traitement parallèle de {len(pages)} pages avec {max_concurrent_pages} threads")
    start_time = time.time()
    
    results: Dict[str, float] = {}
    
    # Préparer les données pour la parallélisation
    page_data_list = [
        (title, start, end, lang, verbose) 
        for title in pages
    ]
    
    # Traitement parallèle des pages
    with ThreadPoolExecutor(max_workers=max_concurrent_pages) as executor:
        future_to_page = {
            executor.submit(process_single_page, page_data): page_data[0]
            for page_data in page_data_list
        }
        
        for future in as_completed(future_to_page):
            page_title = future_to_page[future]
            try:
                title, risk_score = future.result(timeout=300)  # 5 minutes max par page
                results[title] = risk_score
            except Exception as e:
                logger.error(f"Échec critique pour {page_title}: {e}")
                results[page_title] = 0.0
    
    total_time = time.time() - start_time
    logger.info(f"Traitement parallèle terminé en {total_time:.2f}s")
    
    return pd.Series(results, name="revert_risk")

# Version avec batching pour très gros volumes
def get_revert_risk_batched(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr",
    verbose: bool = False,
    batch_size: int = 10
) -> pd.Series:
    """Version avec traitement par batches pour éviter les timeouts sur de gros volumes"""
    logger.info(f"Traitement par batches de {batch_size} pages")
    
    all_results = {}
    
    for i in range(0, len(pages), batch_size):
        batch_pages = pages[i:i+batch_size]
        logger.info(f"Traitement du batch {i//batch_size + 1}: pages {i+1}-{min(i+batch_size, len(pages))}")
        
        batch_results = get_revert_risk_parallel(
            batch_pages, start, end, lang, verbose, 
            max_concurrent_pages=min(4, len(batch_pages))
        )
        
        all_results.update(batch_results.to_dict())
        
        # Pause entre les batches pour éviter la surcharge
        if i + batch_size < len(pages):
            time.sleep(2)
    
    return pd.Series(all_results, name="revert_risk")

# Fonction de compatibilité avec l'API existante
def get_revert_risk(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr",
    verbose: bool = False
) -> pd.Series:
    """Interface de compatibilité - utilise automatiquement la version parallélisée"""
    if len(pages) > 20:
        logger.info("Grand nombre de pages détecté, utilisation du mode batched")
        return get_revert_risk_batched(pages, start, end, lang, verbose)
    else:
        return get_revert_risk_parallel(pages, start, end, lang, verbose)

# ───────────── CLI pour test rapide ─────────────
if __name__ == "__main__":
    import argparse
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(
        description="Calcul parallélisé du taux de revert d'une ou plusieurs pages Wikipedia"
    )
    parser.add_argument("pages", nargs="+", help="Titres d'articles Wikipedia")
    parser.add_argument("--start", default="2025-04-21", help="Date de début YYYY-MM-DD")
    parser.add_argument("--end", default="2025-05-21", help="Date de fin YYYY-MM-DD")
    parser.add_argument("--lang", default="fr", help="Code langue wiki (ex. 'en')")
    parser.add_argument("--verbose", action="store_true", help="Affiche le score de chaque révision")
    parser.add_argument("--batch-size", type=int, default=10, help="Taille des batches pour gros volumes")
    parser.add_argument("--max-page-workers", type=int, default=MAX_CONCURRENT_PAGES, 
                       help="Nombre de pages traitées simultanément")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        print("### Mode verbose activé : détails des scores de chaque révision.")

    start_time = time.time()
    
    if len(args.pages) > args.batch_size:
        series = get_revert_risk_batched(
            args.pages, args.start, args.end, args.lang, 
            args.verbose, args.batch_size
        )
    else:
        series = get_revert_risk_parallel(
            args.pages, args.start, args.end, args.lang, 
            args.verbose, args.max_page_workers
        )
    
    total_time = time.time() - start_time
    
    print(f"\n### Taux de revert (0–1) - Calculé en {total_time:.2f}s\n")
    print(series.round(3).to_markdown())
    
    # Statistiques de performance
    print(f"\n### Statistiques de performance")
    print(f"Pages traitées: {len(args.pages)}")
    print(f"Temps total: {total_time:.2f}s")
    print(f"Temps moyen par page: {total_time/len(args.pages):.2f}s")
