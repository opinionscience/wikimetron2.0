# pipeline.py - Version multi-langues du second pipeline (corrigée)
"""
Pipeline de scoring Wikipedia avec support multi-langues simultanées.
Chaque page peut avoir sa propre langue détectée depuis son URL.
SCORES MULTIPLIÉS PAR 100
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

# ───────────────────────────  Poids - IDENTIQUES À L'ORIGINAL ────────────────────────────
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
    "Citations Gaps": 3,
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

GLOB_W = {
    "heat": 1.5,
    "quality": 2,
    "risk": 1
}

MAX_WORKERS = 16

@dataclass
class PageInfo:
    """Structure pour stocker les informations d'une page"""
    original_input: str
    clean_title: str
    language: str
    unique_key: str  # Clé unique pour éviter les conflits

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

# ─────────────────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────────────────────────────────

def extract_clean_title_and_language(input_str: str) -> Tuple[str, Optional[str]]:
    """
    Transforme une URL Wikipedia en titre propre et extrait la langue.
    Si ce n'est pas une URL, retourne la chaîne telle quelle avec None pour la langue.
    """
    try:
        if input_str.startswith("http"):
            parsed = urlparse(input_str)
            if "wikipedia.org" in parsed.netloc and "/wiki/" in parsed.path:
                lang = parsed.netloc.split('.')[0]
                raw_title = parsed.path.split("/wiki/")[1]
                clean_title = unquote(raw_title.replace("_", " "))
                return clean_title, lang
    except Exception as e:
        logger.warning(f"Erreur d'extraction de titre/langue depuis URL: {input_str} ({e})")
    return input_str, None

def prepare_pages_with_languages(pages: List[str], default_language: str = "fr") -> List[PageInfo]:
    """
    Prépare une liste de PageInfo avec détection de langue par page.
    Chaque page garde sa langue détectée ou utilise la langue par défaut.
    """
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
        logger.debug(f"Page '{clean_title}' → langue: {final_lang} → clé: {unique_key}")
    return page_infos

def group_pages_by_language(page_infos: List[PageInfo]) -> Dict[str, List[PageInfo]]:
    """Groupe les pages par langue pour optimiser les appels aux métriques."""
    lang_groups = defaultdict(list)
    for page_info in page_infos:
        lang_groups[page_info.language].append(page_info)
    for lang, pages in lang_groups.items():
        titles = [p.clean_title for p in pages]
        logger.info(f"Langue {lang}: {len(pages)} pages - {titles[:3]}{'...' if len(titles) > 3 else ''}")
    return dict(lang_groups)

# ─────────────────────────────────────────────────────────────────────────────────────────
# Exécuteur de métriques multi-langues (corrigé)
# ─────────────────────────────────────────────────────────────────────────────────────────

def safe_metric_executor_multilang(
    metric_func: Callable,
    metric_name: str,
    pages_by_lang: Dict[str, List[str]],
    unique_keys_map: Dict[str, str],  # Map "{titre}_{lang}" -> unique_key
    start: str,
    end: str,
    *extra_args
) -> pd.Series:
    """
    Exécute une métrique sur plusieurs groupes de langues et combine les résultats.
    """
    try:
        start_time = time.time()
        logger.info(f"Début collecte métrique multi-langues: {metric_name}")
        all_results: Dict[str, float] = {}

        for lang, page_titles in pages_by_lang.items():
            try:
                logger.debug(f"  → {metric_name} pour {len(page_titles)} pages en {lang}")

                # Sélecteur d'arguments, compatible avec l'ancien pipeline
                if metric_name in ["Views spikes", "Edits spikes",
                                   "Anonymity", "Edits revert probability"]:
                    # (pages, start, end, lang)
                    result = metric_func(page_titles, start, end, lang)

                elif metric_name in ["Protection", "Featured article", "Source concentration"]:
                    # (pages, lang [, extras])
                    result = metric_func(page_titles, lang, *extra_args) if extra_args else metric_func(page_titles, lang)

                    
                elif metric_name == "Add/delete ratio":
    # QUALITY: (pages, end, limit, lang)
                    result = metric_func(page_titles, *extra_args, lang) if extra_args else metric_func(page_titles, lang)



                elif metric_name == "Contributor add/delete ratio":
                    # RISK: (pages, lang, 10, 100, end)
                    result = metric_func(page_titles, lang, *extra_args) if extra_args else metric_func(page_titles, lang)

                elif metric_name == "Contributors concentration":
                    # RISK: (pages, lang, 10, end)
                    result = metric_func(page_titles, lang, *extra_args) if extra_args else metric_func(page_titles, lang)

                elif metric_name == "Sporadicity":
                    # RISK: (pages, lang, 10, 100, end)
                    result = metric_func(page_titles, lang, *extra_args) if extra_args else metric_func(page_titles, lang)

                elif metric_name == "Staleness":
                    # (pages, lang, 365, end)
                    result = metric_func(page_titles, lang, 365, end)

                elif metric_name == "Discussion intensity":
    # (pages, start, end, lang)
                    result = metric_func(page_titles, start, end, lang)

                elif metric_name == "Suspicious sources":
                    # (pages, blacklist_path, lang)
                    bl_path = extra_args[0] if len(extra_args) >= 1 else "blacklist.csv"
                    result = metric_func(page_titles, bl_path, lang)

                elif metric_name == "Sockpuppets":
                    # (pages, faux_nez_path, lang)
                    fn_path = extra_args[0] if len(extra_args) >= 1 else "faux_nez.csv"
                    result = metric_func(page_titles, fn_path, lang)
                elif metric_name == "Citations Gaps":
    # (pages, lang)
                    result = metric_func(page_titles, lang)

                else:
                    # Métriques simples (e.g. "Citations need")
                    result = metric_func(page_titles)

                # Normalisation résultat -> Series
                if isinstance(result, pd.Series):
                    series = result.astype(float)
                elif isinstance(result, dict):
                    series = pd.Series(result, dtype=float)
                elif hasattr(result, 'Score'):  # DataFrame avec col "Score"
                    series = result["Score"].astype(float)
                else:
                    series = pd.Series(index=page_titles, data=0.0, dtype=float)

                # Multiplier par 100
                series = series * 100.0

                # Remapper vers unique_key
                for page_title in page_titles:
                    lookup_key = f"{page_title}_{lang}"
                    unique_key = unique_keys_map.get(lookup_key)
                    if unique_key:
                        all_results[unique_key] = float(series.get(page_title, 0.0))
                        logger.debug(f"    Mapping {page_title} ({lang}) -> {unique_key}: {series.get(page_title, 0.0)}")
                    else:
                        logger.warning(f"Clé unique non trouvée pour {page_title} ({lang})")

            except Exception as e:
                logger.error(f"Erreur pour {metric_name} en {lang}: {e}")
                for page_title in page_titles:
                    lookup_key = f"{page_title}_{lang}"
                    unique_key = unique_keys_map.get(lookup_key)
                    if unique_key:
                        all_results[unique_key] = 0.0

        # Série finale indexée par toutes les unique_keys
        all_unique_keys = list(unique_keys_map.values())
        final_result = pd.Series(all_results, name=metric_name, dtype=float)
        final_result = final_result.reindex(all_unique_keys, fill_value=0.0)

        duration = time.time() - start_time
        logger.info(f"✓ {metric_name} multi-langues terminée en {duration:.2f}s")
        return final_result

    except Exception as e:
        logger.error(f"✗ Erreur critique dans {metric_name}: {str(e)}")
        all_unique_keys = list(unique_keys_map.values())
        return pd.Series(index=all_unique_keys, data=0.0, name=metric_name, dtype=float)

# ─────────────────────────────────────────────────────────────────────────────────────────
# Données de test
# ─────────────────────────────────────────────────────────────────────────────────────────

def generate_test_data_multilang(page_infos: List[PageInfo]) -> Dict[str, pd.Series]:
    """Génère des données de test multi-langues avec clés uniques"""
    logger.warning("Génération de données de test multi-langues - modules de métriques manquants")
    np.random.seed(42)  # Seed fixe pour reproductibilité

    unique_keys = [p.unique_key for p in page_infos]
    all_metrics = list(HEAT_W.keys()) + list(QUAL_W.keys()) + list(RISK_W.keys())
    results: Dict[str, pd.Series] = {}

    logger.info(f"Génération de données de test pour {len(unique_keys)} pages : {unique_keys}")

    for metric in all_metrics:
        values = []
        for i, page_info in enumerate(page_infos):
            # Seed différente par page et langue
            lang_seed = hash(page_info.language) % 1000
            np.random.seed(42 + i + lang_seed)
            value = np.random.beta(2, 5) * 100
            values.append(value)
            logger.debug(f"  {metric} pour {page_info.unique_key} ({page_info.language}): {value:.3f}")
        results[metric] = pd.Series(values, index=unique_keys, name=metric, dtype=float)

    return results

# ─────────────────────────────────────────────────────────────────────────────────────────
# Collecte parallèle multi-langues (corrigée)
# ─────────────────────────────────────────────────────────────────────────────────────────

def collect_metrics_parallel_multilang(
    page_infos: List[PageInfo],
    start: str,
    end: str,
    max_workers: int = MAX_WORKERS
) -> Dict[str, pd.Series]:
    """
    Collecte toutes les métriques en parallèle avec support multi-langues.
    """
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
        from faux_nez import get_user_detection_score
    except ImportError as e:
        logger.error(f"Erreur d'import des modules de métriques: {e}")
        return generate_test_data_multilang(page_infos)

    # Grouper les pages par langue
    lang_groups = group_pages_by_language(page_infos)

    # Construire pages_by_lang et mapping vers unique_key
    pages_by_lang: Dict[str, List[str]] = {}
    unique_keys_map: Dict[str, str] = {}  # "{title}_{lang}" -> unique_key

    for lang, pages in lang_groups.items():
        titles = [p.clean_title for p in pages]
        pages_by_lang[lang] = titles
        for p in pages:
            key = f"{p.clean_title}_{lang}"
            unique_keys_map[key] = p.unique_key

    # Config des métriques
    metric_configs = [
        ("Views spikes", get_pageview_spikes_normalized),
        ("Edits spikes", get_edit_spikes),
        ("Protection", get_protection_scores),
        ("Citations Gaps", get_citation_gap),
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

    # Arguments additionnels par métrique (alignés sur l'ancien pipeline)
    extra_args_by_metric: Dict[str, Tuple[Any, ...]] = {
        # QUAL
        "Add/delete ratio": (end, 10),
        # RISK
        "Contributor add/delete ratio": (10, 100, end),  # get_mean_contributor_balance(pages, lang, 10, 100, end)
        "Contributors concentration": (10, end),                        # get_monopolization_scores(pages, lang, 10, end)
        "Sporadicity": (10, 100, end),                  # get_avg_activity_score(pages, lang, 10, 100, end)
        # Fichiers
        "Suspicious sources": ("wikimetron/metrics/blacklist.csv",),
        "Sockpuppets": ("wikimetron/metrics/faux_nez.csv",),
    }

    logger.info(f"Démarrage collecte multi-langues: {len(metric_configs)} métriques pour {len(page_infos)} pages")
    start_time = time.time()
    results: Dict[str, pd.Series] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_metric: Dict[Any, str] = {}
        for metric_name, metric_func in metric_configs:
            extras = extra_args_by_metric.get(metric_name, ())
            future = executor.submit(
                safe_metric_executor_multilang,
                metric_func,
                metric_name,
                pages_by_lang,
                unique_keys_map,
                start,
                end,
                *extras
            )
            future_to_metric[future] = metric_name

        for future in as_completed(future_to_metric):
            metric_name = future_to_metric[future]
            try:
                result = future.result(timeout=60)
                results[metric_name] = result
            except Exception as e:
                logger.error(f"Échec critique pour {metric_name}: {e}")
                all_unique_keys = [p.unique_key for p in page_infos]
                results[metric_name] = pd.Series(index=all_unique_keys, data=0.0, name=metric_name, dtype=float)

    total_time = time.time() - start_time
    success_count = len([r for r in results.values() if r.sum() > 0])
    logger.info(f"Collecte multi-langues terminée en {total_time:.2f}s - {success_count}/{len(metric_configs)} métriques")

    return results

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
    """
    Fonction principale multi-langues : chaque page garde sa langue détectée.
    """
    page_infos = prepare_pages_with_languages(pages, default_language)

    logger.info(f"Pipeline multi-langues pour {len(page_infos)} pages")
    lang_counts = Counter([p.language for p in page_infos])
    for lang, count in lang_counts.items():
        logger.info(f"  → {count} pages en {lang}")

    pipeline_start = time.time()
    raw_metrics = collect_metrics_parallel_multilang(page_infos, start, end, max_workers)

    # DataFrame des métriques: index = unique_keys + reindex pour l'ordre
    unique_keys = [p.unique_key for p in page_infos]
    metrics = pd.DataFrame(raw_metrics).apply(pd.to_numeric, errors="coerce").fillna(0.0)
    metrics = metrics.reindex(unique_keys, fill_value=0.0)

    logger.info(f"DataFrame des métriques créé: {metrics.shape}")

    # Sélection des métriques disponibles
    available_heat_metrics = [m for m in HEAT_W.keys() if m in metrics.columns]
    available_qual_metrics = [m for m in QUAL_W.keys() if m in metrics.columns]
    available_risk_metrics = [m for m in RISK_W.keys() if m in metrics.columns]

    # Heat
    if available_heat_metrics:
        heat_weights = pd.Series({m: HEAT_W[m] for m in available_heat_metrics}, dtype=float)
        heat_raw = (metrics[available_heat_metrics] * heat_weights).sum(axis=1)
        heat = heat_raw / heat_weights.sum()
    else:
        heat_raw = pd.Series(index=metrics.index, data=0.0, dtype=float)
        heat = heat_raw.copy()

    # Quality
    if available_qual_metrics:
        qual_weights = pd.Series({m: QUAL_W[m] for m in available_qual_metrics}, dtype=float)
        quality_raw = (metrics[available_qual_metrics] * qual_weights).sum(axis=1)
        quality = quality_raw / qual_weights.sum()
    else:
        quality_raw = pd.Series(index=metrics.index, data=0.0, dtype=float)
        quality = quality_raw.copy()

    # Risk
    if available_risk_metrics:
        risk_weights = pd.Series({m: RISK_W[m] for m in available_risk_metrics}, dtype=float)
        risk_raw = (metrics[available_risk_metrics] * risk_weights).sum(axis=1)
        risk = risk_raw / risk_weights.sum()
    else:
        risk_raw = pd.Series(index=metrics.index, data=0.0, dtype=float)
        risk = risk_raw.copy()

    # Score final (pondérations globales non utilisées ici, on garde moyenne simple)
    sensitivity = (heat + quality + risk) / 3.0

    total_time = time.time() - pipeline_start
    logger.info(f"Pipeline multi-langues terminé en {total_time:.2f}s")

    return ScoringResult(heat, quality, risk, sensitivity, heat_raw, quality_raw, risk_raw), metrics, page_infos

# ─────────────────────────────────────────────────────────────────────────────────────────
# Wrapper API (corrigé pour utiliser unique_key)
# ─────────────────────────────────────────────────────────────────────────────────────────

def compute_scores_for_api_multilang(
    pages: List[str],
    start_date: str,
    end_date: str,
    default_language: str = "fr",
    max_workers: int = MAX_WORKERS
) -> Dict[str, Any]:
    """
    Wrapper API avec support multi-langues automatique.
    """
    try:
        pipeline_start = time.time()

        scoring_result, metrics, page_infos = compute_scores_multilang(
            pages, start_date, end_date, default_language, max_workers
        )

        processing_time = time.time() - pipeline_start

        results: Dict[str, Any] = {
            "pages": [],
            "summary": {
                "total_pages": len(pages),
                "analyzed_pages": len(page_infos),
                "start_date": start_date,
                "end_date": end_date,
                "languages": dict(Counter([p.language for p in page_infos])),
                "processing_time": round(processing_time, 2),
                "available_metrics": {
                    "heat": [m for m in HEAT_W.keys() if m in metrics.columns],
                    "quality": [m for m in QUAL_W.keys() if m in metrics.columns],
                    "risk": [m for m in RISK_W.keys() if m in metrics.columns],
                },
            },
            "scores": {
                "heat": scoring_result.heat.to_dict(),
                "quality": scoring_result.quality.to_dict(),
                "risk": scoring_result.risk.to_dict(),
                "sensitivity": scoring_result.sensitivity.to_dict(),
            },
            "raw_scores": {
                "heat_raw": scoring_result.heat_raw.to_dict(),
                "quality_raw": scoring_result.quality_raw.to_dict(),
                "risk_raw": scoring_result.risk_raw.to_dict(),
            },
            "detailed_metrics": metrics.to_dict('index'),
        }

        for page_info in page_infos:
            uk = page_info.unique_key
            page_data = {
                "title": page_info.clean_title,
                "original_input": page_info.original_input,
                "language": page_info.language,
                "status": "analyzed",
                "scores": {
                    "heat": float(scoring_result.heat.get(uk, 0.0)),
                    "quality": float(scoring_result.quality.get(uk, 0.0)),
                    "risk": float(scoring_result.risk.get(uk, 0.0)),
                    "sensitivity": float(scoring_result.sensitivity.get(uk, 0.0)),
                },
                "raw_scores": {
                    "heat_raw": float(scoring_result.heat_raw.get(uk, 0.0)),
                    "quality_raw": float(scoring_result.quality_raw.get(uk, 0.0)),
                    "risk_raw": float(scoring_result.risk_raw.get(uk, 0.0)),
                },
                "metrics": {metric: float(metrics.loc[uk, metric]) for metric in metrics.columns},
            }
            results["pages"].append(page_data)

        return results

    except Exception as e:
        logger.error(f"Erreur dans le pipeline multi-langues: {e}")
        return {
            "pages": [{"title": page, "status": "error", "error": str(e)} for page in pages],
            "summary": {
                "total_pages": len(pages),
                "analyzed_pages": 0,
                "start_date": start_date,
                "end_date": end_date,
                "error": str(e),
            },
            "scores": {},
            "error": str(e),
        }

# ─────────────────────────────────────────────────────────────────────────────────────────
# Compatibilité ancienne API
# ─────────────────────────────────────────────────────────────────────────────────────────

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
    lang_counts = Counter(languages)
    most_common_lang = lang_counts.most_common(1)[0][0]
    if len(set(languages)) > 1:
        logger.warning(f"Langues mixtes détectées: {dict(lang_counts)}. Utilisation de '{most_common_lang}'")
    else:
        logger.info(f"Langue détectée automatiquement: '{most_common_lang}'")
    return most_common_lang

def extract_clean_title(input_str: str) -> str:
    """Version simplifiée pour compatibilité avec le code existant."""
    title, _ = extract_clean_title_and_language(input_str)
    return title

def compute_scores(
    pages: List[str],
    start: str,
    end: str,
    lang: str = "fr",
    max_workers: int = MAX_WORKERS
) -> Tuple[ScoringResult, pd.DataFrame]:
    """
    Version simplifiée pour rétrocompatibilité - utilise une seule langue pour tous.
    """
    clean_pages = [extract_clean_title(p) for p in pages]

    # Créer des PageInfo avec la même langue pour tous (corrigé avec unique_key)
    page_infos = [
        PageInfo(
            original_input=pages[i],
            clean_title=clean_pages[i],
            language=lang,
            unique_key=f"{clean_pages[i]}___{lang}",
        )
        for i in range(len(pages))
    ]

    logger.info(f"Début du pipeline de scoring pour {len(pages)} pages")
    pipeline_start = time.time()

    raw_metrics = collect_metrics_parallel_multilang(page_infos, start, end, max_workers)

    # DataFrame
    unique_keys = [p.unique_key for p in page_infos]
    metrics = pd.DataFrame(raw_metrics).apply(pd.to_numeric, errors="coerce").fillna(0.0)
    metrics = metrics.reindex(unique_keys, fill_value=0.0)
    logger.info(f"DataFrame des métriques créé: {metrics.shape}")

    # Sélection
    available_heat_metrics = [m for m in HEAT_W.keys() if m in metrics.columns]
    available_qual_metrics = [m for m in QUAL_W.keys() if m in metrics.columns]
    available_risk_metrics = [m for m in RISK_W.keys() if m in metrics.columns]

    # Heat
    if available_heat_metrics:
        heat_weights = pd.Series({m: HEAT_W[m] for m in available_heat_metrics}, dtype=float)
        heat_raw = (metrics[available_heat_metrics] * heat_weights).sum(axis=1)
        heat = heat_raw / heat_weights.sum()
    else:
        heat_raw = pd.Series(index=metrics.index, data=0.0, dtype=float)
        heat = heat_raw.copy()

    # Quality
    if available_qual_metrics:
        qual_weights = pd.Series({m: QUAL_W[m] for m in available_qual_metrics}, dtype=float)
        quality_raw = (metrics[available_qual_metrics] * qual_weights).sum(axis=1)
        quality = quality_raw / qual_weights.sum()
    else:
        quality_raw = pd.Series(index=metrics.index, data=0.0, dtype=float)
        quality = quality_raw.copy()

    # Risk
    if available_risk_metrics:
        risk_weights = pd.Series({m: RISK_W[m] for m in available_risk_metrics}, dtype=float)
        risk_raw = (metrics[available_risk_metrics] * risk_weights).sum(axis=1)
        risk = risk_raw / risk_weights.sum()
    else:
        risk_raw = pd.Series(index=metrics.index, data=0.0, dtype=float)
        risk = risk_raw.copy()

    sensitivity = (heat + quality + risk) / 3.0

    total_time = time.time() - pipeline_start
    logger.info(f"Pipeline terminé en {total_time:.2f}s")

    return ScoringResult(heat, quality, risk, sensitivity, heat_raw, quality_raw, risk_raw), metrics

# ─────────────────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Pipeline multi-langues Wikipedia v2 (corrigée)")
    ap.add_argument("pages", nargs="+", help="Pages à analyser (URLs ou titres)")
    ap.add_argument("--start", default="2025-04-21", help="Date de début")
    ap.add_argument("--end", default="2025-05-21", help="Date de fin")
    ap.add_argument("--default-lang", default="fr", help="Langue par défaut")
    ap.add_argument("--workers", type=int, default=MAX_WORKERS, help="Workers parallèles")
    ap.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")

    args = ap.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        scores, detail, page_infos = compute_scores_multilang(
            args.pages, args.start, args.end, args.default_lang, args.workers
        )

        print("\n" + "=" * 60)
        print(f"RAPPORT MULTI-LANGUES V2 - {len(args.pages)} pages analysées")
        print("=" * 60)

        # Affichage par langue
        lang_groups = group_pages_by_language(page_infos)
        for lang, pages in lang_groups.items():
            print(f"\nLangue {lang.upper()}: {len(pages)} pages")
            for page in pages:
                print(f"  • {page.clean_title}")

        print("\n### Métriques détaillées")
        if not detail.empty:
            print(detail.round(3))
        else:
            print("Aucune métrique disponible")

        print("\n### Scores finaux")
        final_data = []
        for page_info in page_infos:
            uk = page_info.unique_key
            final_data.append({
                "title": page_info.clean_title,
                "langue": page_info.language,
                "heat": scores.heat.get(uk, 0.0),
                "quality": scores.quality.get(uk, 0.0),
                "risk": scores.risk.get(uk, 0.0),
                "sensitivity": scores.sensitivity.get(uk, 0.0),
            })
        final = pd.DataFrame(final_data).round(3)
        print(final)

    except Exception as e:
        logger.error(f"Erreur dans le pipeline: {e}")
        raise