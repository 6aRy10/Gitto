"""
Red Weeks Flagging Service
Flags weeks where cash falls below threshold with cause attribution.
"""

from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import models
from cash_calendar_service import get_13_week_workspace


def flag_red_weeks(
    db: Session,
    snapshot_id: int,
    threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Flag weeks where closing cash falls below threshold.
    Returns attribution of largest drivers.
    
    Args:
        threshold: Cash threshold (defaults to snapshot.min_cash_threshold)
    """
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        return {"red_weeks": [], "threshold": threshold or 0.0}
    
    threshold = threshold or snapshot.min_cash_threshold or 0.0
    
    workspace = get_13_week_workspace(db, snapshot_id)
    if not workspace or 'grid' not in workspace:
        return {"red_weeks": [], "threshold": threshold}
    
    red_weeks = []
    
    for week in workspace['grid']:
        closing_cash = week.get('closing_cash', 0)
        
        if closing_cash < threshold:
            # Calculate cause attribution
            inflows = week.get('inflow_p50', 0)
            outflows = week.get('outflow_committed', 0)
            opening = week.get('opening_cash', 0)
            
            # Identify largest drivers
            drivers = []
            
            # Check if low opening cash is the issue
            if opening < threshold:
                drivers.append({
                    "type": "low_opening_cash",
                    "amount": opening,
                    "impact": opening - threshold
                })
            
            # Check if high outflows are the issue
            if outflows > inflows:
                drivers.append({
                    "type": "high_outflows",
                    "amount": outflows,
                    "impact": outflows - inflows
                })
            
            # Check if low inflows are the issue
            if inflows < outflows:
                drivers.append({
                    "type": "low_inflows",
                    "amount": inflows,
                    "impact": inflows - outflows
                })
            
            # Sort by absolute impact
            drivers.sort(key=lambda x: abs(x['impact']), reverse=True)
            
            red_weeks.append({
                "week_label": week.get('week_label', 'Unknown'),
                "week_index": workspace['grid'].index(week),
                "closing_cash": closing_cash,
                "threshold": threshold,
                "shortfall": threshold - closing_cash,
                "largest_drivers": drivers[:3],  # Top 3 drivers
                "opening_cash": opening,
                "inflows": inflows,
                "outflows": outflows
            })
    
    return {
        "red_weeks": red_weeks,
        "threshold": threshold,
        "total_red_weeks": len(red_weeks),
        "snapshot_id": snapshot_id
    }


def get_red_weeks_drilldown(
    db: Session,
    snapshot_id: int,
    week_index: int
) -> Dict[str, Any]:
    """
    Get detailed drilldown for a red week.
    Returns invoice/bill IDs that contribute to the shortfall.
    """
    from cash_calendar_service import get_week_drilldown_data
    
    # Get week details
    inflows_data = get_week_drilldown_data(db, snapshot_id, week_index, "inflow")
    outflows_data = get_week_drilldown_data(db, snapshot_id, week_index, "outflow")
    
    # Get workspace to find threshold
    workspace = get_13_week_workspace(db, snapshot_id)
    if workspace and 'grid' and week_index < len(workspace['grid']):
        week = workspace['grid'][week_index]
        threshold = workspace.get('min_cash_threshold', 0.0)
        closing_cash = week.get('closing_cash', 0)
        
        return {
            "week_index": week_index,
            "week_label": week.get('week_label', 'Unknown'),
            "closing_cash": closing_cash,
            "threshold": threshold,
            "shortfall": max(0, threshold - closing_cash),
            "inflow_items": inflows_data.get('items', []),
            "outflow_items": outflows_data.get('items', []),
            "total_inflow": sum(item.get('amount', 0) for item in inflows_data.get('items', [])),
            "total_outflow": sum(item.get('amount', 0) for item in outflows_data.get('items', []))
        }
    
    return {"error": "Week not found"}





