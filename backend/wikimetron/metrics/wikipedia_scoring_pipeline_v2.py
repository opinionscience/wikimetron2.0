# wikipedia_scoring_pipeline_v2.py  – v2.0 (avec parallélisation)
"""
Pipeline de scoring Wikipedia avec collecte parallélisée des métriques.
Calcule Heat / Quality / Risk + score sensitivity par page.
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Callable, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ───────────────────────────  Poids ────────────────────────────
HEAT_W = {
    "pageview_spike": 5,    # Spike de trafic (normalisé)
    "edit_spike": 4,  
    "revert_risk": 3,# Spike d'éditions (normalisé) 
    "protection_level": 2,
    "talk_intensity": 1,    # Intensité page de discussion
      # Niveau de protection
}

QUAL_W = {
    "citation_gap": 6,
    "blacklist_share": 5,
    "event_imbalance": 4,
    "recency_score": 3,
    'adq_score': 2,  
    "domain_dominance": 50,  # Domination du domaine
}

RISK_W = {
    "anon_edit": 4,  # Part des éditions anonymes
    "mean_contributor_balance": 3,  # Équilibre des contributeurs
    "monopolization_score": 2,  # Monopolisation des contributions
    "avg_activity_score": 1,  # Activité moyenne des contributeurs
}

GLOB_W = {
    "heat": 1,
    "quality": 1,
    "risk": 1
}

MAX_WORKERS =  16 # Nombre de threads parallèles

@dataclass
class ScoringResult:
    heat: pd.Series
    quality: pd.Series
    risk: pd.Series
    sensitivity: pd.Series
    heat_raw: pd.Series
    quality_raw: pd.Series
    risk_raw: pd.Series

class MetricError(Exception):
    """Exception personnalisée pour les erreurs de métriques"""
    pass

def safe_metric_executor(metric_func: Callable, metric_name: str, pages: List[str], *args) -> pd.Series:
    """
    Exécute une métrique de manière sécurisée avec gestion d'erreurs.
    """
    try:
        start_time = time.time()
        logger.info(f"Début collecte métrique: {metric_name}")
        
        result = metric_func(pages, *args)
        
        # Validation du résultat
        if isinstance(result, pd.Series):
            result = result
        elif isinstance(result, dict):
            result = pd.Series(result)
        elif hasattr(result, 'Score'):  # Pour protection_rating
            result = result["Score"].astype(float)
        else:
            raise MetricError(f"Format de retour invalide pour {metric_name}: {type(result)}")
        
        # Vérification des valeurs manquantes
        result = result.reindex(pages).fillna(0.0)
        
        duration = time.time() - start_time
        logger.info(f"✓ {metric_name} terminée en {duration:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"✗ Erreur dans {metric_name}: {str(e)}")
        # Retourner des valeurs par défaut en cas d'erreur
        return pd.Series(index=pages, data=0.0, name=metric_name)


def collect_metrics_parallel(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr",
    max_workers: int = MAX_WORKERS
) -> Dict[str, pd.Series]:
    """
    Collecte toutes les métriques en parallèle.
    """
    # Import des fonctions de métriques
    from pageviews import get_pageview_spikes_normalized
    from edit import get_edit_spikes
    from protection import get_protection_scores
    from ref import get_citation_gap
    from balance import get_event_imbalance_events_only
    from last_edit import get_recency_score
    from adq import  get_adq_score
    from user_balance_metric import get_mean_contributor_balance
    from monopol import get_monopolization_scores
    from quantity import get_avg_activity_score
    from domination import get_domain_dominance
    from taille_talk import discussion_score
    from ano_edit import get_anon_edit_score_series
    from blacklist_metric import get_blacklist_share
    from revert_risk import get_revert_risk
    
    # Configuration des métriques à collecter
    metric_configs = [
        ("pageview_spike", get_pageview_spikes_normalized, (pages, start, end, lang)), #lang agnostic
        ("edit_spike", get_edit_spikes, (pages, start, end, lang)),#lang agnostic
        ("protection_level", get_protection_scores, (pages, lang)), 
        ("citation_gap", get_citation_gap, (pages,)), #lang agnostic
        ("event_imbalance", get_event_imbalance_events_only, (pages, start, end, lang)), #lang agnostic
        ("recency_score", get_recency_score, (pages, lang)),#lang agnostic
        ("adq_score", get_adq_score, (pages, lang)), 
        ("mean_contributor_balance", get_mean_contributor_balance, (pages, lang)),#lang agnostic
        ("monopolization_score", get_monopolization_scores, (pages, lang)),#lang agnostic
        ("avg_activity_score", get_avg_activity_score, (pages, lang)),#lang agnostic
        ("domain_dominance", get_domain_dominance, (pages, lang)),  #lang agnostic
        ("talk_intensity", discussion_score, (pages,start, end)),
        ("anon_edit", get_anon_edit_score_series, (pages, start, end, lang)),  #lang agnostic
        ("blacklist_share", get_blacklist_share, (pages, "blacklist.csv", lang)), #lang agnostic
        ("revert_risk", get_revert_risk, (pages, start, end, lang)) #lang agnostic
    ]
    
    logger.info(f"Démarrage collecte parallèle de {len(metric_configs)} métriques pour {len(pages)} pages")
    start_time = time.time()
    
    results = {}
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Soumission de tous les jobs
        future_to_metric = {}
        for metric_name, metric_func, args in metric_configs:
            future = executor.submit(safe_metric_executor, metric_func, metric_name, *args)
            future_to_metric[future] = metric_name
        
        # Collecte des résultats au fur et à mesure
        for future in as_completed(future_to_metric):
            metric_name = future_to_metric[future]
            try:
                result = future.result(timeout=30)  # Timeout de 30s par métrique
                results[metric_name] = result
            except Exception as e:
                logger.error(f"Échec critique pour {metric_name}: {e}")
                results[metric_name] = pd.Series(index=pages, data=0.0, name=metric_name)
    
    total_time = time.time() - start_time
    success_count = len([r for r in results.values() if r.sum() > 0])
    logger.info(f"Collecte terminée en {total_time:.2f}s - {success_count}/{len(metric_configs)} métriques récupérées")
    
    return results

def compute_scores(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr",
    max_workers: int = MAX_WORKERS
) -> Tuple[ScoringResult, pd.DataFrame]:
    """
    Fonction principale : collecte parallèle + calcul des scores.
    """
    logger.info(f"Début du pipeline de scoring pour {len(pages)} pages")
    pipeline_start = time.time()
    
    # 1. Collecte parallèle des métriques
    raw_metrics = collect_metrics_parallel(pages, start, end, lang, max_workers)
    
    # 2. Conversion en DataFrame
    metrics = pd.DataFrame(raw_metrics).apply(pd.to_numeric, errors="coerce").fillna(0)
    logger.info(f"DataFrame des métriques créé: {metrics.shape}")
    
    # 3. Agrégation par pondération
    available_heat_metrics = [m for m in HEAT_W.keys() if m in metrics.columns]
    available_qual_metrics = [m for m in QUAL_W.keys() if m in metrics.columns]
    available_risk_metrics = [m for m in RISK_W.keys() if m in metrics.columns]
    
    logger.info(f"Métriques Heat disponibles: {available_heat_metrics}")
    logger.info(f"Métriques Quality disponibles: {available_qual_metrics}")
    logger.info(f"Métriques Risk disponibles: {available_risk_metrics}")
    
    # Calcul Heat: scores bruts et normalisés
    if available_heat_metrics:
        heat_weights = pd.Series({m: HEAT_W[m] for m in available_heat_metrics})
        heat_raw = (metrics[available_heat_metrics] * heat_weights).sum(axis=1)
        heat = heat_raw / heat_weights.sum()  # Version normalisée
    else:
        heat_raw = pd.Series(index=metrics.index, data=0.0)
        heat = pd.Series(index=metrics.index, data=0.0)
    
    # Calcul Quality: scores bruts et normalisés
    if available_qual_metrics:
        qual_weights = pd.Series({m: QUAL_W[m] for m in available_qual_metrics})
        quality_raw = (metrics[available_qual_metrics] * qual_weights).sum(axis=1)
        quality = quality_raw / qual_weights.sum()  # Version normalisée
    else:
        quality_raw = pd.Series(index=metrics.index, data=0.0)
        quality = pd.Series(index=metrics.index, data=0.0)
    
    # Calcul Risk: scores bruts et normalisés
    if available_risk_metrics:
        risk_weights = pd.Series({m: RISK_W[m] for m in available_risk_metrics})
        risk_raw = (metrics[available_risk_metrics] * risk_weights).sum(axis=1)
        risk = risk_raw / risk_weights.sum()  # Version normalisée
    else:
        risk_raw = pd.Series(index=metrics.index, data=0.0)
        risk = pd.Series(index=metrics.index, data=0.0)
    
    # 4. Score final: moyenne simple des 3 catégories normalisées
    sensitivity = (heat + quality + risk) / 3
    
    total_time = time.time() - pipeline_start
    logger.info(f"Pipeline terminé en {total_time:.2f}s")
    
    return ScoringResult(heat, quality, risk, sensitivity, heat_raw, quality_raw, risk_raw), metrics

# CLI pour tests
if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser(description="Pipeline de scoring Wikipedia parallélisé")
    ap.add_argument("pages", nargs="+", help="Liste des pages à analyser")
    ap.add_argument("--start", default="2025-04-21", help="Date de début")
    ap.add_argument("--end", default="2025-05-21", help="Date de fin")
    ap.add_argument("--lang", default="fr", help="Langue Wikipedia")
    ap.add_argument("--workers", type=int, default=MAX_WORKERS, help="Nombre de workers parallèles")
    ap.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")
    
    args = ap.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        scores, detail = compute_scores(args.pages, args.start, args.end, args.lang, args.workers)
        
        print("\n" + "="*60)
        print(f"RAPPORT DE SCORING - {len(args.pages)} pages analysées")
        print("="*60)
        
        print("\n### Métriques brutes")
        print(detail.round(3).to_markdown(tablefmt="grid"))
        
        # Tableaux par catégorie avec détail des métriques
        available_heat_metrics = [m for m in HEAT_W.keys() if m in detail.columns]
        available_qual_metrics = [m for m in QUAL_W.keys() if m in detail.columns]
        available_risk_metrics = [m for m in RISK_W.keys() if m in detail.columns]
        
        if available_heat_metrics:
            print("\n### Détail catégorie HEAT")
            heat_detail = detail[available_heat_metrics].copy()
            heat_weights = pd.Series({m: HEAT_W[m] for m in available_heat_metrics})
            
            # Créer un tableau avec métriques, poids et contributions
            heat_table = pd.DataFrame()
            for metric in available_heat_metrics:
                heat_table[f'{metric}'] = detail[metric]
                
            
            # Ajouter ligne des poids
            poids_row = {}
            for metric in available_heat_metrics:
                poids_row[f'{metric}'] = f'(poids: {HEAT_W[metric]})'
                poids_row[f'{metric}_×{HEAT_W[metric]}'] = 'contribution'
            heat_table.loc['POIDS'] = poids_row
            
            print(heat_table.to_markdown(tablefmt="grid"))
        
        if available_qual_metrics:
            print("\n### Détail catégorie QUALITY")
            qual_detail = detail[available_qual_metrics].copy()
            
            # Créer un tableau avec métriques, poids et contributions
            qual_table = pd.DataFrame()
            for metric in available_qual_metrics:
                qual_table[f'{metric}'] = detail[metric]
                
            
            # Ajouter ligne des poids
            poids_row = {}
            for metric in available_qual_metrics:
                poids_row[f'{metric}'] = f'(poids: {QUAL_W[metric]})'
                poids_row[f'{metric}_×{QUAL_W[metric]}'] = 'contribution'
            qual_table.loc['POIDS'] = poids_row
                
            print(qual_table.to_markdown(tablefmt="grid"))
        
        if available_risk_metrics:
            print("\n### Détail catégorie RISK")
            risk_detail = detail[available_risk_metrics].copy()
            
            # Créer un tableau avec métriques, poids et contributions
            risk_table = pd.DataFrame()
            for metric in available_risk_metrics:
                risk_table[f'{metric}'] = detail[metric]
                
            
            # Ajouter ligne des poids
            poids_row = {}
            for metric in available_risk_metrics:
                poids_row[f'{metric}'] = f'(poids: {RISK_W[metric]})'
                poids_row[f'{metric}_×{RISK_W[metric]}'] = 'contribution'
            risk_table.loc['POIDS'] = poids_row
                
            print(risk_table.to_markdown(tablefmt="grid"))
        
        # Scores finaux normalisés
        final = pd.DataFrame({
            "heat": scores.heat.round(3),
            "quality": scores.quality.round(3),
            "risk": scores.risk.round(3),
            "sensitivity": scores.sensitivity.round(3)
        }, index=args.pages)
        
        print("\n### Scores finaux (normalisés)")
        print(final.to_markdown(tablefmt="grid"))
        
        # Scores bruts (somme pondérée pure)
        final_raw = pd.DataFrame({
            "heat_raw": scores.heat_raw.round(3),
            "quality_raw": scores.quality_raw.round(3),
            "risk_raw": scores.risk_raw.round(3),
            "sensitivity_raw": scores.heat_raw.round(3) +
                                scores.quality_raw.round(3) +
                                scores.risk_raw.round(3)
        }, index=args.pages)
        
        print("\n### Scores bruts (somme pondérée)")
        print(final_raw.to_markdown(tablefmt="grid"))
        
        # Top pages par sensibilité
        top_sensitive = final.nlargest(min(5, len(final)), 'sensitivity')
        print(f"\n### Top {len(top_sensitive)} pages les plus sensibles")
        print(top_sensitive.to_markdown(tablefmt="grid"))
        
    except Exception as e:
        logger.error(f"Erreur dans le pipeline: {e}")
        raise