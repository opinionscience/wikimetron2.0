import requests
import pandas as pd
from datetime import datetime, date
import time
import re

HEADERS = {"User-Agent": "ActivityTimespanAnalyzer/1.0"}

def is_temporary_account(username):
    """
    Détecte si un nom d'utilisateur est un compte temporaire Wikipedia
    Format: ~YYYY-XXXXX-X (ex: ~2025-20097-0)
    """
    temp_pattern = r'^~\d{4}-\d+-\d+$'
    return re.match(temp_pattern, username) is not None

def is_ip(username):
    """
    Détecte si un nom d'utilisateur est une adresse IP (IPv4 ou IPv6)
    """
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}$'
    return re.match(ip_pattern, username) is not None

def get_recent_contributors(page_title, lang="fr", limit=10, end=None, debug=False):
    """
    Récupère les contributeurs récents d'une page Wikipedia
    """
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": page_title,
        "prop": "revisions",
        "rvprop": "user",
        "rvlimit": min(limit * 3, 500),
        "formatversion": "2"
    }
    
    # Utiliser la date d'aujourd'hui si end n'est pas spécifié
    if end is None:
        end = date.today().strftime("%Y-%m-%d")
    
    # Convertir YYYY-MM-DD en format timestamp ISO pour l'API
    end_timestamp = f"{end}T23:59:59Z"
    params["rvstart"] = end_timestamp
    
    if debug:
        print(f"URL API: {api_url}")
        print(f"Paramètres: {params}")
    
    try:
        r = requests.get(api_url, headers=HEADERS, params=params, timeout=30)
        data = r.json()
        
        if debug:
            print(f"Statut HTTP: {r.status_code}")
            if "error" in data:
                print(f"Erreur API: {data['error']}")
            else:
                print(f"Réponse OK")
        
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            if debug:
                print("Aucune page trouvée dans la réponse")
            return []
        
        if "revisions" not in pages[0]:
            if debug:
                print("Aucune révision trouvée pour cette page")
                print(f"Contenu de la page: {pages[0]}")
            return []
        
        if debug:
            print(f"Nombre de révisions trouvées: {len(pages[0]['revisions'])}")
        
        seen = set()
        contributors = []
        for rev in pages[0]["revisions"]:
            user = rev.get("user")
            if debug:
                print(f"  Révision: utilisateur='{user}', IP={is_ip(user) if user else 'N/A'}")
            if user and user not in seen and not is_ip(user):
                seen.add(user)
                contributors.append(user)
            if len(contributors) >= limit:
                break
        return contributors
        
    except requests.RequestException as e:
        if debug:
            print(f"Erreur de requête: {e}")
        return []

def get_user_activity_score(username, lang="fr", contribs=10, end=None):
    """
    Calcule le score d'activité d'un utilisateur basé sur l'étalement temporel de ses contributions
    """
    # Les comptes temporaires et les IPs ont automatiquement un score de 1 (peu actif)
    if is_temporary_account(username) or is_ip(username):
        return 1.0
        
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "usercontribs",
        "ucuser": username,
        "ucprop": "timestamp",
        "ucnamespace": "0",
        "uclimit": contribs,
        "formatversion": "2"
    }
    
    # Utiliser la date d'aujourd'hui si end n'est pas spécifié
    if end is None:
        end = date.today().strftime("%Y-%m-%d")
    
    # Convertir YYYY-MM-DD en format timestamp ISO pour l'API
    end_timestamp = f"{end}T23:59:59Z"
    params["ucstart"] = end_timestamp
    
    try:
        r = requests.get(api_url, headers=HEADERS, params=params, timeout=30)
        data = r.json()
        contributions = data.get("query", {}).get("usercontribs", [])
        
        if len(contributions) < 2:
            return 0
            
        contributions.sort(key=lambda x: x["timestamp"], reverse=True)
        most_recent = contributions[0]["timestamp"]
        oldest = contributions[-1]["timestamp"]
        
        recent_dt = datetime.fromisoformat(most_recent.replace("Z", "+00:00"))
        oldest_dt = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
        
        timespan_days = (recent_dt - oldest_dt).total_seconds() / (24 * 3600)
        score = min(1.0, timespan_days / 365.0)
        return round(score, 3)
        
    except (requests.RequestException, KeyError, ValueError):
        return 0

def get_avg_activity_score(pages, lang="fr", contributors=10, contributions=10, end=None, debug=False):
    """
    Pour chaque page, retourne la moyenne d'activité des X derniers contributeurs
    (0 = très actif, 1 = peu actif).
    
    Args:
        pages: Liste des pages à analyser
        lang: Code langue de Wikipedia (défaut: "fr")
        contributors: Nombre de contributeurs récents à analyser (défaut: 10)
        contributions: Nombre de contributions par utilisateur à analyser (défaut: 10)
        end: Date de fin au format YYYY-MM-DD (ex: "2024-01-01") pour analyser 
             les contributeurs jusqu'à cette date. Si None, utilise la date d'aujourd'hui.
        debug: Si True, affiche des informations de débogage
    """
    results = {}
    for page in pages:
        if debug:
            print(f"\n=== Analyse de la page: {page} ===")
        
        users = get_recent_contributors(page, lang, contributors, end, debug)
        if debug:
            print(f"Contributeurs trouvés: {len(users)}")
            print(f"Contributeurs: {users}")
        
        if not users:
            if debug:
                print("Aucun contributeur trouvé")
            results[page] = 0.0
            continue
            
        scores = []
        for user in users:
            score = get_user_activity_score(user, lang, contributions, end)
            scores.append(score)
            if debug:
                account_type = ""
                if is_temporary_account(user):
                    account_type = " (compte temporaire)"
                elif is_ip(user):
                    account_type = " (IP)"
                print(f"  {user}: {score}{account_type}")
            time.sleep(0.1)  # Délai pour éviter de surcharger l'API
            
        final_score = float(pd.Series(scores).mean()) if scores else 0.0
        if debug:
            print(f"Score moyen final: {final_score:.3f}")
        results[page] = final_score
        
    return pd.Series(results, name="avg_activity_score")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyse l'activité des contributeurs de pages Wikipedia")
    parser.add_argument("pages", nargs="+", help="Pages Wikipedia à analyser")
    parser.add_argument("--lang", default="fr", help="Code langue de Wikipedia (défaut: fr)")
    parser.add_argument("--contributors", type=int, default=10, help="Nombre de contributeurs récents à analyser")
    parser.add_argument("--contributions", type=int, default=100, help="Nombre de contributions par utilisateur à analyser")
    parser.add_argument("--end", help="Date de fin au format YYYY-MM-DD (ex: 2024-01-01). Par défaut: aujourd'hui")
    parser.add_argument("--debug", action="store_true", help="Affiche des informations de débogage")
    args = parser.parse_args()

    scores = get_avg_activity_score(args.pages, args.lang, args.contributors, args.contributions, args.end, args.debug)
    for page, score in scores.items():
        print(f"{page}: {score:.3f}")