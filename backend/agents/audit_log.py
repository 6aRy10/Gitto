"""
Audit Log

Comprehensive logging of all AI agent actions for compliance and debugging.
Every autonomous action is recorded with full context.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Types of auditable actions"""
    # Workflow actions
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    # Briefing actions
    BRIEFING_GENERATED = "briefing_generated"
    WEEKLY_PACK_GENERATED = "weekly_pack_generated"
    
    # Decision actions
    DECISION_CREATED = "decision_created"
    DECISION_AUTO_APPROVED = "decision_auto_approved"
    DECISION_APPROVED = "decision_approved"
    DECISION_DISMISSED = "decision_dismissed"
    DECISION_EXPIRED = "decision_expired"
    DECISION_EXECUTED = "decision_executed"
    DECISION_EXECUTION_FAILED = "decision_execution_failed"
    
    # Analysis actions
    VARIANCE_ANALYZED = "variance_analyzed"
    ANOMALY_DETECTED = "anomaly_detected"
    FORECAST_GENERATED = "forecast_generated"
    FORECAST_DRIFT_DETECTED = "forecast_drift_detected"
    
    # Reconciliation actions
    RECONCILIATION_RUN = "reconciliation_run"
    MATCHES_APPLIED = "matches_applied"
    ITEMS_ESCALATED = "items_escalated"
    
    # LLM actions
    LLM_QUERY = "llm_query"
    LLM_RESPONSE = "llm_response"
    NARRATIVE_GENERATED = "narrative_generated"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    
    # Question answering
    QUESTION_ASKED = "question_asked"
    QUESTION_ANSWERED = "question_answered"
    
    # Monitoring
    ALERT_TRIGGERED = "alert_triggered"
    THRESHOLD_BREACHED = "threshold_breached"
    
    # Period close
    PERIOD_CLOSE_INITIATED = "period_close_initiated"
    PERIOD_LOCKED = "period_locked"


class AuditSeverity(str, Enum):
    """Severity levels for audit entries"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """
    A single audit log entry.
    
    Every AI action creates an audit entry with full context.
    """
    id: str
    timestamp: datetime
    action: AuditAction
    severity: AuditSeverity
    
    # Context
    entity_id: int
    snapshot_id: Optional[int]
    workflow_name: Optional[str]
    agent_name: Optional[str]
    
    # Details
    description: str
    details: Dict[str, Any]
    
    # Traceability
    triggered_by: str  # "schedule", "event", "user", "system"
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None  # Link related entries
    
    # Financial impact
    amount_involved: Optional[Decimal] = None
    currency: Optional[str] = None
    
    # Outcomes
    success: bool = True
    error_message: Optional[str] = None
    
    # Timing
    duration_ms: Optional[int] = None
    
    @classmethod
    def create(
        cls,
        action: AuditAction,
        entity_id: int,
        description: str,
        details: Dict[str, Any] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        snapshot_id: Optional[int] = None,
        workflow_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        triggered_by: str = "system",
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        amount_involved: Optional[Decimal] = None,
        currency: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> 'AuditEntry':
        return cls(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            action=action,
            severity=severity,
            entity_id=entity_id,
            snapshot_id=snapshot_id,
            workflow_name=workflow_name,
            agent_name=agent_name,
            description=description,
            details=details or {},
            triggered_by=triggered_by,
            user_id=user_id,
            correlation_id=correlation_id,
            amount_involved=amount_involved,
            currency=currency,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "severity": self.severity.value,
            "entity_id": self.entity_id,
            "snapshot_id": self.snapshot_id,
            "workflow_name": self.workflow_name,
            "agent_name": self.agent_name,
            "description": self.description,
            "details": self.details,
            "triggered_by": self.triggered_by,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "amount_involved": str(self.amount_involved) if self.amount_involved else None,
            "currency": self.currency,
            "success": self.success,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
        }


class AuditLog:
    """
    Manages audit logging for the FP&A Analyst system.
    
    All autonomous actions are logged for compliance and debugging.
    """
    
    def __init__(self, db: Session, entity_id: int):
        self.db = db
        self.entity_id = entity_id
        self._entries: List[AuditEntry] = []  # In-memory buffer
        self._current_correlation_id: Optional[str] = None
    
    def start_correlation(self, workflow_name: str) -> str:
        """Start a new correlation context for related entries"""
        self._current_correlation_id = str(uuid.uuid4())
        return self._current_correlation_id
    
    def end_correlation(self):
        """End the current correlation context"""
        self._current_correlation_id = None
    
    def log(
        self,
        action: AuditAction,
        description: str,
        details: Dict[str, Any] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        snapshot_id: Optional[int] = None,
        workflow_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        triggered_by: str = "system",
        user_id: Optional[str] = None,
        amount_involved: Optional[Decimal] = None,
        currency: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> AuditEntry:
        """Log an action"""
        entry = AuditEntry.create(
            action=action,
            entity_id=self.entity_id,
            description=description,
            details=details,
            severity=severity,
            snapshot_id=snapshot_id,
            workflow_name=workflow_name,
            agent_name=agent_name,
            triggered_by=triggered_by,
            user_id=user_id,
            correlation_id=self._current_correlation_id,
            amount_involved=amount_involved,
            currency=currency,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        
        self._entries.append(entry)
        self._persist_entry(entry)
        
        # Also log to standard logger
        log_func = {
            AuditSeverity.DEBUG: logger.debug,
            AuditSeverity.INFO: logger.info,
            AuditSeverity.WARNING: logger.warning,
            AuditSeverity.ERROR: logger.error,
            AuditSeverity.CRITICAL: logger.critical,
        }.get(severity, logger.info)
        
        log_func(f"[{action.value}] {description}")
        
        return entry
    
    def log_workflow_start(
        self,
        workflow_name: str,
        triggered_by: str = "schedule",
        user_id: Optional[str] = None,
    ) -> str:
        """Log workflow start and return correlation ID"""
        correlation_id = self.start_correlation(workflow_name)
        
        self.log(
            action=AuditAction.WORKFLOW_STARTED,
            description=f"Workflow '{workflow_name}' started",
            workflow_name=workflow_name,
            triggered_by=triggered_by,
            user_id=user_id,
        )
        
        return correlation_id
    
    def log_workflow_complete(
        self,
        workflow_name: str,
        duration_ms: int,
        details: Dict[str, Any] = None,
    ):
        """Log workflow completion"""
        self.log(
            action=AuditAction.WORKFLOW_COMPLETED,
            description=f"Workflow '{workflow_name}' completed in {duration_ms}ms",
            workflow_name=workflow_name,
            details=details,
            duration_ms=duration_ms,
        )
        self.end_correlation()
    
    def log_workflow_failed(
        self,
        workflow_name: str,
        error: str,
        duration_ms: Optional[int] = None,
    ):
        """Log workflow failure"""
        self.log(
            action=AuditAction.WORKFLOW_FAILED,
            description=f"Workflow '{workflow_name}' failed: {error}",
            workflow_name=workflow_name,
            severity=AuditSeverity.ERROR,
            success=False,
            error_message=error,
            duration_ms=duration_ms,
        )
        self.end_correlation()
    
    def log_decision(
        self,
        action: AuditAction,
        decision_id: str,
        description: str,
        amount: Optional[Decimal] = None,
        user_id: Optional[str] = None,
        details: Dict[str, Any] = None,
    ):
        """Log a decision-related action"""
        self.log(
            action=action,
            description=description,
            details={
                "decision_id": decision_id,
                **(details or {}),
            },
            user_id=user_id,
            amount_involved=amount,
        )
    
    def log_llm_query(
        self,
        prompt_type: str,
        token_count: int,
        model: str,
        details: Dict[str, Any] = None,
    ):
        """Log an LLM query (for cost tracking)"""
        self.log(
            action=AuditAction.LLM_QUERY,
            description=f"LLM query: {prompt_type} ({token_count} tokens)",
            details={
                "prompt_type": prompt_type,
                "token_count": token_count,
                "model": model,
                **(details or {}),
            },
            severity=AuditSeverity.DEBUG,
        )
    
    def get_entries(
        self,
        action: Optional[AuditAction] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        workflow_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Query audit entries"""
        entries = self._entries
        
        if action:
            entries = [e for e in entries if e.action == action]
        
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        
        if until:
            entries = [e for e in entries if e.timestamp <= until]
        
        if severity:
            entries = [e for e in entries if e.severity == severity]
        
        if workflow_name:
            entries = [e for e in entries if e.workflow_name == workflow_name]
        
        if correlation_id:
            entries = [e for e in entries if e.correlation_id == correlation_id]
        
        # Sort by timestamp descending
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        return entries[:limit]
    
    def get_stats(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get audit statistics"""
        entries = self._entries
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        
        return {
            "total_entries": len(entries),
            "by_action": {
                action.value: len([e for e in entries if e.action == action])
                for action in AuditAction
                if any(e.action == action for e in entries)
            },
            "by_severity": {
                sev.value: len([e for e in entries if e.severity == sev])
                for sev in AuditSeverity
            },
            "errors": len([e for e in entries if not e.success]),
            "total_llm_tokens": sum(
                e.details.get("token_count", 0)
                for e in entries
                if e.action == AuditAction.LLM_QUERY
            ),
        }
    
    def _persist_entry(self, entry: AuditEntry):
        """Persist entry to database (placeholder)"""
        # TODO: Implement actual database persistence
        pass
    
    def _load_entries(self, limit: int = 1000):
        """Load entries from database (placeholder)"""
        # TODO: Implement actual database loading
        pass
