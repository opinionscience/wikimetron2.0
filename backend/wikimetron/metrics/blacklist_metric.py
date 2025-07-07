# blacklist_metric.py
"""
Calcule la part de références provenant d'un **domaine blacklisté**.

Fonction exposée
----------------
get_blacklist_share(pages, blacklist_csv="blacklist.csv", lang="fr") -> pd.Series
get_blacklisted_domains(pages, blacklist_csv="blacklist.csv", lang="fr") -> dict

* `blacklist.csv` doit contenir **une colonne `domain`** (ex.: `breitbart.com`).
* Pour chaque page Wikipédia :
    1. Récupère le wikitext.
    2. Extrait toutes les URL dans les balises `<ref>`.
    3. Prend le nom de domaine (`urllib.parse.urlparse(url).hostname`).
    4. Logique de ratio NOUVELLE :
       - 0 domaine blacklisté → ratio = 0.0
       - 1 domaine blacklisté → ratio = 0.5  
       - 2+ domaines blacklistés → ratio = 1.0
* Retourne un `Series` avec ratios (0.0, 0.5, ou 1.0).
* La fonction `get_blacklisted_domains` retourne les domaines blacklistés trouvés par page.
"""

from __future__ import annotations
import pandas as pd, re, requests, time, pathlib
from typing import List, Dict
from urllib.parse import urlparse

UA = {"User-Agent": "BlacklistMetric/1.1 (opsci)"}
URL_REGEX = re.compile(r"https?://[^\s<>\"]+")


def _load_blacklist(path: str | pathlib.Path) -> set[str]:
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Blacklist introuvable : {p}")
    if p.suffix == ".csv":
        df = pd.read_csv(p)
        if "domain" in df.columns:
            return set(df["domain"].dropna().str.strip().str.lower())
        # fallback première colonne
        return set(df.iloc[:, 0].dropna().str.strip().str.lower())
    # txt une ligne par domaine
    return set(l.strip().lower() for l in p.read_text().splitlines() if l.strip())


def _wikitext(title: str, lang: str) -> str:
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "titles": title, "format": "json", "formatversion": 2
    }
    r = requests.get(api, params=params, headers=UA, timeout=20)
    r.raise_for_status()
    pg = r.json()["query"]["pages"][0]
    return pg.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")


def get_blacklist_share(pages: List[str], blacklist_csv="blacklist.csv", lang="fr") -> pd.Series:
    """
    Calcule le ratio de blacklist selon la nouvelle logique :
    - 0 domaine blacklisté → ratio = 0.0
    - 1 domaine blacklisté → ratio = 0.5
    - 2+ domaines blacklistés → ratio = 1.0
    """
    bl_domains = _load_blacklist(blacklist_csv)
    ratios = {}
    for p in pages:
        text = _wikitext(p, lang)
        urls = URL_REGEX.findall(text)
        if not urls:
            ratios[p] = 0.0
        else:
            domains = [urlparse(u).hostname or "" for u in urls]
            # Compter les domaines blacklistés uniques
            blacklisted_domains = set()
            for d in domains:
                for bd in bl_domains:
                    if bd in d:
                        blacklisted_domains.add(d)
            
            # Nouvelle logique de calcul du ratio
            num_blacklisted = len(blacklisted_domains)
            if num_blacklisted == 0:
                ratios[p] = 0.0
            elif num_blacklisted == 1:
                ratios[p] = 0.5
            else:  # 2 ou plus
                ratios[p] = 1.0
        time.sleep(0.1)
    return pd.Series(ratios, name="blacklist_share")


def get_blacklisted_domains(pages: List[str], blacklist_csv="blacklist.csv", lang="fr") -> Dict[str, List[str]]:
    """
    Retourne les domaines blacklistés trouvés pour chaque page (domaines uniques).
    
    Args:
        pages: Liste des titres de pages Wikipedia
        blacklist_csv: Chemin vers le fichier de blacklist
        lang: Code langue de Wikipedia
        
    Returns:
        Dict[page_title, List[unique_blacklisted_domains_found]]
    """
    bl_domains = _load_blacklist(blacklist_csv)
    blacklisted_by_page = {}
    
    for p in pages:
        print(f"Analyse des domaines blacklistés pour: {p}")
        text = _wikitext(p, lang)
        urls = URL_REGEX.findall(text)
        
        if not urls:
            blacklisted_by_page[p] = []
        else:
            domains = [urlparse(u).hostname or "" for u in urls]
            # Trouve les domaines blacklistés uniques
            blacklisted_domains = set()
            for d in domains:
                for bd in bl_domains:
                    if bd in d:
                        blacklisted_domains.add(d)
            blacklisted_by_page[p] = list(blacklisted_domains)
            
        num_found = len(blacklisted_by_page[p])
        print(f"  → {num_found} domaine(s) blacklisté(s) unique(s) trouvé(s)")
        if blacklisted_by_page[p]:
            print(f"     Domaines: {', '.join(sorted(blacklisted_by_page[p]))}")
        
        time.sleep(0.1)
    
    return blacklisted_by_page


def get_blacklist_analysis(pages: List[str], blacklist_csv="blacklist.csv", lang="fr") -> Dict:
    """
    Analyse complète des domaines blacklistés avec la nouvelle logique de ratios.
    Ratio : 0 = aucun, 0.5 = 1 domaine, 1.0 = 2+ domaines blacklistés
    
    Returns:
        Dict avec 'ratios' (Series) et 'blacklisted_domains' (Dict)
    """
    bl_domains = _load_blacklist(blacklist_csv)
    ratios = {}
    blacklisted_by_page = {}
    
    print(f"=== ANALYSE DES DOMAINES BLACKLISTÉS ===")
    print(f"Blacklist chargée: {len(bl_domains)} domaine(s)")
    print(f"Logique de ratio: 0 domaine=0.0, 1 domaine=0.5, 2+ domaines=1.0")
    print(f"Pages à analyser: {len(pages)}")
    print()
    
    for p in pages:
        print(f"📄 Analyse de: {p}")
        text = _wikitext(p, lang)
        urls = URL_REGEX.findall(text)
        
        if not urls:
            ratios[p] = 0.0
            blacklisted_by_page[p] = []
            print(f"   ⚠️  Aucune URL trouvée")
        else:
            domains = [urlparse(u).hostname or "" for u in urls]
            # Trouve les domaines blacklistés uniques
            blacklisted_domains = set()
            for d in domains:
                for bd in bl_domains:
                    if bd in d:
                        blacklisted_domains.add(d)
            
            blacklisted_by_page[p] = list(blacklisted_domains)
            
            # Nouvelle logique de calcul du ratio
            num_blacklisted = len(blacklisted_domains)
            if num_blacklisted == 0:
                ratios[p] = 0.0
                status = "✅ Aucun problème"
            elif num_blacklisted == 1:
                ratios[p] = 0.5
                status = "⚠️ Problème grave"
            else:  # 2 ou plus
                ratios[p] = 1.0
                status = "🚫 Page catastrophique"
            
            print(f"   📊 Total domaines: {len(domains)}")
            print(f"   🚫 Blacklistés: {num_blacklisted} → Ratio: {ratios[p]} ({status})")
            if blacklisted_domains:
                print(f"   📝 Domaines blacklistés: {', '.join(sorted(blacklisted_domains))}")
        
        print()
        time.sleep(0.1)
    
    return {
        'ratios': pd.Series(ratios, name="blacklist_share"),
        'blacklisted_domains': blacklisted_by_page
    }


# ───────────────────────────  CLI test ─────────────────────────
if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="Ratio de références blacklistées par article")
    ap.add_argument("pages", nargs="+", help="Titres d'articles")
    ap.add_argument("--blacklist", default="blacklist.csv", help="Chemin vers blacklist.csv")
    ap.add_argument("--lang", default="fr", help="Code langue wiki")
    ap.add_argument("--mode", choices=["ratio", "domains", "analysis"], default="ratio", 
                   help="Mode: ratio (défaut), domains (domaines blacklistéspy), analysis (complet)")
    ap.add_argument("--json", action="store_true", help="Affiche le résultat en JSON")
    ns = ap.parse_args()

    if ns.mode == "ratio":
        res = get_blacklist_share(ns.pages, ns.blacklist, ns.lang)
        if ns.json:
            print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(res.to_markdown())
    
    elif ns.mode == "domains":
        domains = get_blacklisted_domains(ns.pages, ns.blacklist, ns.lang)
        if ns.json:
            print(json.dumps(domains, ensure_ascii=False, indent=2))
        else:
            print("\n=== DOMAINES BLACKLISTÉS PAR PAGE ===")
            for page, bl_domains in domains.items():
                print(f"\n{page}:")
                if bl_domains:
                    for domain in bl_domains:
                        print(f"  • {domain}")
                else:
                    print("  ✅ Aucun domaine blacklisté")
    
    elif ns.mode == "analysis":
        analysis = get_blacklist_analysis(ns.pages, ns.blacklist, ns.lang)
        
        if ns.json:
            result = {
                'ratios': analysis['ratios'].to_dict(),
                'blacklisted_domains': analysis['blacklisted_domains']
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("=== RÉSUMÉ FINAL ===")
            print("\n📊 Ratios par page (0.0=aucun, 0.5=1 domaine, 1.0=2+ domaines):")
            print(analysis['ratios'].to_markdown())
            
            print(f"\n🚫 Domaines blacklistés trouvés:")
            for page, bl_domains in analysis['blacklisted_domains'].items():
                if bl_domains:
                    print(f"  {page}: {', '.join(bl_domains)}")
                else:
                    print(f"  {page}: ✅ Aucun")