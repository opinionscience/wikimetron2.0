#!/usr/bin/env python3
# minor_edits.py
"""
Module pour calculer la proportion d'éditions mineures sur une page Wikipedia.
Version 2.0 : Supporte l'exclusion des Admin et des Bots.
"""

from __future__ import annotations
from typing import List, Dict, Set
import pandas as pd
import requests
import time
import logging
import argparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "MinorEditsMetric/2.0 (opsci@wikimetron.com)"}
DEFAULT_LIMIT = 100


def _fetch_revisions_with_flags(title: str, lang: str = "fr", limit: int = DEFAULT_LIMIT) -> List[Dict]:
    """Récupère les dernières révisions d'une page."""
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "titles": title,
        "prop": "revisions",
        "rvprop": "ids|timestamp|user|flags|comment",
        "rvlimit": min(limit, 500),
        "redirects": 1
    }

    try:
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", [])

        if not pages or "missing" in pages[0]:
            logger.warning(f"Page '{title}' introuvable")
            return []

        return pages[0].get("revisions", [])

    except Exception as e:
        logger.error(f"❌ Erreur API pour '{title}': {e}")
        return []


def _get_user_groups(usernames: List[str], lang: str = "fr") -> Dict[str, List[str]]:
    """
    Récupère les groupes (droits) pour une liste d'utilisateurs.
    Nécessaire pour identifier les admins (sysop).
    """
    if not usernames:
        return {}

    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    user_groups = {}


    BATCH_SIZE = 50
    unique_users = list(set(usernames))

    logger.info(f"🔍 Vérification des droits pour {len(unique_users)} utilisateurs...")

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
            r = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
            data = r.json()
            users_data = data.get("query", {}).get("users", [])

            for user in users_data:
                user_groups[user.get("name")] = user.get("groups", [])

        except Exception as e:
            logger.warning(f"Erreur lors de la récupération des groupes: {e}")

    return user_groups


def _filter_revisions(revisions: List[Dict], lang: str, exclude_admins: bool, exclude_bots: bool) -> List[Dict]:
    """
    Filtre les révisions selon les critères d'exclusion.
    """
    if not revisions or (not exclude_admins and not exclude_bots):
        return revisions

    # 1. Identifier les utilisateurs à vérifier (ignorer les IPs/anonymes pour les droits admin)
    users_to_check = [
        rev.get("user") for rev in revisions
        if rev.get("user") and not rev.get("anon")
    ]

    # 2. Récupérer leurs groupes si on veut exclure les admins
    # Note: Pour les bots, on peut utiliser le flag de révision 'bot' (plus simple)
    # ou le groupe utilisateur. Ici on utilise les groupes pour être cohérent avec votre demande.
    user_groups_map = _get_user_groups(users_to_check, lang)

    filtered_revisions = []
    excluded_count = 0

    for rev in revisions:
        user = rev.get("user")
        groups = user_groups_map.get(user, [])

        is_excluded = False
        reason = ""

        # Exclusion ADMINS
        if exclude_admins:
            if "sysop" in groups or "bureaucrat" in groups or "rollbacker" in groups:
                is_excluded = True
                reason = "Admin"



        if is_excluded:
            excluded_count += 1
            # logger.debug(f"Exclusion: {user} ({reason})")
        else:
            filtered_revisions.append(rev)

    if excluded_count > 0:
        logger.info(f"🧹 Filtrage: {excluded_count} révisions exclues (Admins/Bots). Reste: {len(filtered_revisions)}")

    return filtered_revisions


def calculate_minor_edit_ratio(revisions: List[Dict], verbose: bool = False) -> float:
    """Calcule le ratio avec la correction du booléen."""
    if not revisions:
        return 0.0

    minor_count = 0
    total = len(revisions)

    for i, rev in enumerate(revisions, 1):
        # CORRECTION APPLIQUÉE ICI
        is_minor = rev.get("minor") is True

        if is_minor:
            minor_count += 1

        if verbose:
            user = rev.get("user", "Unknown")
            ts = rev.get("timestamp", "")
            logger.info(f"  {i:3d}. [{user:15s}] Minor: {'OUI' if is_minor else 'NON'} ({ts})")

    return minor_count / total if total > 0 else 0.0


def get_minor_edit_ratio(title: str, lang: str = "fr", limit: int = DEFAULT_LIMIT,
                         exclude_admins: bool = False, exclude_bots: bool = False,
                         verbose: bool = False) -> float:
    """Fonction principale."""
    logger.info(f"=== Analyse: {title} ===")

    # 1. Récupérer
    revisions = _fetch_revisions_with_flags(title, lang, limit)

    # 2. Filtrer
    if exclude_admins or exclude_bots:
        revisions = _filter_revisions(revisions, lang, exclude_admins, exclude_bots)

    if not revisions:
        logger.warning("Aucune révision après filtrage.")
        return 0.0

    # 3. Calculer
    return calculate_minor_edit_ratio(revisions, verbose)


# ─────────────────────────── CLI ──────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse des éditions mineures (avec filtres)")
    parser.add_argument("pages", nargs="+", help="Titre de la page")
    parser.add_argument("--lang", default="fr")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--verbose", "-v", action="store_true")

    # Nouveaux arguments
    parser.add_argument("--exclude-admins", action="store_true", help="Exclure les administrateurs")
    parser.add_argument("--exclude-bots", action="store_true", help="Exclure les bots")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    for page in args.pages:
        ratio = get_minor_edit_ratio(
            page,
            lang=args.lang,
            limit=args.limit,
            exclude_admins=args.exclude_admins,
            exclude_bots=args.exclude_bots,
            verbose=args.verbose
        )
        print(f"\n🏁 RÉSULTAT FINALE POUR '{page}': {ratio:.4f}\n")