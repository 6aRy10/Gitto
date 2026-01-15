"""
Async Operations Service
Handles long-running operations: upload parsing, reconciliation, forecast computation.
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
import models
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading


# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)


class AsyncTask:
    """Represents an async task"""
    def __init__(self, task_id: str, task_type: str, status: str = "pending"):
        self.task_id = task_id
        self.task_type = task_type
        self.status = status
        self.created_at = datetime.utcnow()
        self.completed_at = None
        self.result = None
        self.error = None


# In-memory task store (in production, use Redis or database)
_task_store = {}
_task_lock = threading.Lock()


def create_async_task(task_type: str) -> str:
    """Create a new async task and return task ID"""
    import uuid
    task_id = str(uuid.uuid4())
    
    with _task_lock:
        _task_store[task_id] = AsyncTask(task_id, task_type, "pending")
    
    return task_id


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get status of an async task"""
    with _task_lock:
        task = _task_store.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task_id,
            "task_type": task.task_type,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "error": task.error
        }


def update_task_status(task_id: str, status: str, result: Any = None, error: str = None):
    """Update task status"""
    with _task_lock:
        task = _task_store.get(task_id)
        if task:
            task.status = status
            task.completed_at = datetime.utcnow() if status in ["completed", "failed"] else None
            task.result = result
            task.error = error


def run_async_upload_parsing(db: Session, file_content: bytes, entity_id: int, mapping_config: dict = None):
    """Run upload parsing asynchronously"""
    task_id = create_async_task("upload_parsing")
    
    def _parse():
        try:
            from utils import parse_excel_to_df
            import json
            
            df, health = parse_excel_to_df(file_content, mapping_config)
            update_task_status(task_id, "completed", {
                "rows": len(df),
                "health": health,
                "columns": list(df.columns)
            })
        except Exception as e:
            update_task_status(task_id, "failed", error=str(e))
    
    executor.submit(_parse)
    return task_id


def run_async_reconciliation(db: Session, entity_id: int):
    """Run reconciliation asynchronously"""
    task_id = create_async_task("reconciliation")
    
    def _reconcile():
        try:
            # Use new reconciliation service V2 by default
            from reconciliation_service_v2 import ReconciliationServiceV2
            service = ReconciliationServiceV2(db)
            results = service.reconcile_entity(entity_id)
            
            # Also detect intercompany washes
            from bank_service import detect_intercompany_washes
            washes = detect_intercompany_washes(db, entity_id)
            
            update_task_status(task_id, "completed", {
                "deterministic": results.get("deterministic", 0),
                "rule_based": results.get("rule_based", 0),
                "suggested": results.get("suggested", 0),
                "manual": results.get("manual", 0),
                "many_to_many": results.get("many_to_many", 0),
                "washes": len(washes) if washes else 0
            })
        except Exception as e:
            update_task_status(task_id, "failed", error=str(e))
    
    executor.submit(_reconcile)
    return task_id


def run_async_forecast(db: Session, snapshot_id: int):
    """Run forecast computation asynchronously"""
    task_id = create_async_task("forecast")
    
    def _forecast():
        try:
            from utils import run_forecast_model
            
            run_forecast_model(db, snapshot_id)
            
            # Get forecast summary
            from utils import get_forecast_aggregation
            forecast = get_forecast_aggregation(db, snapshot_id, group_by="week")
            
            update_task_status(task_id, "completed", {
                "snapshot_id": snapshot_id,
                "weeks_forecasted": len(forecast),
                "total_forecast": sum(w.get("base", 0) for w in forecast)
            })
        except Exception as e:
            update_task_status(task_id, "failed", error=str(e))
    
    executor.submit(_forecast)
    return task_id




