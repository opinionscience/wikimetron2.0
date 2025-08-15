from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
import asyncio
from datetime import datetime, timedelta
import logging
import traceback
import pandas as pd

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(
    title="Wikimetron API",
    description="Wikipedia Content Intelligence Platform with Auto Language Detection",
    version="1.1.0",  # Version mise à jour
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8300", 
        "http://127.0.0.1:8300",
        "http://37.59.112.214:8300",  # ← AJOUTER CETTE LIGNE
        "http://37.59.112.214"        # ← ET CELLE-CI aussi
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════
# MODÈLES PYDANTIC ADAPTÉS POUR LA DÉTECTION AUTOMATIQUE
# ═══════════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    pages: List[str]
    start_date: str
    end_date: str  
    language: Optional[str] = None  # 🔄 Maintenant optionnel pour détection auto

class PageviewsRequest(BaseModel):
    pages: List[str]
    start_date: str
    end_date: str
    language: Optional[str] = None  # 🔄 Optionnel aussi

class EditTimeseriesRequest(BaseModel):
    pages: List[str]
    start_date: str
    end_date: str
    language: Optional[str] = None  # 🔄 Optionnel aussi
    editor_type: str = "user"  # "user" ou "all"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    estimated_time: Optional[int] = None
    detected_language: Optional[str] = None  # 🆕 Nouveau champ

# Stockage temporaire des tâches (en production: Redis/DB)
tasks_storage = {}

def update_task_status(task_id: str, status: str, results: dict = None, error: str = None):
    """Met à jour le statut d'une tâche"""
    if task_id in tasks_storage:
        tasks_storage[task_id]["status"] = status
        tasks_storage[task_id]["updated_at"] = datetime.now()
        
        if results:
            tasks_storage[task_id]["results"] = results
        if error:
            tasks_storage[task_id]["error"] = error

async def run_analysis_background(task_id: str, request_data: dict):
    """Lance l'analyse en arrière-plan avec détection automatique de langue"""
    try:
        logger.info(f"Début de l'analyse pour la tâche {task_id}")
        update_task_status(task_id, "running")
        
        # Import du pipeline avec détection automatique
        from wikimetron.metrics.pipeline import compute_scores_for_api
        
        # Extraire les paramètres
        pages = request_data.get("pages", [])
        start_date = request_data.get("start_date")
        end_date = request_data.get("end_date")
        language = request_data.get("language")  # Peut être None pour détection auto
        
        # 🆕 Lancer l'analyse avec détection automatique
        results = compute_scores_for_api(pages, start_date, end_date, language)
        
        # Mettre à jour avec les résultats
        update_task_status(task_id, "completed", results=results)
        logger.info(f"Analyse terminée avec succès pour la tâche {task_id}")
        
    except Exception as e:
        error_msg = f"Erreur lors de l'analyse: {str(e)}"
        logger.error(f"Erreur dans la tâche {task_id}: {error_msg}")
        logger.error(traceback.format_exc())
        update_task_status(task_id, "error", error=error_msg)

def detect_language_from_request(pages: List[str], requested_language: Optional[str] = None) -> str:
    """
    Détermine la langue à utiliser : soit celle demandée, soit détection automatique
    """
    logger.info(f"🔍 === DEBUG detect_language_from_request ===")
    logger.info(f"📄 Pages reçues: {pages}")
    logger.info(f"📄 Type des pages: {[type(p) for p in pages]}")
    logger.info(f"🌐 Langue demandée: {requested_language}")
    
    if requested_language:
        logger.info(f"✅ Langue forcée par l'utilisateur: {requested_language}")
        return requested_language
    
    # Import de la fonction de détection
    try:
        logger.info(f"📦 Tentative d'import detect_language_from_pages...")
        from wikimetron.metrics.pipeline import detect_language_from_pages
        logger.info(f"✅ Import detect_language_from_pages: OK")
        
        logger.info(f"🔧 Appel detect_language_from_pages avec: {pages}")
        detected = detect_language_from_pages(pages)
        logger.info(f"🎯 Résultat detect_language_from_pages: {detected}")
        
        logger.info(f"✅ Langue détectée automatiquement: {detected}")
        logger.info(f"🔍 === FIN DEBUG detect_language_from_request ===")
        return detected
        
    except ImportError as e:
        logger.error(f"❌ Erreur d'import detect_language_from_pages: {e}")
        fallback = "fr"
        logger.info(f"🔄 Fallback sur: {fallback}")
        return fallback
        
    except Exception as e:
        logger.error(f"❌ Erreur dans detect_language_from_pages: {e}")
        logger.error(f"📚 Traceback complet:")
        logger.error(traceback.format_exc())
        
        # 🔧 TENTATIVE DE DÉTECTION MANUELLE EN CAS D'ERREUR
        logger.info(f"🔧 Tentative de détection manuelle...")
        
        for page in pages:
            logger.info(f"🔍 Analyse de la page: '{page}'")
            if isinstance(page, str) and "wikipedia.org" in page:
                try:
                    import re
                    match = re.search(r'https?://([a-z]{2})\.wikipedia\.org', page)
                    if match:
                        manual_lang = match.group(1)
                        logger.info(f"✅ Langue extraite manuellement: {manual_lang}")
                        return manual_lang
                    else:
                        logger.info(f"❌ Pas de match regex pour: {page}")
                except Exception as manual_error:
                    logger.error(f"❌ Erreur extraction manuelle: {manual_error}")
            else:
                logger.info(f"❌ Pas une URL Wikipedia: {page}")
        
        fallback = "fr"
        logger.info(f"🔄 Fallback final sur: {fallback}")
        return fallback
@app.get("/")
async def root():
    return {
        "message": "Wikimetron API with Auto Language Detection",
        "version": "1.1.0",
        "docs": "/docs",
        "status": "operational",
        "features": [
            "Automatic language detection from Wikipedia URLs",
            "Multi-language support",
            "Parallel metrics computation",
            "Real-time timeseries data"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS PRINCIPAUX ADAPTÉS
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/analyze", response_model=TaskResponse)
async def analyze_pages(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Lance une analyse Wikipedia avec détection automatique de langue"""
    
    # Validation
    if not request.pages:
        raise HTTPException(status_code=400, detail="Au moins une page est requise")
    
    if len(request.pages) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 pages par analyse")
    
    # 🆕 Détection automatique de langue
    try:
        detected_language = detect_language_from_request(request.pages, request.language)
    except Exception as e:
        logger.warning(f"Erreur lors de la détection de langue: {e}")
        detected_language = request.language or "fr"  # Fallback
    
    # Créer une tâche
    task_id = str(uuid.uuid4())
    tasks_storage[task_id] = {
        "status": "queued",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "pages": request.pages,
        "detected_language": detected_language,  # 🆕 Stockage de la langue détectée
        "request": request.dict()
    }
    
    # Mettre à jour la requête avec la langue détectée
    request_dict = request.dict()
    request_dict["language"] = detected_language
    
    # Lancer l'analyse en arrière-plan
    background_tasks.add_task(run_analysis_background, task_id, request_dict)
    
    logger.info(f"Tâche {task_id} créée pour {len(request.pages)} pages (langue: {detected_language})")
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        estimated_time=len(request.pages) * 10,
        detected_language=detected_language  # 🆕 Retour de la langue détectée
    )

@app.post("/api/pageviews")
async def get_pageviews_timeseries(request: PageviewsRequest):
    """Récupère les données de pageviews avec détection automatique de langue"""
    
    try:
        # 🆕 Détection automatique de langue
        detected_language = detect_language_from_request(request.pages, request.language)
        logger.info(f"Récupération pageviews pour {len(request.pages)} pages (langue: {detected_language})")
        
        # Validation
        if not request.pages:
            raise HTTPException(status_code=400, detail="Au moins une page est requise")
        
        if len(request.pages) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 pages pour les graphiques")
        
        # Import de la fonction pageviews
        from wikimetron.metrics.pageviews import get_pageviews_timeseries
        
        # 🔄 Utiliser la langue détectée
        timeseries_data = get_pageviews_timeseries(
            request.pages, 
            request.start_date, 
            request.end_date, 
            detected_language  # Langue détectée au lieu de request.language
        )
        
        # Convertir les données pour le graphique (même logique qu'avant)
        chart_data = []
        all_dates = set()
        
        # Collecter toutes les dates disponibles
        for page, series in timeseries_data.items():
            if not series.empty:
                all_dates.update(series.index.strftime('%Y-%m-%d'))
        
        # Créer une liste triée de dates
        sorted_dates = sorted(list(all_dates))
        
        # Construire les données pour le graphique
        for date_str in sorted_dates:
            data_point = {"date": date_str}
            
            for page, series in timeseries_data.items():
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    date_index = pd.to_datetime(date_obj)
                    
                    if date_index in series.index:
                        data_point[page] = int(series.loc[date_index])
                    else:
                        data_point[page] = 0
                except:
                    data_point[page] = 0
            
            chart_data.append(data_point)
        
        # Préparer les métadonnées avec langue détectée
        pages_metadata = {}
        for page, series in timeseries_data.items():
            if not series.empty:
                pages_metadata[page] = {
                    "total_views": int(series.sum()),
                    "avg_views": round(series.mean(), 2),
                    "max_views": int(series.max()),
                    "data_points": len(series)
                }
            else:
                pages_metadata[page] = {
                    "total_views": 0,
                    "avg_views": 0,
                    "max_views": 0,
                    "data_points": 0
                }
        
        result = {
            "success": True,
            "data": chart_data,
            "metadata": {
                "pages": request.pages,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "requested_language": request.language,  # 🆕 Langue demandée
                "detected_language": detected_language,   # 🆕 Langue détectée
                "total_points": len(chart_data),
                "pages_stats": pages_metadata
            }
        }
        
        logger.info(f"Pageviews récupérées: {len(chart_data)} points de données")
        return result
        
    except Exception as e:
        logger.error(f"Erreur pageviews: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des pageviews: {str(e)}")

@app.post("/api/edit-timeseries")
async def get_edit_timeseries(request: EditTimeseriesRequest):
    """Récupère les données d'éditions avec détection automatique de langue"""
    
    try:
        # 🆕 Détection automatique de langue
        detected_language = detect_language_from_request(request.pages, request.language)
        logger.info(f"Récupération données éditions pour {len(request.pages)} pages (langue: {detected_language})")
        
        # Validation
        if not request.pages:
            raise HTTPException(status_code=400, detail="Au moins une page est requise")
        
        if len(request.pages) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 pages pour les graphiques")
        
        # Import du module edit
        from wikimetron.metrics.edit import EditProcessor
        
        # Conversion des dates
        start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(request.end_date, '%Y-%m-%d')
        
        # 🔄 Créer le processeur avec la langue détectée
        processor = EditProcessor(detected_language, request.editor_type)
        
        # Récupérer les données pour chaque page (même logique qu'avant)
        edit_data = {}
        pages_metadata = {}
        
        for page in request.pages:
            try:
                logger.info(f"Traitement des éditions pour {page}")
                
                daily_counts = processor.fetch_daily_edits_optimized(page, start_date, end_date)
                edit_data[page] = daily_counts
                
                total_edits = sum(daily_counts)
                max_edits = max(daily_counts) if daily_counts else 0
                avg_edits = total_edits / len(daily_counts) if daily_counts else 0
                
                pages_metadata[page] = {
                    "total_edits": total_edits,
                    "avg_edits": round(avg_edits, 2),
                    "max_edits": max_edits,
                    "data_points": len(daily_counts)
                }
                
            except Exception as e:
                logger.error(f"Erreur pour {page}: {e}")
                num_days = (end_date - start_date).days + 1
                edit_data[page] = [0] * num_days
                pages_metadata[page] = {
                    "total_edits": 0,
                    "avg_edits": 0,
                    "max_edits": 0,
                    "data_points": num_days,
                    "error": str(e)
                }
        
        # Construire les données pour le graphique (même logique qu'avant)
        chart_data = []
        current_date = start_date
        date_index = 0
        
        while current_date <= end_date:
            data_point = {
                "date": current_date.strftime('%Y-%m-%d')
            }
            
            for page in request.pages:
                daily_counts = edit_data.get(page, [])
                if date_index < len(daily_counts):
                    data_point[page] = daily_counts[date_index]
                else:
                    data_point[page] = 0
            
            chart_data.append(data_point)
            current_date += timedelta(days=1)
            date_index += 1
        
        # Préparer la réponse avec langue détectée
        result = {
            "success": True,
            "data": chart_data,
            "metadata": {
                "pages": request.pages,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "requested_language": request.language,    # 🆕 Langue demandée
                "detected_language": detected_language,     # 🆕 Langue détectée
                "editor_type": request.editor_type,
                "total_points": len(chart_data),
                "pages_stats": pages_metadata
            }
        }
        
        logger.info(f"Données éditions récupérées: {len(chart_data)} points de données")
        return result
        
    except Exception as e:
        logger.error(f"Erreur éditions: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données d'éditions: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS DE GESTION DES TÂCHES
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Récupère le statut d'une tâche avec info sur la langue détectée"""
    
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    task = tasks_storage[task_id].copy()
    
    # Convertir les dates en string pour JSON
    if "created_at" in task:
        task["created_at"] = task["created_at"].isoformat()
    if "updated_at" in task:
        task["updated_at"] = task["updated_at"].isoformat()
    
    return task

@app.get("/api/tasks")
async def list_tasks():
    """Liste toutes les tâches avec info sur les langues détectées"""
    return {
        "tasks": [
            {
                "task_id": tid,
                "status": task["status"],
                "created_at": task["created_at"].isoformat(),
                "updated_at": task.get("updated_at", task["created_at"]).isoformat(),
                "pages_count": len(task.get("pages", [])),
                "detected_language": task.get("detected_language", "unknown")  # 🆕 Info langue
            }
            for tid, task in tasks_storage.items()
        ]
    }

# ═══════════════════════════════════════════════════════════════════════
# NOUVEAUX ENDPOINTS POUR LA DÉTECTION DE LANGUE
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/detect-language")
async def detect_language_endpoint(pages: List[str]):
    """🆕 Endpoint dédié pour détecter la langue d'une liste de pages"""
    try:
        if not pages:
            raise HTTPException(status_code=400, detail="Au moins une page est requise")
        
        # Import des fonctions de détection
        from wikimetron.metrics.pipeline import detect_language_from_pages, extract_clean_title_and_language
        
        detected_language = detect_language_from_pages(pages)
        
        # Analyse détaillée par page
        page_analysis = []
        for page in pages:
            clean_title, page_lang = extract_clean_title_and_language(page)
            page_analysis.append({
                "original": page,
                "clean_title": clean_title,
                "detected_language": page_lang,
                "is_url": page.startswith("http")
            })
        
        return {
            "detected_language": detected_language,
            "page_analysis": page_analysis,
            "summary": {
                "total_pages": len(pages),
                "urls_count": len([p for p in pages if p.startswith("http")]),
                "titles_count": len([p for p in pages if not p.startswith("http")])
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur détection langue: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la détection: {str(e)}")

@app.get("/api/supported-languages")
async def get_supported_languages():
    """🆕 Liste des langues Wikipedia supportées"""
    return {
        "supported_languages": [
            {"code": "fr", "name": "Français", "wikipedia": "fr.wikipedia.org"},
            {"code": "en", "name": "English", "wikipedia": "en.wikipedia.org"},
            {"code": "de", "name": "Deutsch", "wikipedia": "de.wikipedia.org"},
            {"code": "es", "name": "Español", "wikipedia": "es.wikipedia.org"},
            {"code": "it", "name": "Italiano", "wikipedia": "it.wikipedia.org"},
            {"code": "pt", "name": "Português", "wikipedia": "pt.wikipedia.org"},
            {"code": "ru", "name": "Русский", "wikipedia": "ru.wikipedia.org"},
            {"code": "ja", "name": "日本語", "wikipedia": "ja.wikipedia.org"},
            {"code": "zh", "name": "中文", "wikipedia": "zh.wikipedia.org"},
            {"code": "ar", "name": "العربية", "wikipedia": "ar.wikipedia.org"}
        ],
        "auto_detection": {
            "enabled": True,
            "fallback_language": "fr",
            "description": "Language is automatically detected from Wikipedia URLs. If no URLs provided or detection fails, fallback language is used."
        }
    }

# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS DE TEST ET DEBUG
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/test-pipeline")
async def test_pipeline():
    """Test rapide du pipeline avec détection automatique"""
    try:
        from wikimetron.metrics.pipeline import compute_scores_for_api
        
        # Test avec URLs mixtes pour tester la détection automatique
        test_pages = [
            "https://fr.wikipedia.org/wiki/France",
            "https://fr.wikipedia.org/wiki/Paris"
        ]
        
        results = compute_scores_for_api(test_pages, "2024-01-01", "2024-12-31")  # language=None
        
        return {
            "status": "success", 
            "results": results,
            "test_info": {
                "pages_tested": test_pages,
                "auto_detection": "enabled",
                "detected_language": results.get("summary", {}).get("language", "unknown")
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur test pipeline: {e}")
        return {
            "status": "error", 
            "error": str(e), 
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)