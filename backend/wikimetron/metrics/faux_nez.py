"""
user_detection_metric.py - Métrique de détection d'utilisateurs spécifiques
Vérifie si des utilisateurs d'un CSV ont contribué aux pages Wikipedia.
Score: 1 si au moins un utilisateur détecté, 0 sinon

Exemple de User-Agent approprié :
'MonProjetWikipedia/1.0 (https://github.com/moncompte/monprojet; contact@mondomaine.fr) requests/2.31.0'
"""
import pandas as pd
import requests
import time
import logging
from typing import List, Dict, Set
from functools import lru_cache
logger = logging.getLogger(__name__)
# Cache pour éviter de recharger le CSV à chaque appel
@lru_cache(maxsize=1)
def load_user_list(csv_path: str) -> Set[str]:
    """
    Charge la liste des utilisateurs depuis un fichier CSV.
    Assume que les noms d'utilisateurs sont dans la première colonne.
    """
    try:
        df = pd.read_csv(csv_path)
        # Prendre la première colonne comme noms d'utilisateurs
        usernames = set(df.iloc[:, 0].astype(str).str.strip())
        # Retirer les valeurs vides ou NaN
        usernames = {u for u in usernames if u and u != 'nan'}
        logger.info(f"Chargé {len(usernames)} utilisateurs depuis {csv_path}")
        return usernames
    except Exception as e:
        logger.error(f"Erreur lors du chargement du CSV {csv_path}: {e}")
        return set()
def get_page_contributors(page_title: str, lang: str = "fr", limit: int = 500) -> Dict[str, int]:
    """
    Récupère les contributeurs d'une page Wikipedia via l'API avec le nombre de contributions.
    Utilise l'API revisions pour compter les vraies contributions par page.
    S'inspire du code balance.py qui fonctionne bien.

    Args:
        page_title: Titre de la page Wikipedia
        lang: Code langue (fr, en, etc.)
        limit: Nombre maximum de révisions à récupérer

    Returns:
        Dict avec {nom_utilisateur: nombre_de_contributions_sur_cette_page}
    """
    API_URL = f"https://{lang}.wikipedia.org/w/api.php"

    # Headers avec User-Agent pour s'identifier poliment à l'API
    headers = {
        'User-Agent': 'WikipediaScoringPipeline'
    }

    contributors = {}

    # Paramètres inspirés du code balance.py qui fonctionne
    params = {
        "action": "query",
        "titles": page_title,
        "prop": "revisions",
        "rvprop": "user",  # On veut seulement le nom d'utilisateur
        "rvlimit": "max",  # Récupérer le maximum possible
        "format": "json",
        "formatversion": "2",  # Version moderne de l'API
        "rvdir": "newer"  # Du plus ancien au plus récent
    }

    try:
        cont = {}
        total_revisions_processed = 0

        # Boucle de pagination comme dans balance.py
        while total_revisions_processed < limit:
            req = {**params, **cont}

            response = requests.get(API_URL, params=req, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Debug: afficher la réponse brute si mode debug activé
            logger.debug(f"Réponse API pour '{page_title}': {data}")

            # Vérifier les erreurs API
            if "error" in data:
                logger.error(f"Erreur API pour '{page_title}': {data['error']}")
                break

            # Récupérer les pages (format v2)
            pages = data.get("query", {}).get("pages", [])
            if not pages:
                logger.warning(f"Aucune page trouvée pour '{page_title}'")
                break

            page_data = pages[0]
            logger.debug(f"Données de la page: {page_data}")

            # Vérifier si la page existe
            if "missing" in page_data:
                logger.warning(f"Page '{page_title}' n'existe pas")
                break

            # Récupérer les révisions
            if "revisions" not in page_data:
                logger.warning(f"Pas de révisions trouvées pour '{page_title}'")
                break

            revisions = page_data["revisions"]
            revision_count = len(revisions)
            logger.debug(f"Trouvé {revision_count} révisions pour '{page_title}'")

            # Compter les contributions par utilisateur
            for revision in revisions:
                if "user" in revision:
                    username = revision["user"]
                    # Exclure les utilisateurs systèmes/bots basiques
                    if not username.startswith('MediaWiki ') and username != 'MediaWiki default':
                        contributors[username] = contributors.get(username, 0) + 1
                        total_revisions_processed += 1

            # Vérifier la continuation
            if "continue" in data:
                cont = data["continue"]
                logger.debug(f"Continuation disponible: {cont}")
            else:
                logger.debug("Pas de continuation, toutes les révisions récupérées")
                break

            # Limite de sécurité
            if total_revisions_processed >= limit:
                logger.debug(f"Limite de {limit} révisions atteinte")
                break

        logger.debug(f"Trouvé {len(contributors)} contributeurs pour '{page_title}' avec {sum(contributors.values())} contributions totales sur la page")

        # Afficher les contributeurs si mode debug
        if contributors and logger.isEnabledFor(logging.DEBUG):
            for user, count in sorted(contributors.items(), key=lambda x: x[1], reverse=True)[:10]:
                logger.debug(f"  → {user}: {count} contributions")

    except requests.RequestException as e:
        logger.error(f"Erreur API pour la page '{page_title}': {e}")
    except Exception as e:
        logger.error(f"Erreur inattendue pour la page '{page_title}': {e}")

    return contributors
def calculate_user_detection_score(page_title: str, target_users: Set[str], lang: str = "fr") -> float:
    """
    Calcule le score de détection d'utilisateurs pour une page.
    Retourne 1 si au moins un utilisateur cible a contribué à la page, 0 sinon.

    Args:
        page_title: Titre de la page Wikipedia
        target_users: Set des utilisateurs à détecter
        lang: Code langue

    Returns:
        1.0 si au moins un utilisateur cible est détecté, 0.0 sinon
    """
    if not target_users:
        return 0.0

    # Récupérer les contributeurs de la page avec leur nombre de contributions
    contributors = get_page_contributors(page_title, lang)

    if not contributors:
        return 0.0

    # Vérifier si au moins un utilisateur cible est dans les contributeurs
    detected = False
    detected_users = []

    for username in target_users:
        if username in contributors:
            detected = True
            detected_users.append(username)

    if detected:
        logger.info(f"Page '{page_title}': utilisateurs détectés: {', '.join(detected_users)}")
        return 1.0
    else:
        return 0.0
def get_user_detection_score(pages: List[str], csv_path: str = None, users: List[str] = None, lang: str = "fr") -> pd.Series:
    """
    Fonction principale pour le pipeline de scoring.

    Args:
        pages: Liste des pages Wikipedia à analyser
        csv_path: Chemin vers le CSV contenant les noms d'utilisateurs (optionnel)
        users: Liste directe de noms d'utilisateurs à vérifier (optionnel)
        lang: Code langue Wikipedia

    Returns:
        pd.Series avec les scores de détection pour chaque page

    Note:
        - Si users est fourni, il est utilisé en priorité
        - Si users est None et csv_path fourni, charge depuis le CSV
        - Si les deux sont fournis, combine les deux sources
        - Si aucun n'est fourni, retourne des scores 0
    """
    logger.info(f"Début analyse de détection d'utilisateurs pour {len(pages)} pages")

    target_users = set()

    # Charger depuis la liste directe si fournie
    if users:
        target_users.update([u.strip() for u in users if u and u.strip()])
        logger.info(f"Utilisateurs directs chargés: {len(users)} utilisateurs")

    # Charger depuis le CSV si fourni
    if csv_path:
        csv_users = load_user_list(csv_path)
        target_users.update(csv_users)
        logger.info(f"Utilisateurs CSV chargés: {len(csv_users)} utilisateurs")

    if not target_users:
        logger.warning("Aucun utilisateur fourni (ni liste directe ni CSV), retour de scores 0")
        return pd.Series(index=pages, data=0.0, name="user_detection_score")

    logger.info(f"Total utilisateurs à détecter: {len(target_users)}")
    if len(target_users) <= 10:  # Afficher la liste si petite
        logger.info(f"Utilisateurs ciblés: {sorted(target_users)}")

    scores = {}

    for i, page in enumerate(pages):
        logger.debug(f"Analyse page {i+1}/{len(pages)}: {page}")

        try:
            score = calculate_user_detection_score(page, target_users, lang)
            scores[page] = score

            # Délai respectueux pour éviter de surcharger l'API Wikipedia
            # Plus long car on fait maintenant des requêtes plus lourdes (revisions)
            time.sleep(1.5)

        except Exception as e:
            logger.error(f"Erreur pour la page '{page}': {e}")
            scores[page] = 0.0

    result = pd.Series(scores, name="user_detection_score")

    # Statistiques
    detected_pages = (result > 0).sum()
    avg_score = result.mean()

    logger.info(f"Analyse terminée: {detected_pages}/{len(pages)} pages avec détection, score moyen: {avg_score:.3f}")

    return result
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Test de la métrique de détection d'utilisateurs")
    ap.add_argument("pages", nargs="+", help="Pages Wikipedia à analyser")
    ap.add_argument("--csv", help="Chemin vers le CSV des utilisateurs")
    ap.add_argument("--users", "-u", nargs="+", help="Liste directe d'utilisateurs à vérifier")
    ap.add_argument("--lang", default="fr", help="Code langue Wikipedia")
    ap.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")

    args = ap.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Vérifier qu'au moins une source d'utilisateurs est fournie
    if not args.csv and not args.users:
        print("ERREUR: Vous devez fournir soit --csv soit --users")
        print("\nExemples d'utilisation:")
        print("  # Avec CSV:")
        print("  python user_detection_metric.py 'Paris' --csv users.csv")
        print("  # Avec utilisateurs directs:")
        print("  python user_detection_metric.py 'Paris' --users JohnDoe MarieSmith")
        print("  # Avec les deux (combinés):")
        print("  python user_detection_metric.py 'Paris' --csv users.csv --users ExtraUser")
        ap.exit(1)

    try:
        scores = get_user_detection_score(args.pages, args.csv, args.users, args.lang)

        print("\n" + "="*50)
        print("RÉSULTATS DE DÉTECTION D'UTILISATEURS")
        print("="*50)

        if args.users:
            print(f"Utilisateurs recherchés: {', '.join(args.users)}")
        if args.csv:
            print(f"CSV utilisé: {args.csv}")
        print()

        for page, score in scores.items():
            status = "✓" if score > 0 else "✗"
            print(f"{status} {page:<30} : {score:.0f}")

        print(f"\nStatistiques:")
        print(f"- Pages avec détection: {(scores > 0).sum()}/{len(scores)}")
        print(f"- Score moyen: {scores.mean():.3f}")
        print(f"- Score maximum: {scores.max():.0f}")

    except Exception as e:
        logger.error(f"Erreur dans le test: {e}")
        raise
