#!/usr/bin/env python3
"""
Calcule le ratio de dominance du domaine le plus présent parmi toutes les URLs référencées dans les <ref>.
Usage : python domination_domain.py "Titre de la page"
"""

import requests
import re
import pandas as pd
import argparse
from collections import Counter
from urllib.parse import urlparse

HEADERS = {"User-Agent": "DominationDomainAnalyzer/1.0"}

def get_wikitext(title, lang="fr"):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "titles": title,
        "format": "json",
        "formatversion": 2
    }
    resp = requests.get(url, headers=HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        raise ValueError(f"Page '{title}' introuvable")
    return pages[0]["revisions"][0]["content"]

def extract_domains(wikitext):
    """Extrait les domaines des URLs dans les balises <ref>...<ref>"""
    refs = re.findall(r"<ref[^>/]*>(.*?)</ref>", wikitext, re.DOTALL | re.IGNORECASE)
    url_regex = r"https?://[^\s<>\"]+"
    domains = []
    for ref in refs:
        for url in re.findall(url_regex, ref):
            try:
                domain = urlparse(url).hostname
                if domain:
                    domains.append(domain.lower())
            except Exception:
                continue
    return domains

def compute_domain_dominance(title, lang="fr"):
    wikitext = get_wikitext(title, lang)
    domains = extract_domains(wikitext)
    if not domains:
        return None, 0, 0, 0.0
    counter = Counter(domains)
    dominant, count = counter.most_common(1)[0]
    total = len(domains)
    ratio = count / total if total > 0 else 0.0
    return dominant, count, total, ratio

def get_domain_dominance(pages, lang="fr"):
    """
    Pour chaque page, retourne le ratio de dominance du domaine principal parmi les références externes.
    Retourne un pd.Series indexé par le titre de la page.
    """
    results = {}
    for p in pages:
        try:
            dom, n_dom, n_tot, ratio = compute_domain_dominance(p, lang)
            results[p] = ratio  # (ou un dict si tu veux + d'info)
        except Exception:
            results[p] = 0.0
    return pd.Series(results, name="domain_dominance")
def main():
    parser = argparse.ArgumentParser(description="Ratio dominance d'un domaine sur une page Wikipedia")
    parser.add_argument("title", help="Titre de la page Wikipedia")
    parser.add_argument("--lang", default="fr", help="Code langue (défaut: fr)")
    args = parser.parse_args()
    try:
        dom_domain, n_dom, n_tot, ratio = compute_domain_dominance(args.title, args.lang)
        if n_tot == 0:
            print("Aucune URL trouvée dans les références.")
        else:
            pct = round(ratio * 100, 1)
            print(f"Page : {args.title}")
            print(f"Domaine dominant : {dom_domain}")
            print(f"Occurrences de ce domaine : {n_dom}")
            print(f"Nombre total de domaines référencés : {n_tot}")
            print(f"RATIO DOMINANCE : {pct}% ({n_dom}/{n_tot})")
    except Exception as e:
        print("Erreur :", e)

if __name__ == "__main__":
    main()
