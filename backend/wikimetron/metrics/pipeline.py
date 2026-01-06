# pipeline_v3.py - Version avec Parallélisme par Batch
"""
Pipeline de scoring Wikipedia avec support multi-langues simultanées.
Optimisation V3 : Parallélisme triple (Métrique × Langue × Batch de pages).
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
DEFAULT_BATCH_SIZE = 2  # ← NOUVEAU : Taille par défaut des batches


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
# NOUVEAU : Gestion des batches
# ─────────────────────────────────────────────────────────────────────────────────────────

def split_pages_into_batches(pages: List[PageInfo], batch_size: int) -> List[List[PageInfo]]:
    """
    Découpe une liste de PageInfo en batches de taille fixe.

    Exemple :
        130 pages avec batch_size=20 → 7 batches (6 de 20 + 1 de 10)
    """
    batches = []
    for i in range(0, len(pages), batch_size):
        batch = pages[i:i + batch_size]
        batches.append(batch)

    if batches:
        logger.debug(f"Découpe de {len(pages)} pages en {len(batches)} batches de ~{batch_size} pages")

    return batches


# ─────────────────────────────────────────────────────────────────────────────────────────
# Exécuteur atomique optimisé (MODIFIÉ pour les batches)
# ─────────────────────────────────────────────────────────────────────────────────────────

def execute_single_metric_lang_batch(
        metric_func: Callable,
        metric_name: str,
        lang: str,
        page_batch: List[PageInfo],  # ← CHANGÉ : Maintenant c'est un batch de PageInfo
        *extra_args
) -> tuple:
    """
    Exécute une métrique pour UNE langue sur UN BATCH de pages.

    Nouveauté V3 : Au lieu de traiter toutes les pages d'une langue,
    on ne traite qu'un petit lot (batch).

    Exemple : Au lieu de traiter 130 pages FR en une fois,
              on traite 20 pages FR à la fois.

    Returns:
        Tuple[Dict[str, float], Optional[Dict]]: (scores, details)
        - scores: {page_title: score_value}
        - details: None ou dict avec infos additionnelles (ex: sockpuppets détectés)
    """
    try:
        # Extraire les titres du batch
        titles = [p.clean_title for p in page_batch]

        # Sélecteur d'arguments (identique à V2)
        if metric_name in ["Views spikes", "Edits spikes", "Anonymity", "Edits revert probability",
                           "Discussion intensity"]:
            result = metric_func(titles, *extra_args, lang)
        elif metric_name in ["Protection", "Featured article", "Source concentration", "Citation gaps"]:
            result = metric_func(titles, lang, *extra_args) if extra_args else metric_func(titles, lang)
        elif metric_name == "Add/delete ratio":
            result = metric_func(titles, *extra_args, lang)
        elif metric_name in ["Contributor add/delete ratio", "Contributors concentration", "Sporadicity"]:
            result = metric_func(titles, lang, *extra_args)
        elif metric_name == "Staleness":
            result = metric_func(titles, lang, 365, extra_args[-1])
        elif metric_name in ["Suspicious sources", "Sockpuppets"]:
            result = metric_func(titles, extra_args[0], lang)
        else:
            result = metric_func(titles)

        # Gérer les retours enrichis (tuple pour Sockpuppets)
        details = None
        if isinstance(result, tuple):
            # La métrique retourne (scores, details)
            result, extra_data = result
            if metric_name == "Sockpuppets":
                details = {"detected_users": extra_data}

        # Conversion rapide result -> dict {titre: float}
        raw_dict = {}
        if isinstance(result, pd.Series):
            raw_dict = result.astype(float).to_dict()
        elif isinstance(result, dict):
            raw_dict = {k: float(v) for k, v in result.items()}
        elif hasattr(result, 'Score'):
            raw_dict = result["Score"].astype(float).to_dict()

        # Normalisation * 100 et nettoyage
        final_dict = {}
        for page_info in page_batch:  # ← CHANGÉ : On itère sur page_batch au lieu de titles
            title = page_info.clean_title
            val = raw_dict.get(title, 0.0)
            final_dict[title] = float(val) * 100.0

        return final_dict, details

    except Exception as e:
        logger.error(f"Erreur {metric_name} ({lang}, batch de {len(page_batch)} pages): {e}")
        return {p.clean_title: 0.0 for p in page_batch}, None


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
# Collecte parallèle optimisée (MODIFIÉ avec support des batches)
# ─────────────────────────────────────────────────────────────────────────────────────────

def collect_metrics_parallel_multilang(
        page_infos: List[PageInfo],
        start: str,
        end: str,
        batch_size: int = DEFAULT_BATCH_SIZE,  # ← NOUVEAU paramètre
        max_workers: int = MAX_WORKERS
) -> tuple:
    """
    Orchestre la collecte avec parallélisme TRIPLE :
    - Par métrique (16 métriques)
    - Par langue (N langues)
    - Par batch de pages (M batches par langue)

    NOUVEAU V3 : Si on a 130 pages FR et batch_size=20 :
    - V2 : 16 métriques × 1 langue = 16 tâches
    - V3 : 16 métriques × 1 langue × 7 batches = 112 tâches !

    Résultat : Beaucoup plus de parallélisme, donc plus rapide.

    Returns:
        Tuple[Dict[str, pd.Series], Dict[str, Any]]:
        - metrics: {metric_name: pd.Series}
        - details: {metric_name: details_dict} pour les métriques avec infos additionnelles
    """

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

    # 1. Préparation des groupes par langue
    lang_groups = group_pages_by_language(page_infos)

    # ═══════════════════════════════════════════════════════════════════════════════════
    # NOUVEAU V3 : Découper chaque groupe de langue en batches
    # ═══════════════════════════════════════════════════════════════════════════════════
    lang_batches: Dict[str, List[List[PageInfo]]] = {}
    total_batches = 0

    for lang, pages in lang_groups.items():
        batches = split_pages_into_batches(pages, batch_size)
        lang_batches[lang] = batches
        total_batches += len(batches)
        logger.info(f"Langue {lang}: {len(pages)} pages → {len(batches)} batches de ~{batch_size} pages")

    logger.info(f"Total : {total_batches} batches à traiter en parallèle")
    # ═══════════════════════════════════════════════════════════════════════════════════

    # Mapping inverse rapide: (titre, lang) -> unique_key
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

    # ═══════════════════════════════════════════════════════════════════════════════════
    # NOUVEAU V3 : Workers dynamiques adaptés au nombre de batches
    # ═══════════════════════════════════════════════════════════════════════════════════
    # Plus on a de petites tâches, plus on peut utiliser de workers
    # Formule : min(workers_base × facteur, limite_max)

    if total_batches > 100:
        dynamic_workers = min(max_workers * 3, 48)  # Beaucoup de batches → beaucoup de workers
    elif total_batches > 50:
        dynamic_workers = min(max_workers * 2, 32)
    else:
        dynamic_workers = max_workers

    logger.info(f"Workers dynamiques : {dynamic_workers} (adapté à {total_batches} batches)")
    # ═══════════════════════════════════════════════════════════════════════════════════

    start_time = time.time()
    results_accumulator = defaultdict(dict)  # {metric_name: {unique_key: score}}
    metric_details = defaultdict(dict)  # {metric_name: {lang: details}}

    logger.info(f"Démarrage collecte avec batching (Workers: {dynamic_workers})")

    with ThreadPoolExecutor(max_workers=dynamic_workers) as executor:
        future_map = {}

        # ═══════════════════════════════════════════════════════════════════════════════
        # NOUVEAU V3 : Triple boucle (Métrique × Langue × Batch)
        # ═══════════════════════════════════════════════════════════════════════════════
        for metric_name, metric_func in metric_configs:
            extras = extra_args_by_metric.get(metric_name, ())

            for lang, batches in lang_batches.items():  # ← Pour chaque langue
                for batch_idx, page_batch in enumerate(batches):  # ← NOUVEAU : Pour chaque batch

                    # Une tâche par Métrique × Langue × Batch
                    future = executor.submit(
                        execute_single_metric_lang_batch,  # ← Fonction modifiée
                        metric_func, metric_name, lang, page_batch, *extras
                    )
                    future_map[future] = (metric_name, lang, batch_idx, page_batch)

        logger.info(f"Total de tâches soumises : {len(future_map)}")
        # ═══════════════════════════════════════════════════════════════════════════════

        # 4. Récupération et agrégation
        completed = 0
        for future in as_completed(future_map):
            m_name, lang, batch_idx, page_batch = future_map[future]
            try:
                batch_results, details = future.result(timeout=120)  # Tuple: (Dict {titre: score}, details)

                # Stocker les détails si présents
                if details:
                    # Fusionner les détails des batches pour la même métrique/langue
                    if lang not in metric_details[m_name]:
                        metric_details[m_name][lang] = {"detected_users": {}}

                    if "detected_users" in details:
                        metric_details[m_name][lang]["detected_users"].update(details["detected_users"])

                # Remapping vers unique_key
                for title, score in batch_results.items():
                    uk = lookup_map.get((title, lang))
                    if uk:
                        results_accumulator[m_name][uk] = score

                completed += 1
                if completed % 20 == 0:  # Log de progression tous les 20 batches
                    logger.debug(f"Progression : {completed}/{len(future_map)} batches traités")

            except Exception as e:
                logger.error(f"Echec batch {m_name} - {lang} - batch #{batch_idx}: {e}")

    # 5. Construction finale des Series
    final_results = {}
    for name, _ in metric_configs:
        data_dict = results_accumulator.get(name, {})
        series = pd.Series(data_dict, dtype=float)
        final_results[name] = series.reindex(all_unique_keys, fill_value=0.0)

    duration = time.time() - start_time
    logger.info(f"Collecte avec batching terminée en {duration:.2f}s")
    logger.info(f"Débit : {len(page_infos) / duration:.2f} pages/seconde")

    return final_results, dict(metric_details)


# ─────────────────────────────────────────────────────────────────────────────────────────
# Calcul des scores (MODIFIÉ avec paramètre batch_size)
# ─────────────────────────────────────────────────────────────────────────────────────────

def compute_scores_multilang(
        pages: List[str],
        start: str,
        end: str,
        default_language: str = "fr",
        batch_size: int = DEFAULT_BATCH_SIZE,  # ← NOUVEAU paramètre
        max_workers: int = MAX_WORKERS
) -> Tuple[ScoringResult, pd.DataFrame, List[PageInfo], Dict[str, Any]]:
    """
    Fonction principale multi-langues avec support du batching.

    Paramètres :
        batch_size : Taille des batches de pages (défaut: 20)
                    - Plus petit = plus de parallélisme, mais plus d'overhead
                    - Plus grand = moins de parallélisme, mais moins d'overhead
                    - Recommandé : 15-25 pour un bon équilibre

    Returns:
        Tuple[ScoringResult, pd.DataFrame, List[PageInfo], Dict[str, Any]]:
        - scoring_result: Scores heat/quality/risk/sensitivity
        - metrics: DataFrame avec toutes les métriques brutes
        - page_infos: Informations sur chaque page
        - metric_details: Détails additionnels des métriques (ex: sockpuppets détectés)
    """
    page_infos = prepare_pages_with_languages(pages, default_language)

    pipeline_start = time.time()
    raw_metrics, metric_details = collect_metrics_parallel_multilang(
        page_infos, start, end, batch_size, max_workers  # ← NOUVEAU : batch_size
    )

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

    return ScoringResult(heat, quality, risk, sensitivity, heat_raw, quality_raw,
                         risk_raw), metrics, page_infos, metric_details


# ─────────────────────────────────────────────────────────────────────────────────────────
# Wrapper API (MODIFIÉ avec batch_size)
# ─────────────────────────────────────────────────────────────────────────────────────────

def compute_scores_for_api_multilang(
        pages: List[str],
        start_date: str,
        end_date: str,
        default_language: str = "fr",
        batch_size: int = DEFAULT_BATCH_SIZE,  # ← NOUVEAU paramètre
        max_workers: int = MAX_WORKERS
) -> Dict[str, Any]:
    """Wrapper API avec support multi-langues et batching."""
    try:
        pipeline_start = time.time()
        scoring_result, metrics, page_infos, metric_details = compute_scores_multilang(
            pages, start_date, end_date, default_language, batch_size, max_workers
        )
        processing_time = time.time() - pipeline_start

        results = {
            "pages": [],
            "summary": {
                "total_pages": len(pages),
                "analyzed_pages": len(page_infos),
                "processing_time": round(processing_time, 2),
                "batch_size": batch_size,  # ← Info utile pour le client
            },
            "scores": {
                "heat": scoring_result.heat.to_dict(),
                "quality": scoring_result.quality.to_dict(),
                "risk": scoring_result.risk.to_dict(),
                "sensitivity": scoring_result.sensitivity.to_dict(),
            }
        }

        # Extraire les sockpuppets détectés par page
        sockpuppets_by_page = {}
        if "Sockpuppets" in metric_details:
            for lang, lang_details in metric_details["Sockpuppets"].items():
                if "detected_users" in lang_details:
                    for page_title, users in lang_details["detected_users"].items():
                        sockpuppets_by_page[page_title] = users

        for page_info in page_infos:
            uk = page_info.unique_key
            page_data = {
                "title": page_info.clean_title,
                "original_input": page_info.original_input,
                "language": page_info.language,
                "unique_key": uk,
                "scores": {
                    "heat": float(scoring_result.heat.get(uk, 0.0)),
                    "quality": float(scoring_result.quality.get(uk, 0.0)),
                    "risk": float(scoring_result.risk.get(uk, 0.0)),
                    "sensitivity": float(scoring_result.sensitivity.get(uk, 0.0)),
                },
                "metrics": {m: float(metrics.loc[uk, m]) for m in metrics.columns},
            }

            # Ajouter les sockpuppets détectés si présents
            detected_sockpuppets = sockpuppets_by_page.get(page_info.clean_title, [])
            if detected_sockpuppets:
                page_data["detected_sockpuppets"] = detected_sockpuppets

            results["pages"].append(page_data)

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
    res, metrics, _, _ = compute_scores_multilang(pages, start, end, lang, DEFAULT_BATCH_SIZE, max_workers)
    return res, metrics


# ─────────────────────────────────────────────────────────────────────────────────────────
# CLI (MODIFIÉ avec option batch-size)
# ─────────────────────────────────────────────────────────────────────────────────────────

def format_results_mini(scores: ScoringResult, page_infos: List[PageInfo]):
    """Affichage minimaliste : juste les scores de sensibilité."""

    print(f"\n{'=' * 80}")
    print(f"{'📊 SCORES DE SENSIBILITÉ':^80}")
    print(f"{'=' * 80}\n")

    # Trouver la longueur maximale des titres pour l'alignement
    max_title_len = min(max(len(p.clean_title) for p in page_infos), 60)

    # En-tête du tableau
    print(f"{'Page':<{max_title_len}}  {'Langue':<8}  {'Sensibilité':>12}")
    print(f"{'-' * 80}")

    # Afficher chaque page
    for page_info in page_infos:
        uk = page_info.unique_key
        sens_score = scores.sensitivity.get(uk, 0.0)

        # Couleur basée sur le score
        if sens_score < 30:
            color = '\033[92m'  # Vert
        elif sens_score < 60:
            color = '\033[93m'  # Jaune
        else:
            color = '\033[91m'  # Rouge
        reset = '\033[0m'

        # Tronquer le titre si nécessaire
        title_display = page_info.clean_title[:max_title_len]

        print(f"{title_display:<{max_title_len}}  {page_info.language.upper():<8}  {color}{sens_score:>11.2f}%{reset}")

    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Pipeline V3 Mini - Affichage simple des scores de sensibilité")
    ap.add_argument("pages", nargs="+", help="Pages à analyser")
    ap.add_argument("--start", default="2025-04-21", help="Date de début")
    ap.add_argument("--end", default="2025-05-21", help="Date de fin")
    ap.add_argument("--lang", default="fr", help="Langue par défaut")
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                    help=f"Taille des batches (défaut: {DEFAULT_BATCH_SIZE})")
    ap.add_argument("--workers", type=int, default=MAX_WORKERS,
                    help=f"Nombre de workers max (défaut: {MAX_WORKERS})")
    args = ap.parse_args()

    scores, detail, page_infos, metric_details = compute_scores_multilang(
        args.pages, args.start, args.end, args.lang, args.batch_size, args.workers
    )

    format_results_mini(scores, page_infos)