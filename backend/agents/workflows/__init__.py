"""
FP&A Workflows

Core workflows that mirror real FP&A analyst routines:
- Morning Briefing (daily)
- Weekly Meeting Prep (Monday)
- Month-End Close (EOM)
- Continuous Monitoring (always)
- Question Answering (on-demand)
"""

from .morning_briefing import run_morning_briefing, MorningBriefingWorkflow
from .weekly_meeting_prep import run_weekly_meeting_prep, WeeklyMeetingPrepWorkflow
from .month_end_close import run_month_end_close, MonthEndCloseWorkflow
from .continuous_monitoring import run_continuous_monitoring, ContinuousMonitoringWorkflow
from .question_answering import run_question_answering, QuestionAnsweringWorkflow

__all__ = [
    'run_morning_briefing', 'MorningBriefingWorkflow',
    'run_weekly_meeting_prep', 'WeeklyMeetingPrepWorkflow',
    'run_month_end_close', 'MonthEndCloseWorkflow',
    'run_continuous_monitoring', 'ContinuousMonitoringWorkflow',
    'run_question_answering', 'QuestionAnsweringWorkflow',
]


def register_all_workflows(orchestrator):
    """Register all workflows with the orchestrator"""
    orchestrator.register_workflow("morning_briefing", run_morning_briefing)
    orchestrator.register_workflow("weekly_meeting_prep", run_weekly_meeting_prep)
    orchestrator.register_workflow("month_end_close", run_month_end_close)
    orchestrator.register_workflow("continuous_monitoring", run_continuous_monitoring)
    orchestrator.register_workflow("question_answering", run_question_answering)
