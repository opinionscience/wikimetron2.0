import requests
import pandas as pd
from datetime import datetime
import time

HEADERS = {"User-Agent": "ActivityTimespanAnalyzer/1.0"}

def is_ip(username):
    import re
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}$'
    return re.match(ip_pattern, username) is not None

def get_recent_contributors(page_title, lang="fr", limit=10):
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
    r = requests.get(api_url, headers=HEADERS, params=params, timeout=30)
    data = r.json()
    pages = data.get("query", {}).get("pages", [])
    if not pages or "revisions" not in pages[0]:
        return []
    seen = set()
    contributors = []
    for rev in pages[0]["revisions"]:
        user = rev.get("user")
        if user and user not in seen and not is_ip(user):
            seen.add(user)
            contributors.append(user)
        if len(contributors) >= limit:
            break
    return contributors

def get_user_activity_score(username, lang="fr", contribs=10):
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

def get_avg_activity_score(pages, lang="fr", contributors=10, contributions=10):
    """
    Pour chaque page, retourne la moyenne d'activité des X derniers contributeurs
    (0 = très actif, 1 = peu actif).
    """
    results = {}
    for page in pages:
        users = get_recent_contributors(page, lang, contributors)
        if not users:
            results[page] = 0.0
            continue
        scores = []
        for user in users:
            score = get_user_activity_score(user, lang, contributions)
            scores.append(score)
            time.sleep(0.1)  # Retire ou ajuste si nécessaire
        results[page] = float(pd.Series(scores).mean()) if scores else 0.0
    return pd.Series(results, name="avg_activity_score")
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pages", nargs="+")
    parser.add_argument("--lang", default="fr")
    parser.add_argument("--contributors", type=int, default=10)
    parser.add_argument("--contributions", type=int, default=10)
    args = parser.parse_args()

    scores = get_avg_activity_score(args.pages, args.lang, args.contributors, args.contributions)
    for page, score in scores.items():
        print(f"{page}: {score:.3f}")
