# pipeline.py - Version Optimisée (Granularité Fine)
"""
Pipeline de scoring Wikipedia avec support multi-langues simultanées.
Optimisation : Parallélisme par (Métrique + Langue) et réduction de l'overhead Pandas.
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Callable, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote
from collections import Counter, defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ───────────────────────────  Poids ────────────────────────────
HEAT_W = {
    "Views spikes": 5,
    "Edits spikes": 4,
    "Edits revert probability": 3,
    "Protection": 2,
    "Discussion intensity": 1,
}

QUAL_W = {
    "Suspicious sources": 10,
    "Featured article": 10,
    "Citation gaps": 3,
    "Staleness": 2,
    "Source concentration": 2,
    "Add/delete ratio": 1,
}

RISK_W = {
    "Sockpuppets": 10,
    "Anonymity": 5,
    "Contributors concentration": 3,
    "Sporadicity": 2,
    "Contributor add/delete ratio": 1,
}

MAX_WORKERS = 16


@dataclass
class PageInfo:
    """Structure pour stocker les informations d'une page"""
    original_input: str
    clean_title: str
    language: str
    unique_key: str


@dataclass
class ScoringResult:
    heat: pd.Series
    quality: pd.Series
    risk: pd.Series
    sensitivity: pd.Series
    heat_raw: pd.Series
    quality_raw: pd.Series
    risk_raw: pd.Series


# ─────────────────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────────────────────────────────

def extract_clean_title_and_language(input_str: str) -> Tuple[str, Optional[str]]:
    """Transforme une URL Wikipedia en titre propre et extrait la langue."""
    try:
        if input_str.startswith("http"):
            parsed = urlparse(input_str)
            if "wikipedia.org" in parsed.netloc and "/wiki/" in parsed.path:
                lang = parsed.netloc.split('.')[0]
                raw_title = parsed.path.split("/wiki/")[1]
                clean_title = unquote(raw_title.replace("_", " "))
                return clean_title, lang
    except Exception as e:
        logger.warning(f"Erreur d'extraction de titre/langue: {input_str} ({e})")
    return input_str, None


def prepare_pages_with_languages(pages: List[str], default_language: str = "fr") -> List[PageInfo]:
    """Prépare les PageInfo avec détection de langue."""
    page_infos = []
    for original_page in pages:
        clean_title, detected_lang = extract_clean_title_and_language(original_page)
        final_lang = detected_lang if detected_lang else default_language
        unique_key = f"{clean_title}___{final_lang}"
        page_infos.append(PageInfo(
            original_input=original_page,
            clean_title=clean_title,
            language=final_lang,
            unique_key=unique_key
        ))
    return page_infos


def group_pages_by_language(page_infos: List[PageInfo]) -> Dict[str, List[PageInfo]]:
    """Groupe les pages par langue."""
    lang_groups = defaultdict(list)
    for page_info in page_infos:
        lang_groups[page_info.language].append(page_info)
    return dict(lang_groups)


# ─────────────────────────────────────────────────────────────────────────────────────────
# Exécuteur atomique optimisé
# ─────────────────────────────────────────────────────────────────────────────────────────

def execute_single_metric_lang(
        metric_func: Callable,
        metric_name: str,
        lang: str,
        pages: List[str],
        *extra_args
) -> Dict[str, float]:
    """
    Exécute une métrique pour une seule langue et retourne un dictionnaire natif {titre: score}.
    Évite la lourdeur de Pandas à l'intérieur des threads.
    """
    try:
        # Sélecteur d'arguments
        if metric_name in ["Views spikes", "Edits spikes", "Anonymity", "Edits revert probability",
                           "Discussion intensity"]:
            result = metric_func(pages, *extra_args, lang)  # (pages, start, end, lang)
        elif metric_name in ["Protection", "Featured article", "Source concentration", "Citation gaps"]:
            result = metric_func(pages, lang, *extra_args) if extra_args else metric_func(pages, lang)
        elif metric_name == "Add/delete ratio":
            result = metric_func(pages, *extra_args, lang)
        elif metric_name in ["Contributor add/delete ratio", "Contributors concentration", "Sporadicity"]:
            result = metric_func(pages, lang, *extra_args)
        elif metric_name == "Staleness":
            result = metric_func(pages, lang, 365, extra_args[-1])  # Hack pour récupérer 'end'
        elif metric_name in ["Suspicious sources", "Sockpuppets"]:
            result = metric_func(pages, extra_args[0], lang)
        else:
            result = metric_func(pages)

        # Conversion rapide result -> dict {titre: float}
        raw_dict = {}
        if isinstance(result, pd.Series):
            raw_dict = result.astype(float).to_dict()
        elif isinstance(result, dict):
            raw_dict = {k: float(v) for k, v in result.items()}
        elif hasattr(result, 'Score'):  # DataFrame
            raw_dict = result["Score"].astype(float).to_dict()

        # Normalisation * 100 et nettoyage
        final_dict = {}
        for page in pages:
            val = raw_dict.get(page, 0.0)
            final_dict[page] = float(val) * 100.0

        return final_dict

    except Exception as e:
        logger.error(f"Erreur {metric_name} ({lang}): {e}")
        return {p: 0.0 for p in pages}


# ─────────────────────────────────────────────────────────────────────────────────────────
# Données de test (Fallback)
# ─────────────────────────────────────────────────────────────────────────────────────────

def generate_test_data_multilang(page_infos: List[PageInfo]) -> Dict[str, pd.Series]:
    """Génère des données de test si les modules manquent."""
    logger.warning("Mode Test: Génération de données aléatoires.")
    np.random.seed(42)
    unique_keys = [p.unique_key for p in page_infos]
    all_metrics = list(HEAT_W.keys()) + list(QUAL_W.keys()) + list(RISK_W.keys())
    results: Dict[str, pd.Series] = {}

    for metric in all_metrics:
        values = np.random.beta(2, 5, size=len(unique_keys)) * 100
        results[metric] = pd.Series(values, index=unique_keys, name=metric, dtype=float)
    return results


# ─────────────────────────────────────────────────────────────────────────────────────────
# Collecte parallèle optimisée
# ─────────────────────────────────────────────────────────────────────────────────────────

def collect_metrics_parallel_multilang(
        page_infos: List[PageInfo],
        start: str,
        end: str,
        max_workers: int = MAX_WORKERS
) -> Dict[str, pd.Series]:
    """
    Orchestre la collecte avec une granularité fine (1 Thread = 1 Métrique + 1 Langue).
    """
    try:
        from wikimetron.metrics.pageviews import get_pageview_spikes_normalized
        from wikimetron.metrics.edit import get_edit_spikes
        from wikimetron.metrics.protection import get_protection_scores
        from wikimetron.metrics.ref import get_citation_gap
        from wikimetron.metrics.balance import get_event_imbalance_events_only
        from wikimetron.metrics.last_edit import get_recency_score
        from wikimetron.metrics.adq import get_adq_score
        from wikimetron.metrics.user_balance_metric import get_mean_contributor_balance
        from wikimetron.metrics.monopol import get_monopolization_scores
        from wikimetron.metrics.quantity import get_avg_activity_score
        from wikimetron.metrics.domination import get_domain_dominance
        from wikimetron.metrics.taille_talk import discussion_score
        from wikimetron.metrics.ano_edit import get_anon_edit_score_series
        from wikimetron.metrics.blacklist_metric import get_blacklist_share
        from wikimetron.metrics.revert_risk import get_revert_risk
        from wikimetron.metrics.faux_nez import get_user_detection_score
    except ImportError:
        return generate_test_data_multilang(page_infos)

    # 1. Préparation des groupes
    lang_groups = group_pages_by_language(page_infos)

    # Mapping inverse rapide: (titre, lang) -> unique_key
    # Optimisation: Tuple comme clé de dict est plus rapide que string concaténé
    lookup_map = {(p.clean_title, p.language): p.unique_key for p in page_infos}
    all_unique_keys = [p.unique_key for p in page_infos]

    # 2. Configuration des métriques
    metric_configs = [
        ("Views spikes", get_pageview_spikes_normalized),
        ("Edits spikes", get_edit_spikes),
        ("Protection", get_protection_scores),
        ("Citation gaps", get_citation_gap),
        ("Add/delete ratio", get_event_imbalance_events_only),
        ("Staleness", get_recency_score),
        ("Featured article", get_adq_score),
        ("Contributor add/delete ratio", get_mean_contributor_balance),
        ("Contributors concentration", get_monopolization_scores),
        ("Sporadicity", get_avg_activity_score),
        ("Source concentration", get_domain_dominance),
        ("Discussion intensity", discussion_score),
        ("Anonymity", get_anon_edit_score_series),
        ("Suspicious sources", get_blacklist_share),
        ("Edits revert probability", get_revert_risk),
        ("Sockpuppets", get_user_detection_score),
    ]

    extra_args_by_metric = {
        "Views spikes": (start, end),
        "Edits spikes": (start, end),
        "Discussion intensity": (start, end),
        "Anonymity": (start, end),
        "Edits revert probability": (start, end),
        "Add/delete ratio": (end, 10),
        "Contributor add/delete ratio": (10, 100, end),
        "Contributors concentration": (10, end),
        "Sporadicity": (10, 100, end),
        "Staleness": (end,),
        "Suspicious sources": ("wikimetron/metrics/blacklist.csv",),
        "Sockpuppets": ("wikimetron/metrics/faux_nez.csv",),
    }

    # 3. Soumission des tâches "Explosées"
    # Plus de tâches I/O bound = on peut augmenter les workers
    dynamic_workers = min(max_workers * 2, 32)

    start_time = time.time()
    results_accumulator = defaultdict(dict)  # {metric_name: {unique_key: score}}

    logger.info(f"Démarrage collecte optimisée (Workers: {dynamic_workers})")

    with ThreadPoolExecutor(max_workers=dynamic_workers) as executor:
        future_map = {}

        for metric_name, metric_func in metric_configs:
            extras = extra_args_by_metric.get(metric_name, ())

            for lang, pages in lang_groups.items():
                titles = [p.clean_title for p in pages]
                if not titles: continue

                # Une tâche par Langue par Métrique
                future = executor.submit(
                    execute_single_metric_lang,
                    metric_func, metric_name, lang, titles, *extras
                )
                future_map[future] = (metric_name, lang)

        # 4. Récupération et agrégation
        for future in as_completed(future_map):
            m_name, lang = future_map[future]
            try:
                lang_results = future.result(timeout=120)  # Dict {titre: score}

                # Remapping vers unique_key immédiat
                for title, score in lang_results.items():
                    uk = lookup_map.get((title, lang))
                    if uk:
                        results_accumulator[m_name][uk] = score
            except Exception as e:
                logger.error(f"Echec thread {m_name} - {lang}: {e}")

    # 5. Construction finale des Series
    final_results = {}
    for name, _ in metric_configs:
        data_dict = results_accumulator.get(name, {})
        series = pd.Series(data_dict, dtype=float)
        final_results[name] = series.reindex(all_unique_keys, fill_value=0.0)

    duration = time.time() - start_time
    logger.info(f"Collecte terminée en {duration:.2f}s")
    return final_results


# ─────────────────────────────────────────────────────────────────────────────────────────
# Calcul des scores
# ─────────────────────────────────────────────────────────────────────────────────────────

def compute_scores_multilang(
        pages: List[str],
        start: str,
        end: str,
        default_language: str = "fr",
        max_workers: int = MAX_WORKERS
) -> Tuple[ScoringResult, pd.DataFrame, List[PageInfo]]:
    """Fonction principale multi-langues."""
    page_infos = prepare_pages_with_languages(pages, default_language)

    pipeline_start = time.time()
    raw_metrics = collect_metrics_parallel_multilang(page_infos, start, end, max_workers)

    unique_keys = [p.unique_key for p in page_infos]
    metrics = pd.DataFrame(raw_metrics).apply(pd.to_numeric, errors="coerce").fillna(0.0)
    metrics = metrics.reindex(unique_keys, fill_value=0.0)

    # Sélection des métriques disponibles
    available_heat = [m for m in HEAT_W.keys() if m in metrics.columns]
    available_qual = [m for m in QUAL_W.keys() if m in metrics.columns]
    available_risk = [m for m in RISK_W.keys() if m in metrics.columns]

    def calc_score(available, weights):
        if not available:
            return pd.Series(0.0, index=metrics.index), pd.Series(0.0, index=metrics.index)
        w_series = pd.Series({m: weights[m] for m in available}, dtype=float)
        raw = (metrics[available] * w_series).sum(axis=1)
        normalized = raw / w_series.sum()
        return normalized, raw

    heat, heat_raw = calc_score(available_heat, HEAT_W)
    quality, quality_raw = calc_score(available_qual, QUAL_W)
    risk, risk_raw = calc_score(available_risk, RISK_W)

    sensitivity = (heat + quality + risk) / 3.0

    logger.info(f"Pipeline total terminé en {time.time() - pipeline_start:.2f}s")

    return ScoringResult(heat, quality, risk, sensitivity, heat_raw, quality_raw, risk_raw), metrics, page_infos


# ─────────────────────────────────────────────────────────────────────────────────────────
# Wrapper API
# ─────────────────────────────────────────────────────────────────────────────────────────

def compute_scores_for_api_multilang(
        pages: List[str],
        start_date: str,
        end_date: str,
        default_language: str = "fr",
        max_workers: int = MAX_WORKERS
) -> Dict[str, Any]:
    """Wrapper API avec support multi-langues."""
    try:
        pipeline_start = time.time()
        scoring_result, metrics, page_infos = compute_scores_multilang(
            pages, start_date, end_date, default_language, max_workers
        )
        processing_time = time.time() - pipeline_start

        results = {
            "pages": [],
            "summary": {
                "total_pages": len(pages),
                "analyzed_pages": len(page_infos),
                "processing_time": round(processing_time, 2),
            },
            "scores": {
                "heat": scoring_result.heat.to_dict(),
                "quality": scoring_result.quality.to_dict(),
                "risk": scoring_result.risk.to_dict(),
                "sensitivity": scoring_result.sensitivity.to_dict(),
            }
        }

        for page_info in page_infos:
            uk = page_info.unique_key
            results["pages"].append({
                "title": page_info.clean_title,
                "original_input": page_info.original_input,
                "language": page_info.language,
                "scores": {
                    "heat": float(scoring_result.heat.get(uk, 0.0)),
                    "quality": float(scoring_result.quality.get(uk, 0.0)),
                    "risk": float(scoring_result.risk.get(uk, 0.0)),
                    "sensitivity": float(scoring_result.sensitivity.get(uk, 0.0)),
                },
                "metrics": {m: float(metrics.loc[uk, m]) for m in metrics.columns},
            })

        return results

    except Exception as e:
        logger.error(f"Erreur API: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────────────────
# Compatibilité
# ─────────────────────────────────────────────────────────────────────────────────────────

def extract_clean_title(input_str: str) -> str:
    title, _ = extract_clean_title_and_language(input_str)
    return title


def compute_scores(pages: List[str], start: str, end: str, lang: str = "fr", max_workers: int = MAX_WORKERS):
    """Compatibilité ancienne signature."""
    res, metrics, _ = compute_scores_multilang(pages, start, end, lang, max_workers)
    return res, metrics


# ─────────────────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--start", default="2025-04-21")
    ap.add_argument("--end", default="2025-05-21")
    ap.add_argument("--lang", default="fr")
    args = ap.parse_args()

    scores, detail, _ = compute_scores_multilang(args.pages, args.start, args.end, args.lang)
    print(detail.round(2))