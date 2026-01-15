"""
Invariant Engine API

Expose endpoints for running and retrieving invariant checks.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from invariant_engine import InvariantEngine
from invariant_models import InvariantRun, InvariantResult, RunStatus


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/snapshots",
    tags=["invariants"]
)


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantResultResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    severity: str
    details: Optional[Dict[str, Any]] = None
    proof_string: Optional[str] = None
    evidence_refs: Optional[List[Dict[str, Any]]] = None
    exposure_amount: float = 0.0
    exposure_currency: str = "EUR"
    
    class Config:
        from_attributes = True


class InvariantRunResponse(BaseModel):
    id: int
    snapshot_id: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    summary: Optional[Dict[str, Any]] = None
    triggered_by: Optional[str] = None
    results: List[InvariantResultResponse] = []
    
    class Config:
        from_attributes = True


class InvariantRunStartResponse(BaseModel):
    run_id: int
    status: str
    message: str


class InvariantSummaryResponse(BaseModel):
    snapshot_id: int
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    total_runs: int
    total_passed: int
    total_failed: int
    critical_failures: int
    warning_count: int


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{snapshot_id}/invariants/run", response_model=InvariantRunResponse)
async def run_invariants(
    snapshot_id: int,
    triggered_by: str = "api",
    db: Session = Depends(get_db)
):
    """
    Run all invariants on a snapshot.
    
    Returns the complete run results including all invariant checks.
    """
    try:
        engine = InvariantEngine(db)
        run = engine.run_all_invariants(snapshot_id, triggered_by=triggered_by)
        
        # Load results
        results = db.query(InvariantResult).filter(
            InvariantResult.run_id == run.id
        ).all()
        
        return InvariantRunResponse(
            id=run.id,
            snapshot_id=run.snapshot_id,
            created_at=run.created_at,
            completed_at=run.completed_at,
            status=run.status,
            summary=run.summary_json,
            triggered_by=run.triggered_by,
            results=[
                InvariantResultResponse(
                    id=r.id,
                    name=r.name,
                    description=r.description,
                    status=r.status,
                    severity=r.severity,
                    details=r.details_json,
                    proof_string=r.proof_string,
                    evidence_refs=r.evidence_refs_json,
                    exposure_amount=r.exposure_amount,
                    exposure_currency=r.exposure_currency
                )
                for r in results
            ]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running invariants: {str(e)}")


@router.get("/{snapshot_id}/invariants/latest", response_model=InvariantRunResponse)
async def get_latest_invariants(
    snapshot_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the latest invariant run for a snapshot.
    """
    engine = InvariantEngine(db)
    run = engine.get_latest_run(snapshot_id)
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"No invariant runs found for snapshot {snapshot_id}"
        )
    
    # Load results
    results = db.query(InvariantResult).filter(
        InvariantResult.run_id == run.id
    ).all()
    
    return InvariantRunResponse(
        id=run.id,
        snapshot_id=run.snapshot_id,
        created_at=run.created_at,
        completed_at=run.completed_at,
        status=run.status,
        summary=run.summary_json,
        triggered_by=run.triggered_by,
        results=[
            InvariantResultResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                status=r.status,
                severity=r.severity,
                details=r.details_json,
                proof_string=r.proof_string,
                evidence_refs=r.evidence_refs_json,
                exposure_amount=r.exposure_amount,
                exposure_currency=r.exposure_currency
            )
            for r in results
        ]
    )


@router.get("/{snapshot_id}/invariants/history", response_model=List[InvariantRunResponse])
async def get_invariant_history(
    snapshot_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get the history of invariant runs for a snapshot.
    """
    runs = db.query(InvariantRun).filter(
        InvariantRun.snapshot_id == snapshot_id
    ).order_by(InvariantRun.created_at.desc()).limit(limit).all()
    
    response = []
    for run in runs:
        results = db.query(InvariantResult).filter(
            InvariantResult.run_id == run.id
        ).all()
        
        response.append(InvariantRunResponse(
            id=run.id,
            snapshot_id=run.snapshot_id,
            created_at=run.created_at,
            completed_at=run.completed_at,
            status=run.status,
            summary=run.summary_json,
            triggered_by=run.triggered_by,
            results=[
                InvariantResultResponse(
                    id=r.id,
                    name=r.name,
                    description=r.description,
                    status=r.status,
                    severity=r.severity,
                    details=r.details_json,
                    proof_string=r.proof_string,
                    evidence_refs=r.evidence_refs_json,
                    exposure_amount=r.exposure_amount,
                    exposure_currency=r.exposure_currency
                )
                for r in results
            ]
        ))
    
    return response


@router.get("/{snapshot_id}/invariants/summary", response_model=InvariantSummaryResponse)
async def get_invariant_summary(
    snapshot_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a summary of invariant runs for a snapshot.
    """
    from sqlalchemy import func
    
    # Count total runs
    total_runs = db.query(func.count(InvariantRun.id)).filter(
        InvariantRun.snapshot_id == snapshot_id
    ).scalar() or 0
    
    # Get latest run
    latest_run = db.query(InvariantRun).filter(
        InvariantRun.snapshot_id == snapshot_id
    ).order_by(InvariantRun.created_at.desc()).first()
    
    # Aggregate statistics
    passed = 0
    failed = 0
    critical = 0
    warnings = 0
    
    if latest_run and latest_run.summary_json:
        passed = latest_run.summary_json.get("passed", 0)
        failed = latest_run.summary_json.get("failed", 0)
        critical = latest_run.summary_json.get("critical_failures", 0)
        warnings = latest_run.summary_json.get("warnings", 0)
    
    return InvariantSummaryResponse(
        snapshot_id=snapshot_id,
        last_run_at=latest_run.created_at if latest_run else None,
        last_run_status=latest_run.status if latest_run else None,
        total_runs=total_runs,
        total_passed=passed,
        total_failed=failed,
        critical_failures=critical,
        warning_count=warnings
    )


@router.get("/{snapshot_id}/invariants/{run_id}/result/{name}")
async def get_invariant_result_by_name(
    snapshot_id: int,
    run_id: int,
    name: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific invariant result by name.
    """
    result = db.query(InvariantResult).filter(
        InvariantResult.run_id == run_id,
        InvariantResult.name == name
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Invariant result '{name}' not found in run {run_id}"
        )
    
    return InvariantResultResponse(
        id=result.id,
        name=result.name,
        description=result.description,
        status=result.status,
        severity=result.severity,
        details=result.details_json,
        proof_string=result.proof_string,
        evidence_refs=result.evidence_refs_json,
        exposure_amount=result.exposure_amount,
        exposure_currency=result.exposure_currency
    )
