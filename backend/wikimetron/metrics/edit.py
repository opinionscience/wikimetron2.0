# edit_parallel.py
"""
Version parallélisée du module pour calculer les spikes d'édition sur les pages Wikipedia.
Optimisations: parallélisation des pages + requêtes API optimisées.
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Optional
import pandas as pd
import requests
import statistics
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

UA = "EditTrendBot/2.0 (opsci)"
SPIKE_REF = 22  # Référence pour normalisation : spike=22 devient 1

# Configuration de parallélisation
MAX_CONCURRENT_PAGES = 6    # Pages traitées simultanément
MAX_CONCURRENT_DAYS = 4     # Jours par page traités simultanément (optionnel)
REQUEST_TIMEOUT = 15        # Timeout des requêtes
MAX_RETRIES = 2            # Nombre de tentatives

@dataclass
class EditData:
    page: str
    daily_counts: List[int]
    spike: float
    spike_normalized: float
    peak_day_index: Optional[int]
    peak_edits: int
    total_edits: int
    success: bool = True
    error: Optional[str] = None

class EditProcessor:
    """Gestionnaire de traitement parallèle des éditions"""
    
    def __init__(self, lang: str = "fr", editor_type: str = "user"):
        self.lang = lang
        self.editor_type = editor_type
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA, 
            "Accept": "application/json"
        })
    
    def fetch_daily_edits_optimized(self, page: str, start_date: datetime, end_date: datetime) -> List[int]:
        """
        Version optimisée qui récupère toutes les révisions d'une période puis les groupe par jour
        Au lieu de faire un appel par jour, fait un seul appel pour toute la période
        """
        url = f"https://{self.lang}.wikipedia.org/w/api.php"
        start_iso = start_date.strftime("%Y-%m-%dT00:00:00Z")
        end_iso = (end_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        
        params = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "titles": page,
            "rvlimit": "max",
            "rvstart": end_iso,
            "rvend": start_iso,
            "rvprop": "timestamp|user|ids"
        }
        
        all_revisions = []
        retries = 0
        
        # Récupérer toutes les révisions de la période
        while retries < MAX_RETRIES:
            try:
                response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                if response.status_code != 200:
                    retries += 1
                    continue
                    
                data = response.json()
                if "error" in data:
                    logger.warning(f"Erreur API pour {page}: {data.get('error', {}).get('info', 'Erreur inconnue')}")
                    break
                    
                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    break
                    
                page_data = next(iter(pages.values()))
                if "missing" in page_data:
                    logger.warning(f"Page '{page}' introuvable")
                    break
                    
                revisions = page_data.get("revisions", [])
                for rev in revisions:
                    user = rev.get("user", "")
                    timestamp = rev.get("timestamp", "")
                    
                    # Filtrer selon le type d'éditeur
                    if self.editor_type == "user":
                        if not ("bot" in user.lower() or user.startswith("MediaWiki")):
                            all_revisions.append({
                                "timestamp": timestamp,
                                "user": user
                            })
                    elif self.editor_type == "all":
                        all_revisions.append({
                            "timestamp": timestamp,
                            "user": user
                        })
                
                # Gestion de la pagination
                if "continue" not in data:
                    break
                params.update(data["continue"])
                retries = 0  # Reset des retries si succès
                
            except Exception as e:
                logger.warning(f"Erreur réseau pour {page}: {e}")
                retries += 1
                if retries >= MAX_RETRIES:
                    break
                time.sleep(0.5 * retries)  # Backoff
        
        # Grouper par jour
        return self._group_revisions_by_day(all_revisions, start_date, end_date)
    
    def _group_revisions_by_day(self, revisions: List[Dict], start_date: datetime, end_date: datetime) -> List[int]:
        """Groupe les révisions par jour"""
        # Créer un dictionnaire pour compter par jour
        daily_counts = {}
        curr_date = start_date
        
        # Initialiser tous les jours à 0
        while curr_date <= end_date:
            daily_counts[curr_date.strftime("%Y-%m-%d")] = 0
            curr_date += timedelta(days=1)
        
        # Compter les révisions par jour
        for rev in revisions:
            try:
                rev_datetime = datetime.fromisoformat(rev["timestamp"].replace("Z", "+00:00"))
                rev_date = rev_datetime.date().strftime("%Y-%m-%d")
                if rev_date in daily_counts:
                    daily_counts[rev_date] += 1
            except Exception as e:
                logger.debug(f"Erreur parsing timestamp {rev.get('timestamp', '')}: {e}")
        
        # Retourner la liste ordonnée
        result = []
        curr_date = start_date
        while curr_date <= end_date:
            date_str = curr_date.strftime("%Y-%m-%d")
            result.append(daily_counts.get(date_str, 0))
            curr_date += timedelta(days=1)
        
        return result
    
    def compute_spike(self, daily_counts: List[int]) -> Tuple[float, Optional[int], int]:
        """Calcule le spike d'édition à partir des comptages quotidiens"""
        if not daily_counts or sum(daily_counts) == 0:
            return 0.0, None, 0
        
        med = statistics.median(daily_counts)
        mx = max(daily_counts)
        spike = (mx - med) / (med + 1)
        peak_idx = daily_counts.index(mx)
        
        return spike, peak_idx, mx
    
    def process_single_page(self, page: str, start_date: datetime, end_date: datetime) -> EditData:
        """Traite une seule page"""
        logger.info(f"Début traitement éditions pour {page}")
        start_time = time.time()
        
        try:
            # Récupérer les données d'édition
            daily_counts = self.fetch_daily_edits_optimized(page, start_date, end_date)
            
            # Calculer le spike
            spike, peak_idx, peak_edits = self.compute_spike(daily_counts)
            spike_normalized = min(1.0, spike / SPIKE_REF) 
            total_edits = sum(daily_counts)
            
            duration = time.time() - start_time
            logger.info(f"✅ {page} terminé en {duration:.2f}s - spike: {spike:.3f}, total: {total_edits}")
            
            return EditData(
                page=page,
                daily_counts=daily_counts,
                spike=spike,
                spike_normalized=spike_normalized,
                peak_day_index=peak_idx,
                peak_edits=peak_edits,
                total_edits=total_edits,
                success=True
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Erreur pour {page} après {duration:.2f}s: {e}")
            return EditData(
                page=page,
                daily_counts=[],
                spike=0.0,
                spike_normalized=0.0,
                peak_day_index=None,
                peak_edits=0,
                total_edits=0,
                success=False,
                error=str(e)
            )

def get_edit_spikes_parallel(
    pages: List[str], 
    start: str, 
    end: str, 
    lang: str = "fr",
    max_workers: int = MAX_CONCURRENT_PAGES
) -> pd.Series:
    """
    Version parallélisée du calcul des spikes d'édition
    
    Args:
        pages: Liste des titres de pages
        start: Date de début au format "YYYY-MM-DD"
        end: Date de fin au format "YYYY-MM-DD"
        lang: Code langue
        max_workers: Nombre de threads parallèles
    
    Returns:
        pd.Series avec les spikes normalisés par page
    """
    logger.info(f"Calcul parallèle des spikes d'édition pour {len(pages)} page(s) avec {max_workers} workers")
    start_time = time.time()
    
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    
    processor = EditProcessor(lang, "user")
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre tous les jobs
        future_to_page = {
            executor.submit(processor.process_single_page, page, start_date, end_date): page
            for page in pages
        }
        
        # Récupérer les résultats
        for future in as_completed(future_to_page):
            page = future_to_page[future]
            try:
                edit_data = future.result(timeout=120)  # 2 minutes max par page
                results[page] = edit_data.spike_normalized
            except Exception as e:
                logger.error(f"Échec critique pour {page}: {e}")
                results[page] = 0.0
    
    total_time = time.time() - start_time
    logger.info(f"Calcul parallèle terminé en {total_time:.2f}s")
    
    return pd.Series(results)

def get_edit_spike_detail_parallel(
    pages: List[str], 
    start: str, 
    end: str, 
    lang: str = "fr",
    max_workers: int = MAX_CONCURRENT_PAGES
) -> pd.DataFrame:
    """
    Version parallélisée détaillée qui retourne toutes les métriques d'édition
    
    Returns:
        DataFrame avec colonnes: spike, spike_normalized, peak_day, peak_edits, total_edits
    """
    logger.info(f"Calcul parallèle détaillé des spikes d'édition pour {len(pages)} page(s)")
    start_time = time.time()
    
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    
    processor = EditProcessor(lang, "user")
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre tous les jobs
        future_to_page = {
            executor.submit(processor.process_single_page, page, start_date, end_date): page
            for page in pages
        }
        
        # Récupérer les résultats
        for future in as_completed(future_to_page):
            page = future_to_page[future]
            try:
                edit_data = future.result(timeout=120)
                
                peak_day = ""
                if edit_data.peak_day_index is not None:
                    peak_day = (start_date + timedelta(days=edit_data.peak_day_index)).strftime("%Y-%m-%d")
                
                results[page] = {
                    "spike": edit_data.spike,
                    "spike_normalized": edit_data.spike_normalized,
                    "peak_day": peak_day,
                    "peak_edits": edit_data.peak_edits,
                    "total_edits": edit_data.total_edits,
                    "success": edit_data.success
                }
                
            except Exception as e:
                logger.error(f"Échec critique pour {page}: {e}")
                results[page] = {
                    "spike": 0.0,
                    "spike_normalized": 0.0,
                    "peak_day": "",
                    "peak_edits": 0,
                    "total_edits": 0,
                    "success": False
                }
    
    total_time = time.time() - start_time
    logger.info(f"Calcul parallèle détaillé terminé en {total_time:.2f}s")
    
    return pd.DataFrame.from_dict(results, orient="index")

# Version avec batching pour gros volumes
def get_edit_spikes_batched(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr",
    batch_size: int = 10
) -> pd.Series:
    """Version avec traitement par batches pour éviter les timeouts sur de gros volumes"""
    logger.info(f"Traitement par batches de {batch_size} pages pour les spikes d'édition")
    
    all_results = {}
    
    for i in range(0, len(pages), batch_size):
        batch_pages = pages[i:i+batch_size]
        logger.info(f"Traitement du batch {i//batch_size + 1}: pages {i+1}-{min(i+batch_size, len(pages))}")
        
        batch_results = get_edit_spikes_parallel(
            batch_pages, start, end, lang, 
            max_workers=min(MAX_CONCURRENT_PAGES, len(batch_pages))
        )
        
        all_results.update(batch_results.to_dict())
        
        # Pause entre les batches
        if i + batch_size < len(pages):
            time.sleep(1)
    
    return pd.Series(all_results)

# Fonctions de compatibilité avec l'API existante
def get_edit_spikes(pages: List[str], start: str, end: str, lang: str = "fr") -> pd.Series:
    """Interface de compatibilité - utilise automatiquement la version parallélisée"""
    if len(pages) > 15:
        logger.info("Grand nombre de pages détecté, utilisation du mode batched")
        return get_edit_spikes_batched(pages, start, end, lang)
    else:
        return get_edit_spikes_parallel(pages, start, end, lang)

def get_edit_spike_detail(pages: List[str], start: str, end: str, lang: str = "fr") -> pd.DataFrame:
    """Interface de compatibilité pour la version détaillée"""
    if len(pages) > 15:
        logger.info("Grand nombre de pages détecté pour détail, traitement par batches")
        # Pour le mode détaillé, on peut traiter par plus petits batches
        return get_edit_spike_detail_batched(pages, start, end, lang, batch_size=8)
    else:
        return get_edit_spike_detail_parallel(pages, start, end, lang)

def get_edit_spike_detail_batched(pages: List[str], start: str, end: str, lang: str = "fr", batch_size: int = 8) -> pd.DataFrame:
    """Version détaillée avec batching"""
    all_results = {}
    
    for i in range(0, len(pages), batch_size):
        batch_pages = pages[i:i+batch_size]
        batch_df = get_edit_spike_detail_parallel(batch_pages, start, end, lang)
        all_results.update(batch_df.to_dict('index'))
        
        if i + batch_size < len(pages):
            time.sleep(1)
    
    return pd.DataFrame.from_dict(all_results, orient="index")

# Test CLI si exécuté directement
if __name__ == "__main__":
    import argparse
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Test du module edit parallélisé")
    parser.add_argument("pages", nargs="+", help="Titres des pages")
    parser.add_argument("--start", default="2025-06-01", help="Date début")
    parser.add_argument("--end", default="2025-06-29", help="Date fin")
    parser.add_argument("--lang", default="fr", help="Langue")
    parser.add_argument("--workers", type=int, default=MAX_CONCURRENT_PAGES, help="Nombre de workers")
    parser.add_argument("--batch-size", type=int, default=10, help="Taille des batches")
    parser.add_argument("--detail", action="store_true", help="Affichage détaillé")
    args = parser.parse_args()
    
    start_time = time.time()
    
    if args.detail:
        print("=== Mode détaillé ===")
        detail = get_edit_spike_detail(args.pages, args.start, args.end, args.lang)
        print(detail.to_markdown())
    else:
        print("=== Mode spikes normalisés ===")
        spikes = get_edit_spikes(args.pages, args.start, args.end, args.lang)
        print(spikes.to_markdown())
    
    total_time = time.time() - start_time
    print(f"\n### Traitement terminé en {total_time:.2f}s")
    print(f"Pages traitées: {len(args.pages)}")
    print(f"Temps moyen par page: {total_time/len(args.pages):.2f}s")
