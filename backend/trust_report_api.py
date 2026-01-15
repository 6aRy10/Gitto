"""
Trust Report API

Endpoints for trust reports and snapshot locking.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime

from database import get_db
from trust_report_service import TrustReportService, LockGateThresholds
from trust_report_models import TrustReport, TrustMetric, LockGateOverrideLog


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/snapshots",
    tags=["trust"]
)


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class TrustMetricResponse(BaseModel):
    id: int
    key: str
    description: Optional[str] = None
    value: float
    unit: str
    exposure_amount_base: float = 0.0
    trend_delta: Optional[float] = None
    trend_direction: Optional[str] = None
    evidence_refs: Optional[List[Dict[str, Any]]] = None
    breakdown: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class GateFailureResponse(BaseModel):
    gate: str
    description: Optional[str] = None
    threshold: float
    actual: float
    exposure: float
    status: str


class TrustReportResponse(BaseModel):
    id: int
    snapshot_id: int
    created_at: datetime
    trust_score: float
    lock_eligible: bool
    gate_failures: List[GateFailureResponse] = []
    metrics_summary: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    metrics: List[TrustMetricResponse] = []
    
    class Config:
        from_attributes = True


class LockRequest(BaseModel):
    """Request to lock a snapshot."""
    user_id: str = Field(..., description="User ID attempting the lock")
    user_email: Optional[str] = Field(None, description="User email")
    user_role: Optional[str] = Field(None, description="User role (e.g., CFO)")
    override_acknowledgment: Optional[str] = Field(
        None, 
        description="Required if gates failed. Must be >= 20 chars."
    )
    override_reason: Optional[str] = Field(
        None,
        description="Additional context for why override was necessary"
    )
    
    @validator("override_acknowledgment")
    def validate_acknowledgment(cls, v):
        if v is not None and len(v) < 20:
            raise ValueError("Override acknowledgment must be at least 20 characters")
        return v


class LockResponse(BaseModel):
    success: bool
    message: str
    snapshot_id: int
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    was_override: bool = False
    overridden_gates: Optional[List[str]] = None
    trust_report: Optional[TrustReportResponse] = None


class OverrideLogResponse(BaseModel):
    id: int
    snapshot_id: int
    created_at: datetime
    user_id: str
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    acknowledgment_text: str
    failed_gates: List[Dict[str, Any]]
    override_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{snapshot_id}/trust", response_model=TrustReportResponse)
async def get_trust_report(
    snapshot_id: int,
    regenerate: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get the trust report for a snapshot.
    
    If regenerate=true, generates a fresh report.
    Otherwise, returns the latest cached report or generates one if none exists.
    """
    service = TrustReportService(db)
    
    if regenerate:
        report = service.generate_trust_report(snapshot_id)
    else:
        report = service.get_latest_report(snapshot_id)
        if not report:
            report = service.generate_trust_report(snapshot_id)
    
    # Load metrics
    metrics = db.query(TrustMetric).filter(
        TrustMetric.report_id == report.id
    ).all()
    
    # Parse gate failures
    gate_failures = []
    if report.gate_failures_json:
        for gf in report.gate_failures_json:
            gate_failures.append(GateFailureResponse(
                gate=gf.get("gate", ""),
                description=gf.get("description"),
                threshold=gf.get("threshold", 0),
                actual=gf.get("actual", 0),
                exposure=gf.get("exposure", 0),
                status=gf.get("status", "failed")
            ))
    
    return TrustReportResponse(
        id=report.id,
        snapshot_id=report.snapshot_id,
        created_at=report.created_at,
        trust_score=report.trust_score,
        lock_eligible=report.lock_eligible,
        gate_failures=gate_failures,
        metrics_summary=report.metrics_json,
        config=report.config_json,
        metrics=[
            TrustMetricResponse(
                id=m.id,
                key=m.key,
                description=m.description,
                value=m.value,
                unit=m.unit,
                exposure_amount_base=m.exposure_amount_base,
                trend_delta=m.trend_delta,
                trend_direction=m.trend_direction,
                evidence_refs=m.evidence_refs_json,
                breakdown=m.breakdown_json
            )
            for m in metrics
        ]
    )


@router.post("/{snapshot_id}/lock", response_model=LockResponse)
async def lock_snapshot(
    snapshot_id: int,
    request: LockRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Attempt to lock a snapshot.
    
    Requirements:
    - If lock_eligible is true: Lock proceeds
    - If lock_eligible is false: Requires override_acknowledgment >= 20 chars
    
    Override is logged to audit trail with:
    - User info
    - Acknowledgment text
    - Failed gates
    - Timestamp
    """
    service = TrustReportService(db)
    
    # Get client IP for audit
    ip_address = req.client.host if req.client else None
    
    try:
        success, message, trust_report = service.attempt_lock(
            snapshot_id=snapshot_id,
            user_id=request.user_id,
            user_email=request.user_email,
            user_role=request.user_role,
            override_acknowledgment=request.override_acknowledgment,
            override_reason=request.override_reason,
            ip_address=ip_address
        )
        
        # Build response
        response = LockResponse(
            success=success,
            message=message,
            snapshot_id=snapshot_id,
            was_override=bool(request.override_acknowledgment and success)
        )
        
        if success:
            from models import Snapshot
            snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
            if snapshot:
                response.locked_at = snapshot.locked_at
                response.locked_by = snapshot.locked_by
        
        if trust_report:
            # Get gate failures that were overridden
            if request.override_acknowledgment and success and trust_report.gate_failures_json:
                response.overridden_gates = [g["gate"] for g in trust_report.gate_failures_json]
            
            # Include full trust report
            metrics = db.query(TrustMetric).filter(
                TrustMetric.report_id == trust_report.id
            ).all()
            
            gate_failures = []
            if trust_report.gate_failures_json:
                for gf in trust_report.gate_failures_json:
                    gate_failures.append(GateFailureResponse(
                        gate=gf.get("gate", ""),
                        description=gf.get("description"),
                        threshold=gf.get("threshold", 0),
                        actual=gf.get("actual", 0),
                        exposure=gf.get("exposure", 0),
                        status=gf.get("status", "failed")
                    ))
            
            response.trust_report = TrustReportResponse(
                id=trust_report.id,
                snapshot_id=trust_report.snapshot_id,
                created_at=trust_report.created_at,
                trust_score=trust_report.trust_score,
                lock_eligible=trust_report.lock_eligible,
                gate_failures=gate_failures,
                metrics_summary=trust_report.metrics_json,
                config=trust_report.config_json,
                metrics=[
                    TrustMetricResponse(
                        id=m.id,
                        key=m.key,
                        description=m.description,
                        value=m.value,
                        unit=m.unit,
                        exposure_amount_base=m.exposure_amount_base,
                        trend_delta=m.trend_delta,
                        trend_direction=m.trend_direction,
                        evidence_refs=m.evidence_refs_json,
                        breakdown=m.breakdown_json
                    )
                    for m in metrics
                ]
            )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error locking snapshot: {str(e)}")


@router.get("/{snapshot_id}/trust/history", response_model=List[TrustReportResponse])
async def get_trust_history(
    snapshot_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get history of trust reports for a snapshot.
    """
    reports = db.query(TrustReport).filter(
        TrustReport.snapshot_id == snapshot_id
    ).order_by(TrustReport.created_at.desc()).limit(limit).all()
    
    response = []
    for report in reports:
        metrics = db.query(TrustMetric).filter(
            TrustMetric.report_id == report.id
        ).all()
        
        gate_failures = []
        if report.gate_failures_json:
            for gf in report.gate_failures_json:
                gate_failures.append(GateFailureResponse(
                    gate=gf.get("gate", ""),
                    description=gf.get("description"),
                    threshold=gf.get("threshold", 0),
                    actual=gf.get("actual", 0),
                    exposure=gf.get("exposure", 0),
                    status=gf.get("status", "failed")
                ))
        
        response.append(TrustReportResponse(
            id=report.id,
            snapshot_id=report.snapshot_id,
            created_at=report.created_at,
            trust_score=report.trust_score,
            lock_eligible=report.lock_eligible,
            gate_failures=gate_failures,
            metrics_summary=report.metrics_json,
            config=report.config_json,
            metrics=[
                TrustMetricResponse(
                    id=m.id,
                    key=m.key,
                    description=m.description,
                    value=m.value,
                    unit=m.unit,
                    exposure_amount_base=m.exposure_amount_base,
                    trend_delta=m.trend_delta,
                    trend_direction=m.trend_direction,
                    evidence_refs=m.evidence_refs_json,
                    breakdown=m.breakdown_json
                )
                for m in metrics
            ]
        ))
    
    return response


@router.get("/{snapshot_id}/overrides", response_model=List[OverrideLogResponse])
async def get_override_logs(
    snapshot_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all CFO override logs for a snapshot.
    """
    logs = db.query(LockGateOverrideLog).filter(
        LockGateOverrideLog.snapshot_id == snapshot_id
    ).order_by(LockGateOverrideLog.created_at.desc()).all()
    
    return [
        OverrideLogResponse(
            id=log.id,
            snapshot_id=log.snapshot_id,
            created_at=log.created_at,
            user_id=log.user_id,
            user_email=log.user_email,
            user_role=log.user_role,
            acknowledgment_text=log.acknowledgment_text,
            failed_gates=log.failed_gates_json,
            override_reason=log.override_reason
        )
        for log in logs
    ]


@router.get("/{snapshot_id}/trust/metric/{key}")
async def get_trust_metric_details(
    snapshot_id: int,
    key: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific trust metric.
    
    Returns full evidence references for UI drilldown.
    """
    service = TrustReportService(db)
    report = service.get_latest_report(snapshot_id)
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No trust report found for snapshot {snapshot_id}"
        )
    
    metric = db.query(TrustMetric).filter(
        TrustMetric.report_id == report.id,
        TrustMetric.key == key
    ).first()
    
    if not metric:
        raise HTTPException(
            status_code=404,
            detail=f"Metric '{key}' not found in trust report"
        )
    
    return {
        "id": metric.id,
        "key": metric.key,
        "description": metric.description,
        "value": metric.value,
        "unit": metric.unit,
        "exposure_amount_base": metric.exposure_amount_base,
        "trend_delta": metric.trend_delta,
        "trend_direction": metric.trend_direction,
        "evidence_refs": metric.evidence_refs_json,
        "breakdown": metric.breakdown_json,
        "report_id": report.id,
        "report_created_at": report.created_at.isoformat()
    }
