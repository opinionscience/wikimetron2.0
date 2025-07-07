import requests
import re
from datetime import datetime
import pandas as pd

MONTHS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
}

DATE_RE = re.compile(
    r"(\d{1,2})\s+([A-Za-zéû]+)\s+(\d{4})\s+à\s+(\d{1,2}):(\d{2})"
)

def parse_french_datetime(date_str):
    m = DATE_RE.match(date_str)
    if not m:
        return None
    day, month_name, year, hour, minute = m.groups()
    month = MONTHS.get(month_name.lower())
    if not month:
        return None
    return datetime(int(year), month, int(day), int(hour), int(minute))

def count_messages_in_period(page_title, start_dt, end_dt):
    API_URL = "https://fr.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": f"Discussion:{page_title}",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2"
    }
    resp = requests.get(API_URL, params=params)
    data = resp.json()
    pages = data.get("query", {}).get("pages", [])
    if not pages or "revisions" not in pages[0]:
        return 0

    wikitext = pages[0]["revisions"][0]["slots"]["main"]["content"]
    all_dates = DATE_RE.findall(wikitext)
    datetimes = []
    for grp in all_dates:
        date_str = " ".join(grp[0:3]) + " à " + grp[3] + ":" + grp[4]
        dt = parse_french_datetime(date_str)
        if dt:
            datetimes.append(dt)
    in_range = [dt for dt in datetimes if start_dt <= dt <= end_dt]
    return len(in_range)

def discussion_score(pages, start_date, end_date):
    """
    Pour chaque page, retourne un score de discussion (0.1 par message, max 1.0).
    - pages: list ou Series de titres Wikipedia sans namespace.
    - start_date, end_date: datetime ou string "YYYY-MM-DD".
    Retourne un pd.Series indexé par page.
    """
    # Dates robustes
    if isinstance(start_date, str):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = start_date
    if isinstance(end_date, str):
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = end_date

    scores = {}
    for page in pages:
        n_msg = count_messages_in_period(page, start_dt, end_dt)
        score = min(1.0, 0.1 * n_msg)
        scores[page] = score
    return pd.Series(scores, name="discussion_score")

# Exemple d'utilisation :
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python taille_talk.py PAGE [PAGE2 ...] START_DATE END_DATE")
        print("Exemple: python taille_talk.py \"Page 1\" \"Page 2\" 2022-06-01 2025-07-01")
        sys.exit(1)

    # Tous les arguments sauf les deux derniers sont des titres de pages
    *pages, start_date, end_date = sys.argv[1:]

    print(f"Calcul du score discussion pour les pages {pages} entre {start_date} et {end_date}...\n")
    res = discussion_score(pages, start_date, end_date)
    print(res)
