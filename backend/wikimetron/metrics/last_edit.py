#!/usr/bin/env python3
"""
Calcul simplifié du score de récence des pages Wikipédia.
Score de récence : 0 = récent, 1 = ancien
"""
import requests
import pandas as pd
from datetime import datetime, timezone
from typing import List, Optional
import argparse

UA = {"User-Agent": "WikiAnalyzer/2.0 (analysis@example.com)"}

class WikiPageAnalyzer:
    def __init__(self, lang: str = "fr"):
        self.lang = lang
        self.api_url = f"https://{lang}.wikipedia.org/w/api.php"
        
    def get_10th_revision_before(self, title: str, end_date: str) -> Optional[dict]:
        """Récupère la 10ème révision avant une date donnée (YYYY-MM-DD)."""
        # Convertir YYYY-MM-DD en format ISO pour l'API
        end_datetime = f"{end_date}T23:59:59Z"
        
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "revisions",
            "rvprop": "timestamp",
            "rvlimit": 10,            # Récupère les 10 dernières
            "rvstart": end_datetime,  # Commence à cette date
            "rvdir": "older"          # Va vers le passé
        }
        
        try:
            r = requests.get(self.api_url, headers=UA, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            page = next(iter(data["query"]["pages"].values()))
            
            # Vérifier si la page existe
            if "missing" in page:
                return None
                
            revisions = page.get("revisions", [])
            
            # Retourne la 10ème révision si elle existe, sinon la plus ancienne disponible
            if len(revisions) >= 10:
                return revisions[9]  # Index 9 = 10ème révision
            elif len(revisions) > 0:
                return revisions[-1]  # La plus ancienne disponible
            else:
                return None
            
        except Exception:
            return None
    
    def calculate_recency_score(self, title: str, end_date: str, max_days: int = 365) -> float:
        """Calcule le score de récence d'une page basé sur la 10ème révision par rapport à une date de référence."""
        tenth_rev = self.get_10th_revision_before(title, end_date)
        
        if not tenth_rev:
            return 1.0  # Score maximum si pas de révision trouvée
        
        # Date de référence (fin)
        end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
        
        # Date de la 10ème révision
        tenth_edit_dt = datetime.fromisoformat(tenth_rev["timestamp"].replace("Z", "+00:00"))
        
        # Calcul des jours écoulés
        days_since_edit = (end_dt - tenth_edit_dt).days
        
        # Score de récence (0 = récent, 1 = ancien)
        recency_score = min(1.0, days_since_edit / max_days)
        
        return recency_score

def get_recency_score(pages: List[str], lang: str = "fr", max_days: int = 365, end: str = None) -> pd.Series:
    """
    Calcule le score de récence pour chaque page Wikipedia basé sur la 10ème révision.
    
    Args:
        pages: Liste des titres de pages
        lang: Code langue (fr, en, etc.)
        max_days: Nombre de jours pour score maximal (défaut=365)
        end: Date de référence au format YYYY-MM-DD (défaut=aujourd'hui)
    
    Returns:
        Series indexée par page, valeurs entre 0 (récent) et 1 (ancien)
        Score basé sur la 10ème révision la plus récente avant la date de référence
    """
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")
    
    analyzer = WikiPageAnalyzer(lang)
    scores = {}
    
    for page in pages:
        score = analyzer.calculate_recency_score(page, end, max_days)
        scores[page] = score
    
    series = pd.Series(scores, name="recency_score")
    return series

# CLI simple
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse le score de récence des pages Wikipédia")
    
    parser.add_argument('pages', nargs='*', default=["Paris", "Lyon", "Marseille"],
                       help='Titres des pages à analyser')
    parser.add_argument('--lang', default='fr',
                       help='Code langue (fr, en, etc.)')
    parser.add_argument('--max-days', type=int, default=365,
                       help='Nombre de jours pour score maximal')
    parser.add_argument('--end-date',
                       help='Date de référence YYYY-MM-DD (défaut: aujourd\'hui)')
    
    args = parser.parse_args()
    
    # Calcul des scores
    scores = get_recency_score(
        pages=args.pages,
        lang=args.lang, 
        max_days=args.max_days,
        end=args.end_date
    )
    
    print(f"Scores de récence (langue: {args.lang}, max_days: {args.max_days}):")
    print(scores)