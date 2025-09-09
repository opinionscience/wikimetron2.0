# app.py — Wikimetron API (multi-lang v2)
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import logging
import traceback
import pandas as pd

# ────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# FastAPI App
# ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Wikimetron API",
    description="Wikipedia Content Intelligence Platform with Multi-language (per-page) support",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8300",
        "http://127.0.0.1:8300",
        "http://37.59.112.214:8300",
        "http://37.59.112.214",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ────────────────────────────────────────────────────────────────────
# Pydantic Models (adaptés multi-lang)
# ────────────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    pages: List[str]
    start_date: str
    end_date: str
    default_language: Optional[str] = "fr"  # utilisé uniquement si une page n’a pas de langue

class PageviewsRequest(BaseModel):
    pages: List[str]
    start_date: str
    end_date: str
    default_language: Optional[str] = "fr"

class EditTimeseriesRequest(BaseModel):
    pages: List[str]
    start_date: str
    end_date: str
    editor_type: str = "user"  # "user" ou "all"
    default_language: Optional[str] = "fr"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    estimated_time: Optional[int] = None
    languages: Dict[str, int] = {}  # répartition par langue (ex: {"fr": 3, "en": 2})

# ────────────────────────────────────────────────────────────────────
# Stockage in-memory des tâches (prod: Redis/DB)
# ────────────────────────────────────────────────────────────────────
tasks_storage: Dict[str, Dict[str, Any]] = {}

def update_task_status(task_id: str, status: str, results: dict = None, error: str = None):
    if task_id in tasks_storage:
        tasks_storage[task_id]["status"] = status
        tasks_storage[task_id]["updated_at"] = datetime.now()
        if results is not None:
            tasks_storage[task_id]["results"] = results
        if error is not None:
            tasks_storage[task_id]["error"] = error

# ────────────────────────────────────────────────────────────────────
# Utilitaires multi-lang (s’appuient sur le nouveau pipeline)
# ────────────────────────────────────────────────────────────────────
def prepare_pages_and_languages(pages: List[str], default_language: str = "fr"):
    """
    Retourne:
      - page_infos: list[PageInfo] (original_input, clean_title, language, unique_key)
      - lang_counts: dict[str, int]
      - grouped: dict[lang, list[PageInfo]]
    """
    try:
        from wikimetron.metrics.pipeline import (
            prepare_pages_with_languages,
            group_pages_by_language,
        )
    except ImportError:
        # fallback minimal si import impossible
        def naive_detect(url: str):
            import re
            m = re.search(r"https?://([a-z]{2})\.wikipedia\.org", url or "")
            return m.group(1) if m else None

        page_infos = []
        from dataclasses import dataclass

        @dataclass
        class PageInfoLocal:
            original_input: str
            clean_title: str
            language: str
            unique_key: str

        from urllib.parse import urlparse, unquote
        for p in pages:
            lang = naive_detect(p) or default_language
            title = p
            try:
                if isinstance(p, str) and p.startswith("http"):
                    parsed = urlparse(p)
                    if "wikipedia.org" in parsed.netloc and "/wiki/" in parsed.path:
                        raw = parsed.path.split("/wiki/")[1]
                        title = unquote(raw.replace("_", " "))
            except Exception:
                pass
            page_infos.append(PageInfoLocal(
                original_input=p,
                clean_title=title,
                language=lang,
                unique_key=f"{title}___{lang}"
            ))
        grouped: Dict[str, List[PageInfoLocal]] = {}
        for pi in page_infos:
            grouped.setdefault(pi.language, []).append(pi)
        from collections import Counter
        lang_counts = dict(Counter([pi.language for pi in page_infos]))
        return page_infos, lang_counts, grouped

    page_infos = prepare_pages_with_languages(pages, default_language)
    grouped = group_pages_by_language(page_infos)
    from collections import Counter
    lang_counts = dict(Counter([p.language for p in page_infos]))
    return page_infos, lang_counts, grouped

# ────────────────────────────────────────────────────────────────────
# Background Runner — utilise le wrapper multi-lang
# ────────────────────────────────────────────────────────────────────
async def run_analysis_background(task_id: str, request_data: dict):
    try:
        logger.info(f"Début analyse (task={task_id})")
        update_task_status(task_id, "running")

        from wikimetron.metrics.pipeline import compute_scores_for_api_multilang

        pages = request_data.get("pages", [])
        start_date = request_data.get("start_date")
        end_date = request_data.get("end_date")
        default_language = request_data.get("default_language", "fr")

        # Appel du NOUVEAU wrapper multi-langues
        results = compute_scores_for_api_multilang(
            pages=pages,
            start_date=start_date,
            end_date=end_date,
            default_language=default_language,
        )

        update_task_status(task_id, "completed", results=results)
        logger.info(f"Analyse terminée (task={task_id})")
    except Exception as e:
        logger.error(f"Erreur task {task_id}: {e}")
        logger.error(traceback.format_exc())
        update_task_status(task_id, "error", error=str(e))

# ────────────────────────────────────────────────────────────────────
# Routes basiques
# ────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "message": "Wikimetron API (multi-language per-page)",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "operational",
        "features": [
            "Per-page language detection",
            "Mixed-language inputs in one request",
            "Parallel metrics computation",
            "Heat/Quality/Risk + unique_key",
            "Timeseries endpoints grouping by language",
        ],
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ────────────────────────────────────────────────────────────────────
# ENDPOINTS PRINCIPAUX (multi-lang)
# ────────────────────────────────────────────────────────────────────
@app.post("/api/analyze", response_model=TaskResponse)
async def analyze_pages(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    if not request.pages:
        raise HTTPException(status_code=400, detail="Au moins une page est requise")
    if len(request.pages) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 pages par analyse")

    # Détecter et résumer les langues par page
    _, lang_counts, _ = prepare_pages_and_languages(request.pages, request.default_language)

    task_id = str(uuid.uuid4())
    tasks_storage[task_id] = {
        "status": "queued",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "pages": request.pages,
        "languages": lang_counts,
        "request": request.dict(),
    }

    # Lancer l’analyse multi-lang en arrière-plan
    background_tasks.add_task(run_analysis_background, task_id, request.dict())

    logger.info(f"Tâche {task_id} créée: {len(request.pages)} pages / langues={lang_counts}")
    return TaskResponse(
        task_id=task_id,
        status="queued",
        estimated_time=len(request.pages) * 10,
        languages=lang_counts,
    )

# ────────────────────────────────────────────────────────────────────
# Timeseries: Pageviews (multi-lang)
# ────────────────────────────────────────────────────────────────────
@app.post("/api/pageviews")
async def get_pageviews_timeseries(request: PageviewsRequest):
    try:
        if not request.pages:
            raise HTTPException(status_code=400, detail="Au moins une page est requise")
        if len(request.pages) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 pages pour les graphiques")

        from wikimetron.metrics.pageviews import get_pageviews_timeseries

        page_infos, lang_counts, grouped = prepare_pages_and_languages(request.pages, request.default_language)

        # mapping original -> PageInfo
        orig_to_pi = {pi.original_input: pi for pi in page_infos}

        # Récupération timeseries par langue (sur titres nettoyés)
        per_page_series: Dict[str, pd.Series] = {}
        for lang, pis in grouped.items():
            titles = [pi.clean_title for pi in pis]
            if not titles:
                continue
            lang_ts = get_pageviews_timeseries(
                titles,
                request.start_date,
                request.end_date,
                lang,
            )
            # Remapper vers clé "original_input"
            for pi in pis:
                s = lang_ts.get(pi.clean_title, pd.Series(dtype="int64"))
                per_page_series[pi.original_input] = s

        # Construire la grille de dates
        all_dates = set()
        for s in per_page_series.values():
            if not s.empty:
                all_dates.update(pd.to_datetime(s.index).strftime("%Y-%m-%d"))
        sorted_dates = sorted(all_dates)

        chart_data = []
        for d in sorted_dates:
            row = {"date": d}
            for original in request.pages:
                s = per_page_series.get(original, pd.Series(dtype="int64"))
                val = 0
                if not s.empty:
                    idx = pd.to_datetime(d)
                    if idx in s.index:
                        try:
                            val = int(s.loc[idx])
                        except Exception:
                            val = int(s.loc[idx].item())
                row[original] = val
            chart_data.append(row)

        # Statistiques par page
        pages_metadata = {}
        for original in request.pages:
            s = per_page_series.get(original, pd.Series(dtype="int64"))
            if s is None or s.empty:
                pages_metadata[original] = {"total_views": 0, "avg_views": 0, "max_views": 0, "data_points": 0}
            else:
                pages_metadata[original] = {
                    "total_views": int(s.sum()),
                    "avg_views": round(float(s.mean()), 2),
                    "max_views": int(s.max()),
                    "data_points": int(s.shape[0]),
                }

        return {
            "success": True,
            "data": chart_data,
            "metadata": {
                "pages": request.pages,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "languages_summary": lang_counts,
                "default_language": request.default_language,
                "total_points": len(chart_data),
                "pages_stats": pages_metadata,
            },
        }
    except Exception as e:
        logger.error(f"Erreur pageviews: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des pageviews: {str(e)}")

# ────────────────────────────────────────────────────────────────────
# Timeseries: Edits (multi-lang)
# ────────────────────────────────────────────────────────────────────
@app.post("/api/edit-timeseries")
async def get_edit_timeseries(request: EditTimeseriesRequest):
    try:
        if not request.pages:
            raise HTTPException(status_code=400, detail="Au moins une page est requise")
        if len(request.pages) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 pages pour les graphiques")

        from wikimetron.metrics.edit import EditProcessor

        page_infos, lang_counts, grouped = prepare_pages_and_languages(request.pages, request.default_language)
        # mapping original -> PageInfo
        orig_to_pi = {pi.original_input: pi for pi in page_infos}

        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")

        # Récupération des séries par langue
        per_page_daily: Dict[str, List[int]] = {}
        for lang, pis in grouped.items():
            processor = EditProcessor(lang, request.editor_type)
            for pi in pis:
                try:
                    daily = processor.fetch_daily_edits_optimized(pi.clean_title, start_date, end_date)
                    per_page_daily[pi.original_input] = list(map(int, daily))
                except Exception as e:
                    logger.warning(f"Échec éditions pour {pi.original_input} ({lang}): {e}")
                    num_days = (end_date - start_date).days + 1
                    per_page_daily[pi.original_input] = [0] * num_days

        # Construire chart_data
        chart_data = []
        current_date = start_date
        idx = 0
        num_days = (end_date - start_date).days + 1
        while idx < num_days:
            point = {"date": current_date.strftime("%Y-%m-%d")}
            for original in request.pages:
                series = per_page_daily.get(original, [])
                point[original] = int(series[idx]) if idx < len(series) else 0
            chart_data.append(point)
            current_date += timedelta(days=1)
            idx += 1

        # Stats par page
        pages_metadata = {}
        for original in request.pages:
            series = per_page_daily.get(original, [])
            total_edits = int(sum(series)) if series else 0
            max_edits = int(max(series)) if series else 0
            avg_edits = float(total_edits / len(series)) if series else 0.0
            pages_metadata[original] = {
                "total_edits": total_edits,
                "avg_edits": round(avg_edits, 2),
                "max_edits": max_edits,
                "data_points": len(series),
            }

        return {
            "success": True,
            "data": chart_data,
            "metadata": {
                "pages": request.pages,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "languages_summary": lang_counts,
                "default_language": request.default_language,
                "editor_type": request.editor_type,
                "total_points": len(chart_data),
                "pages_stats": pages_metadata,
            },
        }
    except Exception as e:
        logger.error(f"Erreur éditions: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données d'éditions: {str(e)}")

# ────────────────────────────────────────────────────────────────────
# Gestion des tâches
# ────────────────────────────────────────────────────────────────────
@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    task = tasks_storage[task_id].copy()
    if "created_at" in task:
        task["created_at"] = task["created_at"].isoformat()
    if "updated_at" in task:
        task["updated_at"] = task["updated_at"].isoformat()
    return task

@app.get("/api/tasks")
async def list_tasks():
    return {
        "tasks": [
            {
                "task_id": tid,
                "status": t["status"],
                "created_at": t["created_at"].isoformat(),
                "updated_at": t.get("updated_at", t["created_at"]).isoformat(),
                "pages_count": len(t.get("pages", [])),
                "languages": t.get("languages", {}),
            }
            for tid, t in tasks_storage.items()
        ]
    }

# ────────────────────────────────────────────────────────────────────
# Détection de langue (multi-lang)
# ────────────────────────────────────────────────────────────────────
@app.post("/api/detect-language")
async def detect_language_endpoint(pages: List[str], default_language: str = "fr"):
    try:
        if not pages:
            raise HTTPException(status_code=400, detail="Au moins une page est requise")

        # Utilise les helpers du nouveau pipeline
        try:
            from wikimetron.metrics.pipeline import extract_clean_title_and_language, prepare_pages_with_languages, group_pages_by_language
            page_infos = prepare_pages_with_languages(pages, default_language)
            grouped = group_pages_by_language(page_infos)
        except Exception:
            # fallback sur utilitaire local
            page_infos, _, grouped = prepare_pages_and_languages(pages, default_language)

        page_analysis = []
        for pi in page_infos:
            page_analysis.append({
                "original": pi.original_input,
                "clean_title": pi.clean_title,
                "detected_language": pi.language,
                "unique_key": pi.unique_key,
                "is_url": isinstance(pi.original_input, str) and pi.original_input.startswith("http"),
            })

        from collections import Counter
        lang_counts = dict(Counter([pi.language for pi in page_infos]))

        return {
            "languages_summary": lang_counts,
            "pages": page_analysis,
            "summary": {
                "total_pages": len(pages),
                "urls_count": len([p for p in pages if isinstance(p, str) and p.startswith("http")]),
                "titles_count": len([p for p in pages if not (isinstance(p, str) and p.startswith("http"))]),
                "default_language": default_language,
            },
        }
    except Exception as e:
        logger.error(f"Erreur détection langue: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la détection: {str(e)}")

# ────────────────────────────────────────────────────────────────────
# Langues supportées
# ────────────────────────────────────────────────────────────────────
@app.get("/api/supported-languages")
async def get_supported_languages():
    return {
        "supported_languages": [
            {"code": "en", "name": "English", "wikipedia": "en.wikipedia.org", "talk": "Talk"},
            {"code": "fr", "name": "Français", "wikipedia": "fr.wikipedia.org", "talk": "Discussion"},
            {"code": "de", "name": "Deutsch", "wikipedia": "de.wikipedia.org", "talk": "Diskussion"},
            {"code": "it", "name": "Italiano", "wikipedia": "it.wikipedia.org", "talk": "Discussione"},
            {"code": "es", "name": "Español", "wikipedia": "es.wikipedia.org", "talk": "Discusión"},
            {"code": "ca", "name": "Català", "wikipedia": "ca.wikipedia.org", "talk": "Discussió"},
            {"code": "pt", "name": "Português", "wikipedia": "pt.wikipedia.org", "talk": "Discussão"},
            {"code": "et", "name": "Eesti", "wikipedia": "et.wikipedia.org", "talk": "Arutelu"},
            {"code": "lv", "name": "Latviešu", "wikipedia": "lv.wikipedia.org", "talk": "Diskusija"},
            {"code": "lt", "name": "Lietuvių", "wikipedia": "lt.wikipedia.org", "talk": "Aptarimas"},
            {"code": "ro", "name": "Română", "wikipedia": "ro.wikipedia.org", "talk": "Discuție"},
            {"code": "uk", "name": "Українська", "wikipedia": "uk.wikipedia.org", "talk": "Обговорення"},
            {"code": "be", "name": "беларуская", "wikipedia": "be.wikipedia.org", "talk": "Размовы"},
            {"code": "ru", "name": "Русский", "wikipedia": "ru.wikipedia.org", "talk": "Обсуждение"},
            {"code": "nl", "name": "Nederlands", "wikipedia": "nl.wikipedia.org", "talk": "Overleg"},
            {"code": "da", "name": "Dansk", "wikipedia": "da.wikipedia.org", "talk": "Diskussion"},
            {"code": "sv", "name": "Svenska", "wikipedia": "sv.wikipedia.org", "talk": "Diskussion"},
            {"code": "no", "name": "Norsk", "wikipedia": "no.wikipedia.org", "talk": "Diskusjon"},
            {"code": "fi", "name": "Suomi", "wikipedia": "fi.wikipedia.org", "talk": "Etusivu"},
            {"code": "is", "name": "Íslenska", "wikipedia": "is.wikipedia.org", "talk": "Spjall"},
            {"code": "pl", "name": "Polski", "wikipedia": "pl.wikipedia.org", "talk": "Dyskusja"},
            {"code": "hu", "name": "Magyar", "wikipedia": "hu.wikipedia.org", "talk": "Vita"},
            {"code": "cs", "name": "Čeština", "wikipedia": "cs.wikipedia.org", "talk": "Diskuse"},
            {"code": "sk", "name": "Slovenčina", "wikipedia": "sk.wikipedia.org", "talk": "Diskusia"},
            {"code": "bg", "name": "Български", "wikipedia": "bg.wikipedia.org", "talk": "Беседа"},
            {"code": "sr", "name": "Српски", "wikipedia": "sr.wikipedia.org", "talk": "Разговор"},
            {"code": "sh", "name": "Srpskohrvatski", "wikipedia": "sh.wikipedia.org", "talk": "Razgovor"},
            {"code": "hr", "name": "Hrvatski", "wikipedia": "hr.wikipedia.org", "talk": "Razgovor"},
            {"code": "bs", "name": "Bosanski", "wikipedia": "bs.wikipedia.org", "talk": "Razgovor"},
            {"code": "mk", "name": "македонски", "wikipedia": "mk.wikipedia.org", "talk": "Разговор"},
            {"code": "sl", "name": "Slovenščina", "wikipedia": "sl.wikipedia.org", "talk": "Diskusija"},
            {"code": "sq", "name": "Shqip", "wikipedia": "sq.wikipedia.org", "talk": "Diskutim"},
            {"code": "el", "name": "Ελληνικά", "wikipedia": "el.wikipedia.org", "talk": "Συζήτηση"},
            {"code": "tr", "name": "Türkçe", "wikipedia": "tr.wikipedia.org", "talk": "Tartışma"},
            {"code": "ka", "name": "ქართული", "wikipedia": "ka.wikipedia.org", "talk": "განხილვა"},
            {"code": "hy", "name": "հայերեն", "wikipedia": "hy.wikipedia.org", "talk": "Քննարկում"},
            {"code": "he", "name": "עברית", "wikipedia": "he.wikipedia.org", "talk": "שיחה"},
            {"code": "ar", "name": "العربية", "wikipedia": "ar.wikipedia.org", "talk": "نقاش"},
            {"code": "arz", "name": "مصرى", "wikipedia": "arz.wikipedia.org", "talk": "نقاش"},
            {"code": "fa", "name": "فارسی", "wikipedia": "fa.wikipedia.org", "talk": "بحث"},
            {"code": "hi", "name": "हिन्दी", "wikipedia": "hi.wikipedia.org", "talk": "वार्ता"},
            {"code": "id", "name": "Bahasa Indonesia", "wikipedia": "id.wikipedia.org", "talk": "Pembicaraan"},
            {"code": "ceb", "name": "Cebuano", "wikipedia": "ceb.wikipedia.org", "talk": "Hisgot"},
            {"code": "zh", "name": "中文", "wikipedia": "zh.wikipedia.org", "talk": "Talk"},
            {"code": "ja", "name": "日本語", "wikipedia": "ja.wikipedia.org", "talk": "ノート"}
        ]
    ,
        "auto_detection": {
            "enabled": True,
            "fallback_language": "fr",
            "description": "Language is detected per page from Wikipedia URLs/titles; fallback applies only when missing.",
        },
    }

# ────────────────────────────────────────────────────────────────────
# Test pipeline — multi-lang
# ────────────────────────────────────────────────────────────────────
@app.post("/api/test-pipeline")
async def test_pipeline():
    try:
        from wikimetron.metrics.pipeline import compute_scores_for_api_multilang

        test_pages = [
            "https://fr.wikipedia.org/wiki/France",
            "https://en.wikipedia.org/wiki/Germany",
            "https://de.wikipedia.org/wiki/Paris",
            "Berlin",  # pas d’URL → prendra default_language
        ]

        results = compute_scores_for_api_multilang(
            test_pages, "2024-01-01", "2024-12-31", default_language="fr"
        )

        # petit résumé des langues à partir du payload retourné
        languages_summary = results.get("summary", {}).get("languages", {})

        return {
            "status": "success",
            "results": results,
            "test_info": {
                "pages_tested": test_pages,
                "languages_summary": languages_summary,
                "wrapper": "compute_scores_for_api_multilang",
            },
        }
    except Exception as e:
        logger.error(f"Erreur test pipeline: {e}")
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

# ────────────────────────────────────────────────────────────────────
# Entrypoint
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)