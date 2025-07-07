from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
import asyncio
from datetime import datetime
import logging
import traceback
import pandas as pd

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(
    title="Wikimetron API",
    description="Wikipedia Content Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS pour le développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8300", "http://127.0.0.1:8300"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles Pydantic
class AnalyzeRequest(BaseModel):
    pages: List[str]
    start_date: str
    end_date: str  
    language: str = "fr"

class PageviewsRequest(BaseModel):
    pages: List[str]
    start_date: str
    end_date: str
    language: str = "fr"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    estimated_time: Optional[int] = None

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
    """Lance l'analyse en arrière-plan et met à jour le statut"""
    try:
        logger.info(f"Début de l'analyse pour la tâche {task_id}")
        update_task_status(task_id, "running")
        
        # Import du pipeline - utiliser la version API wrapper
        from wikimetron.metrics.pipeline import compute_scores_for_api
        
        # Extraire les paramètres
        pages = request_data.get("pages", [])
        start_date = request_data.get("start_date")
        end_date = request_data.get("end_date")
        language = request_data.get("language", "fr")
        
        # Lancer l'analyse
        results = compute_scores_for_api(pages, start_date, end_date, language)
        
        # Mettre à jour avec les résultats
        update_task_status(task_id, "completed", results=results)
        logger.info(f"Analyse terminée avec succès pour la tâche {task_id}")
        
    except Exception as e:
        error_msg = f"Erreur lors de l'analyse: {str(e)}"
        logger.error(f"Erreur dans la tâche {task_id}: {error_msg}")
        logger.error(traceback.format_exc())
        update_task_status(task_id, "error", error=error_msg)

@app.get("/")
async def root():
    return {
        "message": "Wikimetron API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/analyze", response_model=TaskResponse)
async def analyze_pages(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Lance une analyse Wikipedia"""
    
    # Validation
    if not request.pages:
        raise HTTPException(status_code=400, detail="Au moins une page est requise")
    
    if len(request.pages) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 pages par analyse")
    
    # Créer une tâche
    task_id = str(uuid.uuid4())
    tasks_storage[task_id] = {
        "status": "queued",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "pages": request.pages,
        "request": request.dict()
    }
    
    # Lancer l'analyse en arrière-plan
    background_tasks.add_task(run_analysis_background, task_id, request.dict())
    
    logger.info(f"Tâche {task_id} créée pour {len(request.pages)} pages")
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        estimated_time=len(request.pages) * 10
    )

# ✨ NOUVEAU : Endpoint pour récupérer les données pageviews temporelles
@app.post("/api/pageviews")
async def get_pageviews_timeseries(request: PageviewsRequest):
    """Récupère les données de pageviews quotidiennes pour le graphique"""
    
    try:
        logger.info(f"Récupération pageviews pour {len(request.pages)} pages")
        
        # Validation
        if not request.pages:
            raise HTTPException(status_code=400, detail="Au moins une page est requise")
        
        if len(request.pages) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 pages pour les graphiques")
        
        # Import de la fonction pageviews
        from wikimetron.metrics.pageviews import get_pageviews_timeseries
        
        # Récupérer les données temporelles
        timeseries_data = get_pageviews_timeseries(
            request.pages, 
            request.start_date, 
            request.end_date, 
            request.language
        )
        
        # Convertir les données pour le graphique
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
                # Convertir la date string en index datetime pour la recherche
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
        
        # Préparer les métadonnées
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
                "language": request.language,
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

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Récupère le statut d'une tâche"""
    
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
    """Liste toutes les tâches"""
    return {
        "tasks": [
            {
                "task_id": tid,
                "status": task["status"],
                "created_at": task["created_at"].isoformat(),
                "updated_at": task.get("updated_at", task["created_at"]).isoformat(),
                "pages_count": len(task.get("pages", []))
            }
            for tid, task in tasks_storage.items()
        ]
    }

# Endpoint de test rapide pour debug
@app.post("/api/test-pipeline")
async def test_pipeline():
    """Test rapide du pipeline sans tâche"""
    try:
        from wikimetron.metrics.pipeline import compute_scores_for_api
        
        # Test avec une page simple
        results = compute_scores_for_api(["France"], "2024-01-01", "2024-12-31", "fr")
        return {"status": "success", "results": results}
        
    except Exception as e:
        logger.error(f"Erreur test pipeline: {e}")
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)