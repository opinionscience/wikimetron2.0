# ref_risk.py
import requests
import pandas as pd
import time
from typing import List
from datetime import datetime

UA = {"User-Agent": "RefRiskBot/2.0 (opsci)"}
API_URL = "https://api.wikimedia.org/service/lw/inference/v1/models/reference-risk:predict"

def _get_rev_ids(title: str, lang: str, start: str, end: str) -> List[int]:
    """Récupère les rev_id entre start et end."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "revisions",
        "rvlimit": "max",
        "rvstart": f"{end}T23:59:59Z",
        "rvend": f"{start}T00:00:00Z",
        "rvprop": "ids|timestamp",
        "formatversion": "2"
    }
    rev_ids = []
    while True:
        r = requests.get(url, headers=UA, params=params)
        r.raise_for_status()
        data = r.json()
        revs = data.get("query", {}).get("pages", [{}])[0].get("revisions", [])
        rev_ids += [rev["revid"] for rev in revs]
        if "continue" in data:
            params.update(data["continue"])
        else:
            break
    return rev_ids

def _score_single_rev(rev_id: int, lang: str) -> float:
    payload = {"rev_id": rev_id, "lang": lang}
    r = requests.post(API_URL, json=payload, headers=UA)
    r.raise_for_status()
    return r.json().get("output", {}).get("score", 0.0)

def get_reference_risk_score(pages: List[str], start: str, end: str, lang: str = "fr") -> pd.Series:
    """
    Renvoie une moyenne des reference_risk_scores sur une période donnée.
    """
    results = {}
    for title in pages:
        try:
            rev_ids = _get_rev_ids(title, lang, start, end)
            if not rev_ids:
                results[title] = 0.0
                continue
            scores = []
            for rev_id in rev_ids:
                try:
                    s = _score_single_rev(rev_id, lang)
                    scores.append(s)
                    time.sleep(0.2)
                except Exception as e:
                    print(f"Révision {rev_id} ignorée ({e})")
            results[title] = round(sum(scores) / len(scores), 4) if scores else 0.0
        except Exception as e:
            print(f"[Erreur {title}] {e}")
            results[title] = 0.0
    return pd.Series(results, name="reference_risk")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end", default="2025-07-30")
    ns = ap.parse_args()

    s = get_reference_risk_score(ns.pages, ns.start, ns.end, ns.lang)
    print(s.to_markdown())

