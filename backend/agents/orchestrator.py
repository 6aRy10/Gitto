"""
FP&A Orchestrator

Main coordinator for all FP&A workflows. Manages scheduling, event handling,
and coordination between workers and reasoning engines.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import os

from sqlalchemy.orm import Session

from .decision_queue import DecisionQueue, Decision
from .audit_log import AuditLog, AuditAction, AuditSeverity
from .models.briefings import MorningBriefing, WeeklyPack
from .models.variance import VarianceReport

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Status of a workflow"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"


class OrchestratorStatus(str, Enum):
    """Overall orchestrator status"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class WorkflowRun:
    """Record of a workflow execution"""
    workflow_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: WorkflowStatus
    triggered_by: str
    correlation_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ScheduledTask:
    """A scheduled workflow task"""
    workflow_name: str
    cron_expression: str  # e.g., "0 7 * * *" for 7am daily
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class FPAOrchestrator:
    """
    Coordinates FP&A workflows based on schedule and events.
    
    Workflows:
    - Morning Briefing (daily 7am)
    - Weekly Meeting Prep (Monday 6am)
    - Month-End Close (last business day)
    - Continuous Monitoring (every 15 min)
    - Question Answering (on-demand)
    """
    
    def __init__(
        self,
        db: Session,
        entity_id: int,
        autonomous_mode: bool = True,
    ):
        self.db = db
        self.entity_id = entity_id
        self.autonomous_mode = autonomous_mode
        
        # Core components
        self.decision_queue = DecisionQueue(db, entity_id)
        self.audit_log = AuditLog(db, entity_id)
        
        # State
        self.status = OrchestratorStatus.STOPPED
        self._workflow_status: Dict[str, WorkflowStatus] = {}
        self._workflow_runs: List[WorkflowRun] = []
        
        # Scheduled tasks
        self._scheduled_tasks: Dict[str, ScheduledTask] = {
            "morning_briefing": ScheduledTask(
                workflow_name="morning_briefing",
                cron_expression=os.getenv("FPA_MORNING_BRIEFING_SCHEDULE", "0 7 * * *"),
            ),
            "weekly_meeting_prep": ScheduledTask(
                workflow_name="weekly_meeting_prep",
                cron_expression=os.getenv("FPA_WEEKLY_MEETING_PREP_SCHEDULE", "0 6 * * 1"),
            ),
            "continuous_monitoring": ScheduledTask(
                workflow_name="continuous_monitoring",
                cron_expression="*/15 * * * *",  # Every 15 minutes
            ),
        }
        
        # Workflow handlers (will be set by workflow modules)
        self._workflow_handlers: Dict[str, Callable] = {}
        
        # Latest outputs
        self._latest_briefing: Optional[MorningBriefing] = None
        self._latest_weekly_pack: Optional[WeeklyPack] = None
        self._latest_variance_report: Optional[VarianceReport] = None
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    def register_workflow(self, name: str, handler: Callable):
        """Register a workflow handler"""
        self._workflow_handlers[name] = handler
        self._workflow_status[name] = WorkflowStatus.IDLE
        logger.info(f"Registered workflow: {name}")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    async def start(self):
        """Start the orchestrator"""
        if self.status == OrchestratorStatus.RUNNING:
            logger.warning("Orchestrator already running")
            return
        
        self.status = OrchestratorStatus.RUNNING
        self.audit_log.log(
            action=AuditAction.WORKFLOW_STARTED,
            description="FP&A Orchestrator started",
            workflow_name="orchestrator",
            triggered_by="system",
        )
        
        logger.info(f"FP&A Orchestrator started for entity {self.entity_id}")
        
        # Start scheduler if autonomous mode
        if self.autonomous_mode:
            asyncio.create_task(self._scheduler_loop())
    
    async def stop(self):
        """Stop the orchestrator"""
        self.status = OrchestratorStatus.STOPPED
        self.audit_log.log(
            action=AuditAction.WORKFLOW_COMPLETED,
            description="FP&A Orchestrator stopped",
            workflow_name="orchestrator",
            triggered_by="system",
        )
        logger.info("FP&A Orchestrator stopped")
    
    async def pause(self):
        """Pause scheduled workflows (manual triggers still work)"""
        self.status = OrchestratorStatus.PAUSED
        logger.info("FP&A Orchestrator paused")
    
    async def resume(self):
        """Resume scheduled workflows"""
        self.status = OrchestratorStatus.RUNNING
        logger.info("FP&A Orchestrator resumed")
    
    # =========================================================================
    # WORKFLOW EXECUTION
    # =========================================================================
    
    async def run_workflow(
        self,
        workflow_name: str,
        triggered_by: str = "manual",
        user_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Run a specific workflow.
        
        Args:
            workflow_name: Name of the workflow to run
            triggered_by: Who/what triggered this ("schedule", "event", "manual", "user")
            user_id: User ID if triggered by a user
            **kwargs: Additional arguments passed to the workflow
        
        Returns:
            Workflow result dictionary
        """
        if workflow_name not in self._workflow_handlers:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        if self._workflow_status.get(workflow_name) == WorkflowStatus.RUNNING:
            logger.warning(f"Workflow {workflow_name} is already running")
            return {"error": "Workflow already running"}
        
        # Start workflow
        correlation_id = self.audit_log.log_workflow_start(
            workflow_name=workflow_name,
            triggered_by=triggered_by,
            user_id=user_id,
        )
        
        self._workflow_status[workflow_name] = WorkflowStatus.RUNNING
        start_time = datetime.utcnow()
        
        run = WorkflowRun(
            workflow_name=workflow_name,
            started_at=start_time,
            completed_at=None,
            status=WorkflowStatus.RUNNING,
            triggered_by=triggered_by,
            correlation_id=correlation_id,
        )
        
        try:
            # Execute workflow
            handler = self._workflow_handlers[workflow_name]
            result = await handler(
                orchestrator=self,
                entity_id=self.entity_id,
                **kwargs,
            )
            
            # Success
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self._workflow_status[workflow_name] = WorkflowStatus.COMPLETED
            run.status = WorkflowStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.result = result
            
            self.audit_log.log_workflow_complete(
                workflow_name=workflow_name,
                duration_ms=duration_ms,
                details={"result_summary": str(result)[:500]},
            )
            
            # Update scheduled task last run
            if workflow_name in self._scheduled_tasks:
                self._scheduled_tasks[workflow_name].last_run = datetime.utcnow()
            
            return result
            
        except Exception as e:
            # Failure
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self._workflow_status[workflow_name] = WorkflowStatus.FAILED
            run.status = WorkflowStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error = str(e)
            
            self.audit_log.log_workflow_failed(
                workflow_name=workflow_name,
                error=str(e),
                duration_ms=duration_ms,
            )
            
            logger.exception(f"Workflow {workflow_name} failed")
            return {"error": str(e)}
        
        finally:
            self._workflow_runs.append(run)
            # Keep only last 100 runs
            if len(self._workflow_runs) > 100:
                self._workflow_runs = self._workflow_runs[-100:]
    
    # =========================================================================
    # CONVENIENCE METHODS FOR WORKFLOWS
    # =========================================================================
    
    async def run_morning_briefing(
        self,
        triggered_by: str = "manual",
        user_id: Optional[str] = None,
    ) -> MorningBriefing:
        """Run the morning briefing workflow"""
        result = await self.run_workflow(
            "morning_briefing",
            triggered_by=triggered_by,
            user_id=user_id,
        )
        if isinstance(result, MorningBriefing):
            self._latest_briefing = result
        return result
    
    async def run_weekly_meeting_prep(
        self,
        triggered_by: str = "manual",
        user_id: Optional[str] = None,
        snapshot_id: Optional[int] = None,
    ) -> WeeklyPack:
        """Run the weekly meeting prep workflow"""
        result = await self.run_workflow(
            "weekly_meeting_prep",
            triggered_by=triggered_by,
            user_id=user_id,
            snapshot_id=snapshot_id,
        )
        if isinstance(result, WeeklyPack):
            self._latest_weekly_pack = result
        return result
    
    async def run_month_end_close(
        self,
        triggered_by: str = "manual",
        user_id: Optional[str] = None,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the month-end close workflow"""
        return await self.run_workflow(
            "month_end_close",
            triggered_by=triggered_by,
            user_id=user_id,
            period=period,
        )
    
    async def run_continuous_monitoring(self) -> Dict[str, Any]:
        """Run continuous monitoring"""
        return await self.run_workflow(
            "continuous_monitoring",
            triggered_by="schedule",
        )
    
    async def ask_question(
        self,
        question: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ask the AI analyst a question"""
        self.audit_log.log(
            action=AuditAction.QUESTION_ASKED,
            description=f"Question: {question[:100]}...",
            user_id=user_id,
            details={"question": question, "context": context},
        )
        
        result = await self.run_workflow(
            "question_answering",
            triggered_by="user",
            user_id=user_id,
            question=question,
            context=context,
        )
        
        self.audit_log.log(
            action=AuditAction.QUESTION_ANSWERED,
            description=f"Answered question for user {user_id}",
            user_id=user_id,
            details={"answer_length": len(str(result.get("answer", "")))},
        )
        
        return result
    
    # =========================================================================
    # EVENT HANDLING
    # =========================================================================
    
    async def handle_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle an incoming event"""
        logger.info(f"Handling event: {event_type}")
        
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(self, event_data)
            except Exception as e:
                logger.exception(f"Event handler failed for {event_type}")
    
    async def emit_event(self, event_type: str, event_data: Dict[str, Any]):
        """Emit an event for other components to handle"""
        await self.handle_event(event_type, event_data)
    
    # =========================================================================
    # SCHEDULER
    # =========================================================================
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.status == OrchestratorStatus.RUNNING:
            try:
                await self._check_scheduled_tasks()
            except Exception as e:
                logger.exception("Scheduler error")
            
            # Sleep for 1 minute between checks
            await asyncio.sleep(60)
    
    async def _check_scheduled_tasks(self):
        """Check if any scheduled tasks should run"""
        now = datetime.utcnow()
        
        for task_name, task in self._scheduled_tasks.items():
            if not task.enabled:
                continue
            
            if self._should_run_task(task, now):
                logger.info(f"Running scheduled task: {task_name}")
                await self.run_workflow(
                    task.workflow_name,
                    triggered_by="schedule",
                )
    
    def _should_run_task(self, task: ScheduledTask, now: datetime) -> bool:
        """Check if a task should run based on cron expression"""
        # Simplified cron check - in production, use a proper cron library
        # For now, just check basic patterns
        
        cron = task.cron_expression
        parts = cron.split()
        
        if len(parts) != 5:
            return False
        
        minute, hour, day, month, weekday = parts
        
        # Check minute
        if minute != "*" and minute != "*/15":
            if int(minute) != now.minute:
                return False
        elif minute == "*/15":
            if now.minute % 15 != 0:
                return False
        
        # Check hour
        if hour != "*":
            if int(hour) != now.hour:
                return False
        
        # Check weekday (0 = Monday for our purposes)
        if weekday != "*":
            if int(weekday) != now.weekday():
                return False
        
        # Don't run more than once per scheduled period
        if task.last_run:
            if minute == "*/15":
                if (now - task.last_run).total_seconds() < 14 * 60:
                    return False
            else:
                if task.last_run.date() == now.date() and task.last_run.hour == now.hour:
                    return False
        
        return True
    
    # =========================================================================
    # STATUS AND OUTPUTS
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "status": self.status.value,
            "entity_id": self.entity_id,
            "autonomous_mode": self.autonomous_mode,
            "workflows": {
                name: status.value
                for name, status in self._workflow_status.items()
            },
            "scheduled_tasks": {
                name: {
                    "enabled": task.enabled,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "cron": task.cron_expression,
                }
                for name, task in self._scheduled_tasks.items()
            },
            "decision_queue_stats": self.decision_queue.get_stats(),
            "recent_runs": [
                {
                    "workflow": run.workflow_name,
                    "started": run.started_at.isoformat(),
                    "status": run.status.value,
                    "triggered_by": run.triggered_by,
                }
                for run in self._workflow_runs[-10:]
            ],
        }
    
    def get_latest_briefing(self) -> Optional[MorningBriefing]:
        """Get the latest morning briefing"""
        return self._latest_briefing
    
    def get_latest_weekly_pack(self) -> Optional[WeeklyPack]:
        """Get the latest weekly pack"""
        return self._latest_weekly_pack
    
    def get_latest_variance_report(self) -> Optional[VarianceReport]:
        """Get the latest variance report"""
        return self._latest_variance_report
    
    def set_latest_variance_report(self, report: VarianceReport):
        """Set the latest variance report (called by variance workflow)"""
        self._latest_variance_report = report


# =========================================================================
# SINGLETON ORCHESTRATOR MANAGEMENT
# =========================================================================

_orchestrators: Dict[int, FPAOrchestrator] = {}


def get_orchestrator(db: Session, entity_id: int) -> FPAOrchestrator:
    """Get or create an orchestrator for an entity"""
    if entity_id not in _orchestrators:
        autonomous = os.getenv("FPA_AUTONOMOUS_MODE", "true").lower() == "true"
        _orchestrators[entity_id] = FPAOrchestrator(
            db=db,
            entity_id=entity_id,
            autonomous_mode=autonomous,
        )
    return _orchestrators[entity_id]
