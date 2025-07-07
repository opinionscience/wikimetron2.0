#!/usr/bin/env python3
"""
Analyse enrichie des dernières modifications sur des pages Wikipédia.

Informations collectées:
  • Score de récence (0=récent, 1=ancien)
  • Dernier éditeur et commentaire
  • Taille de la page et changement
  • Nombre d'édits récents (7j, 30j, 90j)
  • Métadonnées de la page (création, protection, redirections)
  • Analyse d'activité

Usage:
    python last_edit_enhanced.py "Page 1" "Page 2" --lang fr --max_days 365 --detailed
"""
import requests
import pandas as pd
import time
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import argparse

UA = {"User-Agent": "WikiAnalyzer/2.0 (analysis@example.com)"}

class WikiPageAnalyzer:
    def __init__(self, lang: str = "fr"):
        self.lang = lang
        self.api_url = f"https://{lang}.wikipedia.org/w/api.php"
        
    def get_page_info(self, title: str) -> Dict:
        """Récupère les informations de base de la page."""
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "info|pageprops",
            "inprop": "protection|created|talkid|url|size",
            "ppprop": "disambiguation|redirect"
        }
        
        try:
            r = requests.get(self.api_url, headers=UA, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            page = next(iter(data["query"]["pages"].values()))
            
            if "missing" in page:
                return {"exists": False, "title": title}
                
            return {
                "exists": True,
                "title": page.get("title", title),
                "pageid": page.get("pageid"),
                "size": page.get("size", 0),
                "created": page.get("created"),
                "url": page.get("fullurl", ""),
                "is_redirect": "redirect" in page.get("pageprops", {}),
                "is_disambiguation": "disambiguation" in page.get("pageprops", {}),
                "protection": page.get("protection", [])
            }
        except Exception as e:
            return {"exists": False, "title": title, "error": str(e)}
    
    def get_recent_revisions(self, title: str, days: int = 90, limit: int = 500) -> List[Dict]:
        """Récupère les révisions récentes."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "revisions",
            "rvprop": "timestamp|user|comment|size|ids",
            "rvlimit": limit,
            "rvend": cutoff_str,  # ✅ S'arrête il y a X jours
            "rvdir": "older"      # ✅ Du présent vers le passé
        }
        
        try:
            r = requests.get(self.api_url, headers=UA, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            page = next(iter(data["query"]["pages"].values()))
            return page.get("revisions", [])
        except Exception:
            return []
    
    def get_latest_revision(self, title: str) -> Optional[Dict]:
        """Récupère la dernière révision avec détails."""
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "revisions",
            "rvprop": "timestamp|user|comment|size|ids",
            "rvlimit": 1
        }
        
        try:
            r = requests.get(self.api_url, headers=UA, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            page = next(iter(data["query"]["pages"].values()))
            revisions = page.get("revisions", [])
            return revisions[0] if revisions else None
        except Exception:
            return None
    
    def analyze_page(self, title: str, max_days: int = 365) -> Dict:
        """Analyse complète d'une page."""
        print(f"🔍 Analyse de: {title}")
        
        # Informations de base
        page_info = self.get_page_info(title)
        if not page_info["exists"]:
            return {
                "title": title,
                "exists": False,
                "error": page_info.get("error", "Page inexistante"),
                "recency_score": 1.0
            }
        
        # Dernière révision
        latest_rev = self.get_latest_revision(title)
        if not latest_rev:
            return {
                "title": title,
                "exists": True,
                "error": "Impossible de récupérer les révisions",
                "recency_score": 1.0
            }
        
        # Calcul du score de récence
        last_edit_dt = datetime.fromisoformat(latest_rev["timestamp"].replace("Z", "+00:00"))
        now_utc = datetime.now(timezone.utc)
        days_since_edit = (now_utc - last_edit_dt).days
        recency_score = min(1.0, days_since_edit / max_days)
        
        # Révisions récentes pour analyse d'activité
        recent_revs_90d = self.get_recent_revisions(title, days=90, limit=500)
        recent_revs_30d = [r for r in recent_revs_90d if self._days_ago(r["timestamp"]) <= 30]
        recent_revs_7d = [r for r in recent_revs_90d if self._days_ago(r["timestamp"]) <= 7]
        
        # Analyse des utilisateurs actifs
        users_90d = set(r.get("user", "Anonyme") for r in recent_revs_90d)
        users_30d = set(r.get("user", "Anonyme") for r in recent_revs_30d)
        
        # Calcul de la taille moyenne des changements
        size_changes = []
        for i in range(1, min(len(recent_revs_90d), 20)):  # 20 derniers changements
            if "size" in recent_revs_90d[i-1] and "size" in recent_revs_90d[i]:
                change = recent_revs_90d[i-1]["size"] - recent_revs_90d[i]["size"]
                size_changes.append(change)
        
        avg_change = sum(size_changes) / len(size_changes) if size_changes else 0
        
        # Classification de l'activité
        activity_level = self._classify_activity(len(recent_revs_30d), len(users_30d))
        
        return {
            "title": title,
            "exists": True,
            "pageid": page_info["pageid"],
            "url": page_info["url"],
            "current_size": page_info["size"],
            "created": page_info.get("created"),
            "is_redirect": page_info["is_redirect"],
            "is_disambiguation": page_info["is_disambiguation"],
            "protection": len(page_info["protection"]) > 0,
            
            # Dernière révision
            "last_edit_timestamp": latest_rev["timestamp"],
            "last_edit_user": latest_rev.get("user", "Anonyme"),
            "last_edit_comment": latest_rev.get("comment", "")[:100] + ("..." if len(latest_rev.get("comment", "")) > 100 else ""),
            "days_since_last_edit": days_since_edit,
            "recency_score": round(recency_score, 4),
            
            # Activité récente
            "edits_7d": len(recent_revs_7d),
            "edits_30d": len(recent_revs_30d),
            "edits_90d": len(recent_revs_90d),
            "unique_users_30d": len(users_30d),
            "unique_users_90d": len(users_90d),
            "avg_size_change": round(avg_change, 1),
            "activity_level": activity_level,
            
            # Méta
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _days_ago(self, timestamp: str) -> int:
        """Calcule le nombre de jours depuis un timestamp."""
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    
    def _classify_activity(self, edits_30d: int, users_30d: int) -> str:
        """Classifie le niveau d'activité de la page."""
        if edits_30d == 0:
            return "🔴 INACTIVE"
        elif edits_30d <= 2:
            return "🟡 FAIBLE"
        elif edits_30d <= 10:
            return "🟢 MODÉRÉE"
        elif edits_30d <= 30:
            return "🔵 ÉLEVÉE"
        else:
            return "🟣 TRÈS ÉLEVÉE"


def analyze_pages(pages: List[str], lang: str = "fr", max_days: int = 365, detailed: bool = False) -> pd.DataFrame:
    """Analyse un ensemble de pages et retourne un DataFrame."""
    analyzer = WikiPageAnalyzer(lang)
    results = []
    
    print(f"🚀 Analyse de {len(pages)} page(s) sur {lang}.wikipedia.org")
    print("=" * 60)
    
    for i, page in enumerate(pages, 1):
        print(f"[{i}/{len(pages)}] ", end="")
        result = analyzer.analyze_page(page, max_days)
        results.append(result)
        time.sleep(0.2)  # Rate limiting
    
    df = pd.DataFrame(results)
    
    # Réordonne les colonnes pour une meilleure lisibilité
    if not df.empty and detailed:
        column_order = [
            "title", "exists", "recency_score", "days_since_last_edit",
            "activity_level", "edits_30d", "edits_90d", "unique_users_30d",
            "current_size", "avg_size_change", "last_edit_user", "last_edit_comment",
            "is_redirect", "is_disambiguation", "protection", "url"
        ]
        # Garde seulement les colonnes qui existent
        available_cols = [col for col in column_order if col in df.columns]
        df = df[available_cols + [col for col in df.columns if col not in available_cols]]
    
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Analyse enrichie des dernières modifications sur des pages Wikipédia"
    )
    parser.add_argument("pages", nargs="+", help="Titres d'articles Wikipédia")
    parser.add_argument("--lang", default="fr", help="Code langue (fr, en, …)")
    parser.add_argument("--max_days", type=int, default=365, 
                       help="Nombre de jours pour score maximal (défaut=365)")
    parser.add_argument("--detailed", action="store_true", 
                       help="Affichage détaillé avec toutes les colonnes")
    parser.add_argument("--output", help="Fichier de sortie CSV (optionnel)")
    parser.add_argument("--json", action="store_true", 
                       help="Sortie au format JSON au lieu de tableau")
    
    args = parser.parse_args()
    
    # Analyse
    start_time = time.time()
    df = analyze_pages(args.pages, args.lang, args.max_days, args.detailed)
    end_time = time.time()
    
    print(f"\n⏱️  Analyse terminée en {end_time - start_time:.1f}s")
    print("=" * 60)
    
    if df.empty:
        print("❌ Aucune donnée récupérée")
        return
    
    # Affichage des résultats
    if args.json:
        result_json = df.to_json(orient="records", indent=2, force_ascii=False)
        print(result_json)
    else:
        if args.detailed:
            # Affichage détaillé
            for _, row in df.iterrows():
                print(f"\n📄 {row['title']}")
                if not row.get('exists', True):
                    print(f"   ❌ {row.get('error', 'Page inexistante')}")
                    continue
                    
                print(f"   🎯 Score de récence: {row['recency_score']:.3f} ({row['days_since_last_edit']} jours)")
                print(f"   📈 Activité: {row['activity_level']} ({row['edits_30d']} édits/30j)")
                print(f"   👤 Dernier éditeur: {row['last_edit_user']}")
                print(f"   💬 Commentaire: {row['last_edit_comment']}")
                print(f"   📊 Taille: {row['current_size']:,} octets (Δ moy: {row['avg_size_change']:+.1f})")
                
                flags = []
                if row.get('is_redirect'): flags.append("↪️ Redirection")
                if row.get('is_disambiguation'): flags.append("🔀 Homonymie")
                if row.get('protection'): flags.append("🔒 Protégée")
                if flags:
                    print(f"   🏷️  {' | '.join(flags)}")
        else:
            # Affichage résumé
            summary_cols = ["title", "recency_score", "days_since_last_edit", "activity_level", "edits_30d"]
            available_summary = [col for col in summary_cols if col in df.columns]
            print(df[available_summary].to_string(index=False))
    
    # Sauvegarde si demandée
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\n💾 Résultats sauvegardés dans: {args.output}")
    
    # Statistiques rapides
    if len(df) > 1 and not args.json:
        existing_pages = df[df.get('exists', True) == True]
        if not existing_pages.empty:
            print(f"\n📈 STATISTIQUES:")
            print(f"   Score moyen de récence: {existing_pages['recency_score'].mean():.3f}")
            print(f"   Page la plus récente: {existing_pages.loc[existing_pages['recency_score'].idxmin(), 'title']}")
            print(f"   Page la plus ancienne: {existing_pages.loc[existing_pages['recency_score'].idxmax(), 'title']}")

def get_recency_score(pages, lang="fr", max_days=365):
    """
    Calcule le score de récence pour chaque page Wikipedia.
    Retourne une Series indexée par page, valeurs entre 0 (récent) et 1 (ancien).
    """
    df = analyze_pages(pages, lang, max_days)
    # Si tu veux que le nom de la métrique soit explicite
    series = pd.Series(df.set_index("title")["recency_score"])
    series.name = "recency_score"
    return series

if __name__ == "__main__":
    main()