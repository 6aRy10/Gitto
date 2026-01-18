"""
FP&A Agent API

FastAPI endpoints for controlling the AI FP&A Analyst system.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from .orchestrator import get_orchestrator, FPAOrchestrator
from .decision_queue import DecisionPriority, DecisionStatus, DecisionCategory
from .audit_log import AuditAction
from .workflows import register_all_workflows

router = APIRouter(prefix="/fpa-analyst", tags=["FP&A AI Analyst"])


# =========================================================================
# REQUEST/RESPONSE MODELS
# =========================================================================

class WorkflowTriggerRequest(BaseModel):
    triggered_by: str = "api"
    user_id: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class QuestionRequest(BaseModel):
    question: str
    user_id: str
    context: Optional[Dict[str, Any]] = None


class QuestionResponse(BaseModel):
    question: str
    answer: str
    confidence: float
    sources: List[str]
    follow_up_questions: List[str]
    timestamp: str


class DecisionApprovalRequest(BaseModel):
    approved_by: str
    selected_option_ids: List[str]
    notes: Optional[str] = None


class DecisionDismissRequest(BaseModel):
    dismissed_by: str
    reason: Optional[str] = None


class DecisionResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    amount_at_stake: str
    options: List[Dict[str, Any]]
    recommended_option_ids: List[str]
    recommendation_reasoning: str
    created_at: str
    expires_at: Optional[str]


class WorkflowStatusResponse(BaseModel):
    status: str
    entity_id: int
    autonomous_mode: bool
    workflows: Dict[str, str]
    scheduled_tasks: Dict[str, Any]
    decision_queue_stats: Dict[str, Any]
    recent_runs: List[Dict[str, Any]]


class BriefingResponse(BaseModel):
    id: str
    entity_id: int
    briefing_date: str
    cash_position: Dict[str, Any]
    overnight_inflows: List[Dict[str, Any]]
    overnight_outflows: List[Dict[str, Any]]
    surprises: List[Dict[str, Any]]
    attention_items: List[Dict[str, Any]]
    executive_summary: str


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def get_fpa_orchestrator(
    db: Session = Depends(get_db),
    entity_id: int = Query(1, description="Entity ID"),
) -> FPAOrchestrator:
    """Get orchestrator for entity, registering workflows if needed"""
    orchestrator = get_orchestrator(db, entity_id)
    
    # Register workflows if not already done
    if not orchestrator._workflow_handlers:
        register_all_workflows(orchestrator)
    
    return orchestrator


# =========================================================================
# STATUS ENDPOINTS
# =========================================================================

@router.get("/status", response_model=WorkflowStatusResponse)
async def get_analyst_status(
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get overall FP&A analyst status"""
    return orchestrator.get_status()


@router.post("/start")
async def start_analyst(
    background_tasks: BackgroundTasks,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Start the autonomous FP&A analyst"""
    background_tasks.add_task(orchestrator.start)
    return {"message": "FP&A Analyst starting", "status": "starting"}


@router.post("/stop")
async def stop_analyst(
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Stop the autonomous FP&A analyst"""
    await orchestrator.stop()
    return {"message": "FP&A Analyst stopped", "status": "stopped"}


@router.post("/pause")
async def pause_analyst(
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Pause scheduled workflows (manual triggers still work)"""
    await orchestrator.pause()
    return {"message": "FP&A Analyst paused", "status": "paused"}


@router.post("/resume")
async def resume_analyst(
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Resume scheduled workflows"""
    await orchestrator.resume()
    return {"message": "FP&A Analyst resumed", "status": "running"}


# =========================================================================
# WORKFLOW ENDPOINTS
# =========================================================================

@router.post("/workflows/{workflow_name}/run")
async def run_workflow(
    workflow_name: str,
    request: WorkflowTriggerRequest,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Manually trigger a workflow"""
    try:
        result = await orchestrator.run_workflow(
            workflow_name,
            triggered_by=request.triggered_by,
            user_id=request.user_id,
            **request.params,
        )
        
        # Convert result to dict if it has to_dict method
        if hasattr(result, 'to_dict'):
            result = result.to_dict()
        
        return {
            "workflow": workflow_name,
            "status": "completed",
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_name}/latest")
async def get_workflow_latest(
    workflow_name: str,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get latest output from a workflow"""
    if workflow_name == "morning_briefing":
        briefing = orchestrator.get_latest_briefing()
        if briefing:
            return briefing.to_dict()
        raise HTTPException(status_code=404, detail="No briefing available")
    
    elif workflow_name == "weekly_meeting_prep":
        pack = orchestrator.get_latest_weekly_pack()
        if pack:
            return pack.to_dict()
        raise HTTPException(status_code=404, detail="No weekly pack available")
    
    elif workflow_name == "variance_report":
        report = orchestrator.get_latest_variance_report()
        if report:
            return report.to_dict()
        raise HTTPException(status_code=404, detail="No variance report available")
    
    raise HTTPException(status_code=404, detail=f"Unknown workflow: {workflow_name}")


# =========================================================================
# DECISION QUEUE ENDPOINTS
# =========================================================================

@router.get("/decisions")
async def get_pending_decisions(
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(50, le=100),
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get pending decisions"""
    # Parse filters
    priority_filter = DecisionPriority(priority) if priority else None
    category_filter = DecisionCategory(category) if category else None
    
    decisions = orchestrator.decision_queue.get_pending_decisions(
        priority=priority_filter,
        category=category_filter,
        limit=limit,
    )
    
    return {
        "decisions": [d.to_dict() for d in decisions],
        "total": len(decisions),
    }


@router.get("/decisions/{decision_id}")
async def get_decision(
    decision_id: str,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get a specific decision"""
    decision = orchestrator.decision_queue.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision.to_dict()


@router.post("/decisions/{decision_id}/approve")
async def approve_decision(
    decision_id: str,
    request: DecisionApprovalRequest,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Approve a decision with selected options"""
    try:
        decision = orchestrator.decision_queue.approve_decision(
            decision_id=decision_id,
            approved_by=request.approved_by,
            selected_option_ids=request.selected_option_ids,
            notes=request.notes,
        )
        
        # Log the approval
        orchestrator.audit_log.log_decision(
            action=AuditAction.DECISION_APPROVED,
            decision_id=decision_id,
            description=f"Decision approved by {request.approved_by}",
            user_id=request.approved_by,
            details={
                "selected_options": request.selected_option_ids,
                "notes": request.notes,
            },
        )
        
        return decision.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/decisions/{decision_id}/dismiss")
async def dismiss_decision(
    decision_id: str,
    request: DecisionDismissRequest,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Dismiss a decision"""
    try:
        decision = orchestrator.decision_queue.dismiss_decision(
            decision_id=decision_id,
            dismissed_by=request.dismissed_by,
            reason=request.reason,
        )
        
        orchestrator.audit_log.log_decision(
            action=AuditAction.DECISION_DISMISSED,
            decision_id=decision_id,
            description=f"Decision dismissed by {request.dismissed_by}",
            user_id=request.dismissed_by,
            details={"reason": request.reason},
        )
        
        return decision.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/decisions/stats")
async def get_decision_stats(
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get decision queue statistics"""
    return orchestrator.decision_queue.get_stats()


# =========================================================================
# QUESTION ANSWERING ENDPOINTS
# =========================================================================

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Ask the AI analyst a question"""
    result = await orchestrator.ask_question(
        question=request.question,
        user_id=request.user_id,
        context=request.context,
    )
    
    return QuestionResponse(
        question=result.get("question", request.question),
        answer=result.get("answer", ""),
        confidence=result.get("confidence", 0.5),
        sources=result.get("sources", []),
        follow_up_questions=result.get("follow_up_questions", []),
        timestamp=result.get("timestamp", datetime.utcnow().isoformat()),
    )


# =========================================================================
# INSIGHTS ENDPOINTS
# =========================================================================

@router.get("/insights")
async def get_recent_insights(
    limit: int = Query(10, le=50),
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get recent AI-generated insights"""
    # Get from audit log - insights are logged as various actions
    insights = []
    
    entries = orchestrator.audit_log.get_entries(limit=limit * 2)
    
    for entry in entries:
        if entry.action in [
            AuditAction.ANOMALY_DETECTED,
            AuditAction.FORECAST_DRIFT_DETECTED,
            AuditAction.ALERT_TRIGGERED,
            AuditAction.RECOMMENDATION_GENERATED,
        ]:
            insights.append({
                "type": entry.action.value,
                "timestamp": entry.timestamp.isoformat(),
                "description": entry.description,
                "severity": entry.severity.value,
                "details": entry.details,
            })
    
    return {"insights": insights[:limit]}


# =========================================================================
# MORNING BRIEFING ENDPOINTS
# =========================================================================

@router.get("/morning-briefing")
async def get_morning_briefing(
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get today's morning briefing (generates if needed)"""
    briefing = orchestrator.get_latest_briefing()
    
    # Check if briefing is from today
    if briefing and briefing.briefing_date == datetime.utcnow().date():
        return briefing.to_dict()
    
    # Generate new briefing
    briefing = await orchestrator.run_morning_briefing(triggered_by="api")
    
    if hasattr(briefing, 'to_dict'):
        return briefing.to_dict()
    return briefing


# =========================================================================
# WEEKLY PACK ENDPOINTS
# =========================================================================

@router.get("/weekly-pack")
async def get_weekly_pack(
    snapshot_id: Optional[int] = None,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get this week's meeting pack (generates if needed)"""
    pack = orchestrator.get_latest_weekly_pack()
    
    # Check if pack is from this week
    today = datetime.utcnow().date()
    week_start = today - datetime.timedelta(days=today.weekday())
    
    if pack and pack.pack_date >= week_start:
        return pack.to_dict()
    
    # Generate new pack
    pack = await orchestrator.run_weekly_meeting_prep(
        triggered_by="api",
        snapshot_id=snapshot_id,
    )
    
    if hasattr(pack, 'to_dict'):
        return pack.to_dict()
    return pack


# =========================================================================
# VARIANCE REPORT ENDPOINTS
# =========================================================================

@router.get("/variance-report")
async def get_variance_report(
    snapshot_id: int,
    compare_snapshot_id: int,
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get variance analysis between two snapshots"""
    from .workers.variance_worker import VarianceWorker
    
    worker = VarianceWorker(orchestrator.db, orchestrator.entity_id)
    report = worker.analyze_actual_vs_forecast(snapshot_id, compare_snapshot_id)
    
    return report.to_dict()


# =========================================================================
# AUDIT LOG ENDPOINTS
# =========================================================================

@router.get("/audit-log")
async def get_audit_log(
    action: Optional[str] = None,
    severity: Optional[str] = None,
    workflow_name: Optional[str] = None,
    limit: int = Query(100, le=500),
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get audit log entries"""
    action_filter = AuditAction(action) if action else None
    
    entries = orchestrator.audit_log.get_entries(
        action=action_filter,
        workflow_name=workflow_name,
        limit=limit,
    )
    
    return {
        "entries": [e.to_dict() for e in entries],
        "total": len(entries),
    }


@router.get("/audit-log/stats")
async def get_audit_stats(
    orchestrator: FPAOrchestrator = Depends(get_fpa_orchestrator),
):
    """Get audit log statistics"""
    return orchestrator.audit_log.get_stats()
