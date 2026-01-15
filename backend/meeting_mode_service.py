"""
Meeting Mode Workflow Service
Implements: refresh → snapshot → variance → actions workflow
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
import models
from variance_service import calculate_variance
from red_weeks_service import flag_red_weeks
from utils import get_unknown_bucket


def execute_meeting_mode_workflow(
    db: Session,
    current_snapshot_id: int,
    previous_snapshot_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute meeting mode workflow:
    1. Refresh data (check freshness)
    2. Create/lock snapshot
    3. Calculate variance vs previous
    4. Identify actions needed
    """
    current_snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == current_snapshot_id).first()
    if not current_snapshot:
        return {"error": "Current snapshot not found"}
    
    # 1. Check data freshness
    from data_freshness_service import check_data_freshness, get_data_freshness_summary
    freshness = check_data_freshness(db, current_snapshot.entity_id)
    freshness_summary = get_data_freshness_summary(db, current_snapshot.entity_id)
    
    # 2. Ensure snapshot is locked
    if not current_snapshot.is_locked:
        current_snapshot.is_locked = 1
        current_snapshot.lock_type = "Meeting"
        db.commit()
    
    # 3. Calculate variance if previous snapshot provided
    variance = None
    if previous_snapshot_id:
        variance = calculate_variance(db, current_snapshot_id, previous_snapshot_id)
    
    # 4. Identify red weeks
    red_weeks = flag_red_weeks(db, current_snapshot_id)
    
    # 5. Get unknown bucket status
    unknown_bucket = get_unknown_bucket(db, current_snapshot_id)
    
    # 6. Generate action recommendations
    actions = _generate_action_recommendations(
        db, current_snapshot_id, variance, red_weeks, unknown_bucket
    )
    
    return {
        "snapshot_id": current_snapshot_id,
        "snapshot_name": current_snapshot.name,
        "is_locked": current_snapshot.is_locked,
        "lock_type": current_snapshot.lock_type,
        "data_freshness": freshness_summary,
        "variance": variance,
        "red_weeks": red_weeks,
        "unknown_bucket": unknown_bucket,
        "recommended_actions": actions,
        "workflow_completed_at": datetime.utcnow().isoformat()
    }


def _generate_action_recommendations(
    db: Session,
    snapshot_id: int,
    variance: Optional[Dict[str, Any]],
    red_weeks: Dict[str, Any],
    unknown_bucket: Dict[str, Any]
) -> list:
    """Generate action recommendations based on variance, red weeks, unknown bucket"""
    actions = []
    
    # Check for red weeks
    if red_weeks.get("total_red_weeks", 0) > 0:
        actions.append({
            "priority": "High",
            "type": "Cash Shortfall",
            "description": f"{red_weeks['total_red_weeks']} weeks below threshold",
            "action": "Review red weeks and consider liquidity actions"
        })
    
    # Check unknown bucket
    if not unknown_bucket.get("kpi_target_met", True):
        unknown_pct = unknown_bucket.get("unknown_pct", 0)
        actions.append({
            "priority": "Medium",
            "type": "Data Quality",
            "description": f"Unknown bucket at {unknown_pct:.1f}% exceeds target",
            "action": "Resolve missing data (FX rates, due dates, etc.)"
        })
    
    # Check variance for significant changes
    if variance and variance.get("variance_breakdown"):
        # Check for large timing shifts
        for week_key, week_var in variance.get("variance_breakdown", {}).items():
            if isinstance(week_var, dict) and abs(week_var.get("inflow_delta", 0)) > 100000:
                actions.append({
                    "priority": "Medium",
                    "type": "Timing Shift",
                    "description": f"Significant inflow change in {week_key}",
                    "action": "Review timing shifts and update forecasts"
                })
    
    return actions





