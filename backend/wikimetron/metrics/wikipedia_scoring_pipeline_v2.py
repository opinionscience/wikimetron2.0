# pipeline.py - Adaptation PURE de wikipedia_scoring_pipeline_v2.py pour Wikimetron
"""
Pipeline de scoring Wikipedia avec collecte parallélisée des métriques.
Calcule Heat / Quality / Risk + score sensitivity par page.
ADAPTATION PURE - Logique identique à l'original
SCORES MULTIPLIÉS PAR 100
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Callable, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from urllib.parse import urlparse, unquote
from collections import Counter

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ───────────────────────────  Poids - IDENTIQUES À L'ORIGINAL ────────────────────────────
HEAT_W = {
    "Views spikes": 5,    # Spike de trafic (normalisé)
    "Edits spikes": 4,  
    "Edits revert probability": 3,# Spike d'éditions (normalisé) 
    "Protection": 2,
    "Discussion intensity": 1,    # Intensité page de discussion
      # Niveau de protection
}

QUAL_W = {
    "Suspicious sources": 10,
    'Featured article': 10,
    "Citations need": 3,
    "Staleness": 2,
    "Sources homogeneity": 2, 
    "Additions/deletions balance quality": 1,
   
}

RISK_W = {
    "sockpuppet" : 10,  # Score de détection de faux nez
    "Anonymity": 5,  # Part des éditions anonymes
    "Uniformity": 3,  # Monopolisation des contributions
    "Sporadicity": 2,  # Activité moyenne des contributeurs
    "Additions/deletions balance": 1,  # Équilibre des contributeurs
}

GLOB_W = {
    "heat": 1.5,
    "quality": 2,
    "risk": 1
}

MAX_WORKERS = 16 # Nombre de threads parallèles - IDENTIQUE À L'ORIGINAL

@dataclass
class ScoringResult:
    """Structure IDENTIQUE à l'original"""
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

def extract_clean_title_and_language(input_str: str) -> Tuple[str, Optional[str]]:
    """
    Transforme une URL Wikipedia en titre propre et extrait la langue.
    Si ce n'est pas une URL, retourne la chaîne telle quelle avec None pour la langue.
    
    Exemple : 
    - "https://fr.wikipedia.org/wiki/Emmanuel_Macron" → ("Emmanuel Macron", "fr")
    - "https://en.wikipedia.org/wiki/Barack_Obama" → ("Barack Obama", "en")
    - "Emmanuel Macron" → ("Emmanuel Macron", None)
    """
    try:
        if input_str.startswith("http"):
            parsed = urlparse(input_str)
            
            # Vérifier si c'est une URL Wikipedia
            if "wikipedia.org" in parsed.netloc and "/wiki/" in parsed.path:
                # Extraire la langue du sous-domaine
                lang = parsed.netloc.split('.')[0]
                
                # Extraire le titre de la page
                raw_title = parsed.path.split("/wiki/")[1]
                clean_title = unquote(raw_title.replace("_", " "))
                
                return clean_title, lang
                
    except Exception as e:
        logger.warning(f"Erreur d'extraction de titre/langue depuis URL: {input_str} ({e})")
    
    return input_str, None  # fallback si ce n'est pas une URL Wikipedia

def detect_language_from_pages(pages: List[str]) -> str:
    """
    Détecte la langue à partir d'une liste de pages (URLs ou titres).
    Retourne la langue la plus fréquente ou "fr" par défaut.
    """
    languages = []
    
    for page in pages:
        _, lang = extract_clean_title_and_language(page)
        if lang:
            languages.append(lang)
    
    if not languages:
        logger.info("Aucune langue détectée depuis les URLs, utilisation de 'fr' par défaut")
        return "fr"
    
    # Trouver la langue la plus fréquente
    lang_counts = Counter(languages)
    most_common_lang = lang_counts.most_common(1)[0][0]
    
    # Vérifier la cohérence
    if len(set(languages)) > 1:
        logger.warning(f"Langues mixtes détectées: {dict(lang_counts)}. Utilisation de '{most_common_lang}'")
    else:
        logger.info(f"Langue détectée automatiquement: '{most_common_lang}'")
    
    return most_common_lang

def extract_clean_title(input_str: str) -> str:
    """
    Version simplifiée pour compatibilité avec le code existant.
    Transforme une URL Wikipedia en titre propre, sinon retourne la chaîne telle quelle.
    Exemple : "https://fr.wikipedia.org/wiki/Emmanuel_Macron" → "Emmanuel Macron"
    """
    title, _ = extract_clean_title_and_language(input_str)
    return title

def safe_metric_executor(metric_func: Callable, metric_name: str, pages: List[str], *args) -> pd.Series:
    """
    Exécute une métrique de manière sécurisée avec gestion d'erreurs.
    IDENTIQUE À L'ORIGINAL MAIS SCORES MULTIPLIÉS PAR 100
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
        
        # NOUVEAU: Multiplier par 100
        result = result * 100
        
        duration = time.time() - start_time
        logger.info(f"✓ {metric_name} terminée en {duration:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"✗ Erreur dans {metric_name}: {str(e)}")
        # Retourner des valeurs par défaut en cas d'erreur
        return pd.Series(index=pages, data=0.0, name=metric_name)

def generate_test_data(pages: List[str]) -> Dict[str, pd.Series]:
    """Génère des données de test quand les modules ne sont pas disponibles"""
    logger.warning("Génération de données de test - modules de métriques manquants")
    np.random.seed(42)
    
    all_metrics = list(HEAT_W.keys()) + list(QUAL_W.keys()) + list(RISK_W.keys())
    results = {}
    
    for metric in all_metrics:
        values = np.random.beta(2, 5, len(pages))
        # NOUVEAU: Multiplier par 100 pour les données de test aussi
        values = values * 100
        results[metric] = pd.Series(values, index=pages, name=metric)
    
    return results

def collect_metrics_parallel(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr",
    max_workers: int = MAX_WORKERS
) -> Dict[str, pd.Series]:
    """
    Collecte toutes les métriques en parallèle.
    LOGIQUE IDENTIQUE À L'ORIGINAL - Seuls les imports changent pour le chemin wikimetron.metrics
    """
    # Import des fonctions de métriques - ADAPTATION : chemin wikimetron.metrics
    try:
        from pageviews import get_pageview_spikes_normalized
        from edit import get_edit_spikes
        from protection import get_protection_scores
        from ref import get_citation_gap
        from balance import get_event_imbalance_events_only
        from last_edit import get_recency_score
        from adq import get_adq_score
        from user_balance_metric import get_mean_contributor_balance
        from monopol import get_monopolization_scores
        from quantity import get_avg_activity_score
        from domination import get_domain_dominance
        from taille_talk import discussion_score
        from ano_edit import get_anon_edit_score_series
        from blacklist_metric import get_blacklist_share
        from revert_risk import get_revert_risk
        from faux_nez import get_user_detection_score  # Import du faux nez
    except ImportError as e:
        logger.error(f"Erreur d'import des modules de métriques: {e}")
        # Fallback - générer des données de test
        logger.warning("Utilisation de données de test car modules manquants")
        return generate_test_data(pages)
    
    # Configuration des métriques à collecter - IDENTIQUE À L'ORIGINAL
    metric_configs = [
        ("Views spikes", get_pageview_spikes_normalized, (pages, start, end, lang)),
        ("Edits spikes", get_edit_spikes, (pages, start, end, lang)),
        ("Protection", get_protection_scores, (pages, lang)), # infobulle current status
        ("Citations need", get_citation_gap, (pages,)),
        ("Additions/deletions balance quality", get_event_imbalance_events_only, (pages, start, end, lang)),
        ("Staleness", get_recency_score, (pages, lang, 365, end)),
        ("Featured article", get_adq_score, (pages, lang)), #modifier pour la langue 
        ("Additions/deletions balance", get_mean_contributor_balance, (pages, lang, 10, 100, end)),
        ("Uniformity", get_monopolization_scores, (pages, lang,10, end)),
        ("Sporadicity", get_avg_activity_score, (pages, lang, 10, 100, end)),
        ("Sources homogeneity", get_domain_dominance, (pages, lang)),
        ("Discussion intensity", discussion_score, (pages,start, end)),
        ("Anonymity", get_anon_edit_score_series, (pages, start, end, lang)),
        ("Suspicious sources", get_blacklist_share, (pages, "blacklist.csv", lang)),
        ("Edits revert probability", get_revert_risk, (pages, start, end, lang)),
        ("sockpuppet", get_user_detection_score, (pages, "faux_nez.csv", lang))  # Faux nez
    ]
    
    logger.info(f"Démarrage collecte parallèle de {len(metric_configs)} métriques pour {len(pages)} pages")
    start_time = time.time()
    
    results = {}
    
    # ADAPTATION : ThreadPoolExecutor au lieu de ProcessPoolExecutor pour Docker
    # Mais même logique que l'original
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
    LOGIQUE IDENTIQUE À L'ORIGINAL - même signature, mêmes calculs
    SCORES MULTIPLIÉS PAR 100
    """
    pages = [extract_clean_title(p) for p in pages]
    
    logger.info(f"Début du pipeline de scoring pour {len(pages)} pages")
    pipeline_start = time.time()
    
    # 1. Collecte parallèle des métriques - IDENTIQUE
    raw_metrics = collect_metrics_parallel(pages, start, end, lang, max_workers)
    
    # 2. Conversion en DataFrame - IDENTIQUE
    metrics = pd.DataFrame(raw_metrics).apply(pd.to_numeric, errors="coerce").fillna(0)
    logger.info(f"DataFrame des métriques créé: {metrics.shape}")
    
    # 3. Agrégation par pondération - IDENTIQUE À L'ORIGINAL
    available_heat_metrics = [m for m in HEAT_W.keys() if m in metrics.columns]
    available_qual_metrics = [m for m in QUAL_W.keys() if m in metrics.columns]
    available_risk_metrics = [m for m in RISK_W.keys() if m in metrics.columns]
    
    logger.info(f"Métriques Heat disponibles: {available_heat_metrics}")
    logger.info(f"Métriques Quality disponibles: {available_qual_metrics}")
    logger.info(f"Métriques Risk disponibles: {available_risk_metrics}")
    
    # Calcul Heat: scores bruts et normalisés - IDENTIQUE MAIS MULTIPLIÉS PAR 100
    if available_heat_metrics:
        heat_weights = pd.Series({m: HEAT_W[m] for m in available_heat_metrics})
        heat_raw = (metrics[available_heat_metrics] * heat_weights).sum(axis=1)
        heat = heat_raw / heat_weights.sum()  # Version normalisée
    else:
        heat_raw = pd.Series(index=metrics.index, data=0.0)
        heat = pd.Series(index=metrics.index, data=0.0)
    
    # Calcul Quality: scores bruts et normalisés - IDENTIQUE MAIS MULTIPLIÉS PAR 100
    if available_qual_metrics:
        qual_weights = pd.Series({m: QUAL_W[m] for m in available_qual_metrics})
        quality_raw = (metrics[available_qual_metrics] * qual_weights).sum(axis=1)
        quality = quality_raw / qual_weights.sum()  # Version normalisée
    else:
        quality_raw = pd.Series(index=metrics.index, data=0.0)
        quality = pd.Series(index=metrics.index, data=0.0)
    
    # Calcul Risk: scores bruts et normalisés - IDENTIQUE MAIS MULTIPLIÉS PAR 100
    if available_risk_metrics:
        risk_weights = pd.Series({m: RISK_W[m] for m in available_risk_metrics})
        risk_raw = (metrics[available_risk_metrics] * risk_weights).sum(axis=1)
        risk = risk_raw / risk_weights.sum()  # Version normalisée
    else:
        risk_raw = pd.Series(index=metrics.index, data=0.0)
        risk = pd.Series(index=metrics.index, data=0.0)
    
    # 4. Score final: moyenne simple des 3 catégories normalisées - IDENTIQUE MAIS MULTIPLIÉ PAR 100
    sensitivity = (heat + quality + risk) / 3
    
    total_time = time.time() - pipeline_start
    logger.info(f"Pipeline terminé en {total_time:.2f}s")
    
    # Retour IDENTIQUE à l'original
    return ScoringResult(heat, quality, risk, sensitivity, heat_raw, quality_raw, risk_raw), metrics

# ═══════════════════════════════════════════════════════════════════════
# ADAPTATION POUR WIKIMETRON - Wrappers pour l'API avec détection automatique
# ═══════════════════════════════════════════════════════════════════════

def convert_scoring_result_to_dict(scoring_result: ScoringResult, metrics: pd.DataFrame, 
                                 pages: List[str], start_date: str, end_date: str, 
                                 language: str, processing_time: float) -> Dict[str, Any]:
    """
    Convertit les résultats du pipeline original vers le format API.
    Cette fonction N'AFFECTE PAS les calculs, juste la présentation.
    """
    
    # Préparer les résultats dans le format attendu par l'API
    results = {
        "pages": [],
        "summary": {
            "total_pages": len(pages),
            "analyzed_pages": len(pages),
            "start_date": start_date,
            "end_date": end_date,
            "language": language,
            "processing_time": round(processing_time, 2),
            "available_metrics": {
                "heat": [m for m in HEAT_W.keys() if m in metrics.columns],
                "quality": [m for m in QUAL_W.keys() if m in metrics.columns],
                "risk": [m for m in RISK_W.keys() if m in metrics.columns]
            }
        },
        "scores": {
            "heat": scoring_result.heat.to_dict(),
            "quality": scoring_result.quality.to_dict(),
            "risk": scoring_result.risk.to_dict(),
            "sensitivity": scoring_result.sensitivity.to_dict()
        },
        "raw_scores": {
            "heat_raw": scoring_result.heat_raw.to_dict(),
            "quality_raw": scoring_result.quality_raw.to_dict(),
            "risk_raw": scoring_result.risk_raw.to_dict()
        },
        "detailed_metrics": metrics.to_dict('index')
    }
    
    # Détail par page
    for page in pages:
        page_data = {
            "title": page,
            "status": "analyzed",
            "scores": {
                "heat": float(scoring_result.heat.get(page, 0.0)),
                "quality": float(scoring_result.quality.get(page, 0.0)),
                "risk": float(scoring_result.risk.get(page, 0.0)),
                "sensitivity": float(scoring_result.sensitivity.get(page, 0.0))
            },
            "raw_scores": {
                "heat_raw": float(scoring_result.heat_raw.get(page, 0.0)),
                "quality_raw": float(scoring_result.quality_raw.get(page, 0.0)),
                "risk_raw": float(scoring_result.risk_raw.get(page, 0.0))
            },
            "metrics": {metric: float(metrics.loc[page, metric]) 
                       for metric in metrics.columns if page in metrics.index}
        }
        results["pages"].append(page_data)
    
    return results

def compute_scores_for_api(
    pages: List[str],
    start_date: str,
    end_date: str,
    language: Optional[str] = None,
    max_workers: int = MAX_WORKERS
) -> Dict[str, Any]:
    """
    Wrapper pour l'API qui utilise le pipeline original avec détection automatique de langue.
    Accepte aussi bien des titres de pages que des URLs Wikipedia.
    
    Args:
        pages: Liste des pages (URLs ou titres)
        start_date: Date de début
        end_date: Date de fin
        language: Langue forcée (optionnel). Si None, détection automatique depuis les URLs
        max_workers: Nombre de workers parallèles
    """
    try:
        # 🔁 Nettoyage des pages et détection de langue
        clean_pages = [extract_clean_title(p) for p in pages]
        
        # Détection automatique de langue si non spécifiée
        if language is None:
            detected_language = detect_language_from_pages(pages)
            logger.info(f"Langue détectée automatiquement: {detected_language}")
        else:
            detected_language = language
            logger.info(f"Langue forcée: {detected_language}")

        pipeline_start = time.time()

        # Appel DIRECT du pipeline original avec la langue détectée
        scoring_result, metrics = compute_scores(clean_pages, start_date, end_date, detected_language, max_workers)

        processing_time = time.time() - pipeline_start

        # Conversion pour l'API uniquement
        return convert_scoring_result_to_dict(
            scoring_result, metrics, clean_pages, start_date, end_date, detected_language, processing_time
        )

    except Exception as e:
        logger.error(f"Erreur dans le pipeline API: {e}")
        # Retourner un résultat d'erreur
        return {
            "pages": [{"title": page, "status": "error", "error": str(e)} for page in pages],
            "summary": {
                "total_pages": len(pages),
                "analyzed_pages": 0,
                "start_date": start_date,
                "end_date": end_date,
                "language": language or "unknown",
                "error": str(e)
            },
            "scores": {},
            "error": str(e)
        }

def run_analysis(task_id: str, request_data: Dict[str, Any]) -> None:
    """
    Lance une analyse en arrière-plan pour l'API.
    Utilise le pipeline original avec détection automatique de langue.
    """
    try:
        logger.info(f"Début de l'analyse pour la tâche {task_id}")
        
        # Extraire les paramètres
        pages = request_data.get("pages", [])
        start_date = request_data.get("start_date")
        end_date = request_data.get("end_date")
        language = request_data.get("language")  # Peut être None pour détection automatique
        
        # Lancer l'analyse avec le pipeline original
        results = compute_scores_for_api(pages, start_date, end_date, language)
        
        logger.info(f"Analyse terminée avec succès pour la tâche {task_id}")
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de la tâche {task_id}: {str(e)}")
        raise

# CLI pour tests - ADAPTÉ pour la détection automatique
if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser(description="Pipeline de scoring Wikipedia parallélisé avec détection automatique de langue")
    ap.add_argument("pages", nargs="+", help="Liste des pages à analyser (URLs ou titres)")
    ap.add_argument("--start", default="2025-04-21", help="Date de début")
    ap.add_argument("--end", default="2025-05-21", help="Date de fin")
    ap.add_argument("--lang", default=None, help="Langue Wikipedia (détection automatique si non spécifié)")
    ap.add_argument("--workers", type=int, default=MAX_WORKERS, help="Nombre de workers parallèles")
    ap.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")
    
    args = ap.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Détection automatique de langue si non spécifiée
        if args.lang is None:
            detected_lang = detect_language_from_pages(args.pages)
            print(f"Langue détectée automatiquement: {detected_lang}")
        else:
            detected_lang = args.lang
        
        # Utilisation DIRECTE du pipeline original
        scores, detail = compute_scores(args.pages, args.start, args.end, detected_lang, args.workers)
        
        print("\n" + "="*60)
        print(f"RAPPORT DE SCORING - {len(args.pages)} pages analysées")
        print(f"Langue utilisée: {detected_lang}")
        print("="*60)
        
        print("\n### Métriques brutes")
        print(detail.round(3))
        
        # Scores finaux identiques
        clean_titles = [extract_clean_title(p) for p in args.pages]
        final = pd.DataFrame({
            "heat": scores.heat.round(3),
            "quality": scores.quality.round(3),
            "risk": scores.risk.round(3),
            "sensitivity": scores.sensitivity.round(3)
        }, index=clean_titles)
        
        print("\n### Scores finaux (normalisés)")
        print(final)
        
    except Exception as e:
        logger.error(f"Erreur dans le pipeline: {e}")
        raise