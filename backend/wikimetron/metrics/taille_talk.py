#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple, Union

import requests
import pandas as pd

# ----------------------
# Config & constantes
# ----------------------
TALK_NS = {
    "FR": "Discussion",       # français
    "EN": "Talk",             # anglais
    "DE": "Diskussion",       # allemand
    "IT": "Discussione",      # italien
    "ES": "Discusión",        # espagnol
    "CA": "Discussió",        # catalan
    "PT": "Discussão",        # portugais
    "ET": "Arutelu",          # estonien
    "LV": "Diskusija",        # letton
    "LT": "Aptarimas",        # lituanien
    "RO": "Discuție",         # roumain
    "UK": "Обговорення",      # ukrainien
    "BE": "Размовы",          # biélorusse
    "RU": "Обсуждение",       # russe
    "NL": "Overleg",          # néerlandais
    "DA": "Diskussion",       # danois
    "SV": "Diskussion",       # suédois
    "NO": "Diskusjon",        # norvégien
    "FI": "Keskustelu",       # finnois (corrigé : pas "Etusivu" = page d’accueil)
    "IS": "Spjall",           # islandais
    "PL": "Dyskusja",         # polonais
    "HU": "Vita",          # hongrois
    "CS": "Diskuse",          # tchèque
    "SK": "Diskusia",         # slovaque
    "BG": "Беседа",           # bulgare
    "SR": "Разговор",         # serbe
    "SH": "Razgovor",         # serbo-croate
    "HR": "Razgovor",         # croate
    "BS": "Razgovor",         # bosniaque
    "MK": "Разговор",         # macédonien
    "SL": "Pogovor",          # slovène (corrigé : pas "Diskusia")
    "SQ": "Diskutim",        # albanais
    "EL": "Συζήτηση",         # grec
    "TR": "Tartışma",         # turc

    "KA": "განხილვა",         # géorgien
    "HY": "Քննարկում",        # arménien
    "HE": "שיחה",             # hébreu
    "AR": "نقاش",             # arabe
    "ARZ": "نقاش",            # arabe égyptien
    "FA": "بحث",              # persan
    "HI": "वार्ता",           # hindi
    "ID": "Pembicaraan",      # indonésien
    "CEB": "Hisgot",          # cebuano
    "ZH": "Talk",             # chinois
    "JA": "ノート",           # japonais
}

DEFAULT_UA = "wikimetron/1.0 (research)"
TRANSIENT_CODES = {429, 500, 502, 503, 504, 403} 

# ----------------------
# Utils
# ----------------------

def log(msg: str, level: str = "INFO", enabled: bool = True, stderr: bool = False):
    if not enabled:
        return
    stream = sys.stderr if stderr or level in {"WARN", "ERROR"} else sys.stdout
    print(f"[{level}] {msg}", file=stream, flush=True)

def to_iso_utc(dt):
    """Accepte 'YYYY-MM-DD' ou datetime -> ISO 8601 UTC (string)."""
    if isinstance(dt, str):
        dt = datetime.strptime(dt, "%Y-%m-%d")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")

def make_session(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": user_agent or DEFAULT_UA,
    
    })
    return s

def http_get_with_retry(
    session: requests.Session,
    url: str,
    params: dict,
    timeout: int,
    max_tries: int,
    sleep_base: float,
    verbose: bool,
) -> requests.Response:
    delay = sleep_base
    tries = 0
    while True:
        tries += 1
        r = session.get(url, params=params, timeout=timeout)
        if r.status_code < 400:
            return r
        if r.status_code in TRANSIENT_CODES and tries < max_tries:
            # log hint
            try:
                err_snip = r.json()
            except Exception:
                err_snip = r.text[:300]
            log(f"HTTP {r.status_code} transitoire. Retry {tries}/{max_tries-1} dans {delay:.1f}s. Détails: {err_snip}", "WARN", enabled=verbose, stderr=True)
            time.sleep(delay)
            delay *= 2
            continue
        # fatal
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            # ajouter l'URL complète pour debug
            log(f"Échec HTTP {r.status_code} sur {r.url}", "ERROR", enabled=True, stderr=True)
            raise e

# ----------------------
# Cœur métier
# ----------------------

def fetch_revisions(
    session: requests.Session,
    lang: str,
    talk_title: str,
    start_iso: str,
    end_iso: str,
    timeout: int,
    max_tries: int,
    sleep_base: float,
    verbose: bool,
) -> List[dict]:
    """Récupère toutes les révisions entre deux bornes (rvdir=newer)."""
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": talk_title,
        "prop": "revisions",
        "rvprop": "timestamp|comment",
        "rvlimit": "max",
        "rvdir": "newer",
        "rvstart": start_iso,
        "rvend": end_iso,
        "format": "json",
        "formatversion": "2",
        "origin": "*",
        "maxlag": "5",
    }
    revisions: List[dict] = []
    cont = None
    while True:
        if cont:
            params["rvcontinue"] = cont
        if verbose:
            log(f"GET revisions: {talk_title} (continue={cont})", "DEBUG", enabled=True)
        resp = http_get_with_retry(session, api_url, params, timeout, max_tries, sleep_base, verbose)
        data = resp.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages or "revisions" not in pages[0]:
            break

        chunk = pages[0]["revisions"]
        revisions.extend(chunk)

        cont = data.get("continue", {}).get("rvcontinue")
        if not cont:
            break
    return revisions

def count_revisions_in_period(
    page_title: str,
    start_dt,
    end_dt,
    lang: str = "fr",
    talk_ns: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 30,
    max_tries: int = 5,
    sleep_base: float = 1.0,
    verbose: bool = False,
) -> Tuple[int, List[dict], str]:
    """Retourne (n, revisions, talk_title)."""
    ns = talk_ns or TALK_NS.get(lang.upper(), "Talk")
    talk_title = f"{ns}:{page_title}"
    start_iso = to_iso_utc(start_dt)
    end_iso = to_iso_utc(end_dt)
    sess = session or make_session(DEFAULT_UA)
    revs = fetch_revisions(sess, lang, talk_title, start_iso, end_iso, timeout, max_tries, sleep_base, verbose)
    return len(revs), revs, talk_title

def count_sections_from_revisions(revisions: List[dict]) -> int:
    """
    Approx "nouveaux fils" : on compte les révisions dont le commentaire
    d'édition contient un marqueur de section: /* Titre */
    """
    n = 0
    for r in revisions:
        c = (r.get("comment") or "").strip()
        if c.startswith("/* ") and " */" in c:
            n += 1
    return n

def discussion_score(
    pages: Iterable[str],
    start_date,
    end_date,
    lang: str = "fr",
    talk_ns: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 30,
    max_tries: int = 5,
    sleep_base: float = 1.0,
    verbose: bool = False,
    count_mode: str = "revisions",  # or "sections"
) -> pd.Series:
    """
    Retourne seulement la Series des scores (pour l'intégration dans le pipeline).
    """
    scores = {}

    sess = session or make_session(DEFAULT_UA)
    for page in pages:
        n_revs, revs, talk_title = count_revisions_in_period(
            page, start_date, end_date, lang=lang, talk_ns=talk_ns,
            session=sess, timeout=timeout, max_tries=max_tries,
            sleep_base=sleep_base, verbose=verbose
        )
        if count_mode == "sections":
            n = count_sections_from_revisions(revs)
        else:
            n = n_revs
        score = min(1.0, 0.1 * n)
        scores[page] = score
        
        # courtoisie entre pages
        time.sleep(0.2)

    return pd.Series(scores, name=f"discussion_score_{lang}_{count_mode}")

def discussion_score_with_stats_for_cli(
    pages: Iterable[str],
    start_date,
    end_date,
    lang: str = "fr",
    talk_ns: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 30,
    max_tries: int = 5,
    sleep_base: float = 1.0,
    verbose: bool = False,
    count_mode: str = "revisions",  # or "sections"
) -> Tuple[pd.Series, Dict[str, dict]]:
    """
    Version avec statistiques détaillées pour le CLI.
    """
    stats: Dict[str, dict] = {}
    scores = {}

    sess = session or make_session(DEFAULT_UA)
    for page in pages:
        n_revs, revs, talk_title = count_revisions_in_period(
            page, start_date, end_date, lang=lang, talk_ns=talk_ns,
            session=sess, timeout=timeout, max_tries=max_tries,
            sleep_base=sleep_base, verbose=verbose
        )
        if count_mode == "sections":
            n = count_sections_from_revisions(revs)
        else:
            n = n_revs
        score = min(1.0, 0.1 * n)
        scores[page] = score
        stats[page] = {
            "talk_title": talk_title,
            "revisions": n_revs,
            "sections": count_sections_from_revisions(revs),
            "score": score,
        }
        if verbose:
            log(f"{page} -> talk='{talk_title}', revisions={n_revs}, sections={stats[page]['sections']}, score={score:.2f}", "INFO", enabled=True)

        # courtoisie entre pages
        time.sleep(0.2)

    return pd.Series(scores, name=f"discussion_score_{lang}_{count_mode}"), stats

# ----------------------
# CLI
# ----------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Calcule un score d'activité des pages de discussion Wikipedia sur un intervalle donné.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("lang", help="Code langue du wiki (fr, en, de, ...).")
    p.add_argument("pages", nargs="+", help="Titres d'articles SANS namespace (un ou plusieurs).")
    p.add_argument("--start", required=True, help="Date de début (YYYY-MM-DD).")
    p.add_argument("--end", required=True, help="Date de fin (YYYY-MM-DD).")
    p.add_argument("--talk-ns", default=None, help="Namespace de discussion (override).")
    p.add_argument("--count-mode", choices=["revisions", "sections"], default="revisions",
                   help="Mode de comptage : révisions (par défaut) ou ouvertures de sections (approx).")
    p.add_argument("--timeout", type=int, default=30, help="Timeout HTTP (s).")
    p.add_argument("--max-tries", type=int, default=5, help="Nombre max de retries HTTP.")
    p.add_argument("--sleep", type=float, default=1.0, help="Backoff initial entre retries (s).")
    p.add_argument("--user-agent", default=DEFAULT_UA, help="User-Agent à envoyer à l'API.")
    p.add_argument("--format", choices=["table", "json", "csv"], default="table", help="Format de sortie.")
    p.add_argument("--output", default=None, help="Chemin fichier de sortie (json/csv).")
    p.add_argument("--verbose", action="store_true", help="Logs détaillés.")
    p.add_argument("--quiet", action="store_true", help="Réduit la verbosité (silence hors erreurs).")
    return p.parse_args(argv)

def main(argv: List[str]) -> int:
    args = parse_args(argv)

    verbose = args.verbose and not args.quiet
    if args.quiet:
        # silencieux : on n'écrit que les erreurs
        pass

    # Rappel de la commande
    if verbose:
        log(
            f"Lang={args.lang} | Pages={args.pages} | Start={args.start} | End={args.end} | "
            f"Mode={args.count_mode} | UA='{args.user_agent}' | Timeout={args.timeout}s | "
            f"MaxTries={args.max_tries} | Sleep={args.sleep}s",
            "INFO", enabled=True
        )

    # Session HTTP
    session = make_session(args.user_agent)

    t0 = time.time()
    try:
        series, stats = discussion_score_with_stats_for_cli(
            args.pages,
            args.start,
            args.end,
            lang=args.lang,
            talk_ns=args.talk_ns,
            session=session,
            timeout=args.timeout,
            max_tries=args.max_tries,
            sleep_base=args.sleep,
            verbose=verbose,
            count_mode=args.count_mode,
        )
    except Exception as e:
        log(f"Échec: {e}", "ERROR", enabled=True, stderr=True)
        return 2

    elapsed = time.time() - t0

    # Sortie
    if args.format == "table":
        # Impression lisible en console
        if not args.quiet:
            print(series.to_string())
    elif args.format == "json":
        payload = {
            "lang": args.lang,
            "start": args.start,
            "end": args.end,
            "count_mode": args.count_mode,
            "results": [
                {
                    "page": page,
                    "talk_title": stats[page]["talk_title"],
                    "revisions": stats[page]["revisions"],
                    "sections": stats[page]["sections"],
                    "score": stats[page]["score"],
                }
                for page in series.index
            ],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "elapsed_seconds": round(elapsed, 3),
        }
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            if verbose:
                log(f"JSON écrit -> {args.output}", "INFO", enabled=True)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.format == "csv":
        rows = []
        for page in series.index:
            rows.append({
                "page": page,
                "talk_title": stats[page]["talk_title"],
                "revisions": stats[page]["revisions"],
                "sections": stats[page]["sections"],
                "score": stats[page]["score"],
                "lang": args.lang,
                "start": args.start,
                "end": args.end,
                "count_mode": args.count_mode,
            })
        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            if verbose:
                log(f"CSV écrit -> {args.output}", "INFO", enabled=True)
        else:
            # stdout CSV
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    # Stats finales
    if verbose:
        total_revs = sum(s["revisions"] for s in stats.values())
        total_secs = sum(s["sections"] for s in stats.values())
        log(
            f"Terminé en {elapsed:.2f}s — pages={len(stats)} | révisions={total_revs} | sections={total_secs}",
            "INFO",
            enabled=True,
        )
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))