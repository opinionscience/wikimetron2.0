#!/usr/bin/env python3
"""
Métrique de bonus pour les utilisateurs privilégiés.

Cette métrique calcule un BONUS (score négatif) basé sur la présence d'utilisateurs
privilégiés (sysop, bureaucrat, rollbacker) dans les dernières contributions d'une page.

Principe:
- Si ≥10 contributions par des utilisateurs privilégiés → Bonus de -0.1 (soit -10% après multiplication par 100)
- Si <10 contributions par des utilisateurs privilégiés → Pas de bonus (0.0)
- Leur présence indique une surveillance/qualité → Réduit le score de sensibilité

Score retourné: Binaire 0.0 ou -0.1
- <10 contributions privilégiées → 0.0 (aucun bonus)
- ≥10 contributions privilégiées → -0.1 (bonus de -10 points)

Fonction exposée pour le pipeline:
    get_privileged_bonus(pages: List[str], lang: str = "fr", limit: int = 100) -> pd.Series
"""

from __future__ import annotations
from typing import List, Dict, Set
import pandas as pd
import requests
import logging
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "PrivilegedBonusMetric/1.0 (opsci@wikimetron.com)"}
DEFAULT_LIMIT = 100


def _get_api_url(lang: str = "fr") -> str:
    """Construit l'URL de l'API MediaWiki pour une langue donnée."""
    return f"https://{lang}.wikipedia.org/w/api.php"


def _fetch_revisions(title: str, lang: str = "fr", limit: int = DEFAULT_LIMIT) -> List[Dict]:
    """
    Récupère les dernières révisions d'une page avec les informations utilisateur.

    Args:
        title: Titre de la page Wikipedia
        lang: Code langue (ex: 'fr', 'en')
        limit: Nombre de révisions à récupérer (max 500 par requête)

    Returns:
        Liste de révisions avec infos utilisateur
    """
    api_url = _get_api_url(lang)
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "titles": title,
        "prop": "revisions",
        "rvprop": "ids|timestamp|user",
        "rvlimit": min(limit, 500),
        "redirects": 1
    }

    try:
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", [])

        if not pages or "missing" in pages[0]:
            logger.warning(f"Page '{title}' introuvable sur {lang}.wikipedia.org")
            return []

        return pages[0].get("revisions", [])

    except Exception as e:
        logger.error(f"❌ Erreur API pour '{title}': {e}")
        return []


def _get_user_groups(usernames: List[str], lang: str = "fr") -> Dict[str, List[str]]:
    """
    Récupère les groupes (droits) pour une liste d'utilisateurs.

    Args:
        usernames: Liste de noms d'utilisateurs
        lang: Code langue Wikipedia

    Returns:
        Dict {username: [list_of_groups]}
    """
    if not usernames:
        return {}

    api_url = _get_api_url(lang)
    user_groups = {}
    BATCH_SIZE = 50
    unique_users = list(set(usernames))

    logger.debug(f"🔍 Vérification des droits pour {len(unique_users)} utilisateurs...")

    for i in range(0, len(unique_users), BATCH_SIZE):
        batch = unique_users[i:i + BATCH_SIZE]
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "list": "users",
            "ususers": "|".join(batch),
            "usprop": "groups"
        }

        try:
            response = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            users_data = data.get("query", {}).get("users", [])

            for user in users_data:
                user_groups[user.get("name")] = user.get("groups", [])

            time.sleep(0.05)  # Rate limiting

        except Exception as e:
            logger.warning(f"⚠️  Erreur lors de la récupération des groupes (batch {i}): {e}")
            for username in batch:
                user_groups[username] = []

    return user_groups


def _count_privileged_revisions(revisions: List[Dict], lang: str = "fr", verbose: bool = False) -> Dict[str, any]:
    """
    Compte le nombre de révisions effectuées par des utilisateurs privilégiés.

    Groupes privilégiés:
        - sysop (administrateurs)
        - bureaucrat (bureaucrates)
        - rollbacker (révocateurs)

    Args:
        revisions: Liste de révisions
        lang: Code langue
        verbose: Afficher les détails

    Returns:
        Dict avec:
            - count: nombre de révisions privilégiées
            - total: nombre total de révisions
            - ratio: ratio (count / total)
            - privileged_users: set des utilisateurs privilégiés trouvés
    """
    if not revisions:
        return {
            "count": 0,
            "total": 0,
            "ratio": 0.0,
            "privileged_users": set()
        }

    # Extraire les utilisateurs (ignorer les anonymes)
    users_to_check = [
        rev.get("user") for rev in revisions
        if rev.get("user") and not rev.get("anon")
    ]

    # Récupérer les groupes utilisateurs
    user_groups_map = _get_user_groups(users_to_check, lang)

    # Identifier les utilisateurs privilégiés
    privileged_users = set()
    for username, groups in user_groups_map.items():
        if any(group in groups for group in ["sysop", "bureaucrat", "rollbacker"]):
            privileged_users.add(username)

    # Compter les révisions privilégiées
    privileged_count = 0
    for rev in revisions:
        user = rev.get("user")
        if user in privileged_users:
            privileged_count += 1

    total = len(revisions)
    ratio = privileged_count / total if total > 0 else 0.0

    if verbose:
        logger.info(f"   📊 Révisions: {total} total, {privileged_count} privilégiées ({ratio*100:.1f}%)")
        if privileged_users:
            logger.info(f"   👥 Utilisateurs privilégiés: {', '.join(sorted(privileged_users))}")

    return {
        "count": privileged_count,
        "total": total,
        "ratio": ratio,
        "privileged_users": privileged_users
    }


def calculate_privileged_bonus(title: str, lang: str = "fr", limit: int = DEFAULT_LIMIT, verbose: bool = False) -> float:
    """
    Calcule le score de bonus pour une page.

    Args:
        title: Titre de la page Wikipedia
        lang: Code langue
        limit: Nombre de révisions à analyser (défaut: 100)
        verbose: Afficher les détails

    Returns:
        Score de bonus binaire:
        - 0.0 = moins de 10 contributions par des utilisateurs privilégiés
        - -0.1 = 10 contributions ou plus par des utilisateurs privilégiés (bonus de -10%)
    """
    if verbose:
        logger.info(f"=== Analyse: {title} ({lang}) ===")

    # Récupérer les révisions
    revisions = _fetch_revisions(title, lang, limit)

    if not revisions:
        if verbose:
            logger.warning("   ⚠️  Aucune révision trouvée")
        return 0.0

    # Compter les révisions privilégiées
    stats = _count_privileged_revisions(revisions, lang, verbose)

    # Calculer le bonus (binaire : -0.1 si ≥10 contributions privilégiées, sinon 0)
    bonus = -0.1 if stats["count"] >= 10 else 0.0

    if verbose:
        if bonus < 0:
            logger.info(f"   🎁 Bonus activé: {bonus:.1f} ({stats['count']} contributions privilégiées ≥ 10)")
        else:
            logger.info(f"   ⚠️  Pas de bonus: seulement {stats['count']} contributions privilégiées (< 10)")

    return bonus


def get_privileged_bonus(pages: List[str], lang: str = "fr", limit: int = DEFAULT_LIMIT) -> pd.Series:
    """
    Fonction principale pour le pipeline.
    Calcule le score de bonus pour plusieurs pages.

    Args:
        pages: Liste de titres de pages Wikipedia
        lang: Code langue (défaut: 'fr')
        limit: Nombre de révisions à analyser par page (défaut: 100)

    Returns:
        pd.Series avec les scores de bonus binaires (0.0 ou -0.1) indexés par page
        - 0.0 si <10 contributions privilégiées
        - -0.1 si ≥10 contributions privilégiées (soit -10% après multiplication par 100)

    Exemples:
        >>> get_privileged_bonus(["France", "Paris", "Article obscur"], lang="fr", limit=100)
        France           -0.1
        Paris            -0.1
        Article obscur    0.0
        dtype: float64
    """
    results = {}

    logger.info(f"🎁 Calcul du bonus utilisateurs privilégiés pour {len(pages)} page(s)")
    logger.info(f"   Paramètres: lang={lang}, limit={limit}")

    for page in pages:
        try:
            bonus = calculate_privileged_bonus(page, lang, limit, verbose=False)
            results[page] = bonus
            logger.debug(f"   ✓ {page}: {bonus:.4f}")
            time.sleep(0.5)  # Rate limiting augmenté pour éviter les erreurs 429 (too many requests)
        except Exception as e:
            logger.error(f"   ✗ Erreur pour '{page}': {e}")
            results[page] = 0.0
            time.sleep(1.0)  # Délai supplémentaire en cas d'erreur

    logger.info(f"✅ Calcul terminé: {len(results)} pages traitées")

    return pd.Series(results, name="privileged_bonus", dtype=float)


def get_privileged_details(pages: List[str], lang: str = "fr", limit: int = DEFAULT_LIMIT) -> Dict[str, Dict]:
    """
    Fonction utilitaire pour obtenir les détails des utilisateurs privilégiés.

    Args:
        pages: Liste de titres de pages Wikipedia
        lang: Code langue
        limit: Nombre de révisions à analyser

    Returns:
        Dict {page_title: {"count": int, "total": int, "ratio": float, "users": list}}
    """
    results = {}

    logger.info(f"🔍 Analyse détaillée des utilisateurs privilégiés pour {len(pages)} page(s)")

    for page in pages:
        try:
            revisions = _fetch_revisions(page, lang, limit)
            stats = _count_privileged_revisions(revisions, lang, verbose=False)

            results[page] = {
                "count": stats["count"],
                "total": stats["total"],
                "ratio": stats["ratio"],
                "users": sorted(list(stats["privileged_users"]))
            }

            logger.info(f"   📄 {page}: {stats['count']}/{stats['total']} révisions privilégiées")
            if stats["privileged_users"]:
                logger.info(f"      👥 {', '.join(sorted(stats['privileged_users']))}")

            time.sleep(0.1)

        except Exception as e:
            logger.error(f"   ✗ Erreur pour '{page}': {e}")
            results[page] = {"count": 0, "total": 0, "ratio": 0.0, "users": []}

    return results


# ─────────────────────────── CLI ──────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Calcule le bonus basé sur les contributions d'utilisateurs privilégiés"
    )
    parser.add_argument("pages", nargs="+", help="Titre(s) de page(s)")
    parser.add_argument("--lang", default="fr", help="Code langue Wikipedia (défaut: fr)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                       help=f"Nombre de révisions à analyser (défaut: {DEFAULT_LIMIT})")
    parser.add_argument("--verbose", "-v", action="store_true", help="Affichage détaillé")
    parser.add_argument("--details", "-d", action="store_true",
                       help="Afficher les détails des utilisateurs privilégiés")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.details:
        # Mode détaillé
        details = get_privileged_details(args.pages, args.lang, args.limit)

        print(f"\n{'=' * 80}")
        print(f"{'🎁 DÉTAILS DES UTILISATEURS PRIVILÉGIÉS':^80}")
        print(f"{'=' * 80}\n")

        for page, info in details.items():
            print(f"📄 {page}")
            print(f"   Révisions privilégiées: {info['count']} / {info['total']} ({info['ratio']*100:.1f}%)")
            print(f"   Bonus: {-info['ratio']:.4f} (réduit la sensibilité de {info['ratio']*100:.1f}%)")

            if info['users']:
                print(f"   👥 Utilisateurs privilégiés:")
                for user in info['users']:
                    print(f"      • {user}")
            else:
                print(f"   ⚠️  Aucun utilisateur privilégié détecté")
            print()

    else:
        # Mode simple
        for page in args.pages:
            bonus = calculate_privileged_bonus(page, args.lang, args.limit, args.verbose)

            print(f"\n{'=' * 80}")
            print(f"🏁 RÉSULTAT FINAL POUR '{page}'")
            print(f"{'=' * 80}")
            print(f"Bonus: {bonus:.4f}")
            print(f"Impact: Réduit la sensibilité de {abs(bonus)*100:.1f}%")
            print(f"{'=' * 80}\n")
