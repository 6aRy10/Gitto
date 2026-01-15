"""
Red Weeks Cause Attribution Service
Explains WHY a week is projected to be below threshold (red).
Provides actionable breakdown for CFO decision-making.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import models


class RedWeekCause:
    """Cause category for red week"""
    LARGE_OUTFLOW = "large_outflow"
    CONCENTRATED_OUTFLOW = "concentrated_outflow"
    DELAYED_INFLOWS = "delayed_inflows"
    HIGH_RISK_RECEIVABLES = "high_risk_receivables"
    UNUSUAL_PAYROLL = "unusual_payroll"
    TAX_PAYMENT = "tax_payment"
    SEASONAL_PATTERN = "seasonal_pattern"
    OPENING_BALANCE_LOW = "opening_balance_low"
    FX_ADVERSE = "fx_adverse"


def analyze_red_week_causes(
    db: Session,
    snapshot_id: int,
    week_index: int,
    threshold: float,
    grid_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze why a specific week is red (below threshold).
    Returns attribution breakdown with amounts and percentages.
    """
    if week_index >= len(grid_data):
        return {"error": "Invalid week index"}
    
    week = grid_data[week_index]
    closing_cash = week.get("closing_cash", 0)
    shortfall = threshold - closing_cash
    
    if shortfall <= 0:
        return {
            "is_red": False,
            "week_index": week_index,
            "week_label": week.get("week_label"),
            "closing_cash": closing_cash,
            "threshold": threshold,
            "message": "Week is not below threshold"
        }
    
    causes = []
    
    # 1. Analyze large outflows
    outflow_total = week.get("outflow_total", 0)
    avg_outflow = sum(w.get("outflow_total", 0) for w in grid_data) / max(len(grid_data), 1)
    
    if outflow_total > avg_outflow * 1.5:
        excess_outflow = outflow_total - avg_outflow
        causes.append({
            "cause": RedWeekCause.LARGE_OUTFLOW,
            "description": "Outflows are 50%+ higher than average",
            "impact_amount": excess_outflow,
            "impact_pct": round(min(100, (excess_outflow / shortfall) * 100), 1),
            "severity": "high" if outflow_total > avg_outflow * 2 else "medium",
            "recommendation": "Review discretionary payments that can be delayed"
        })
    
    # 2. Analyze inflow shortfall
    inflow = week.get("inflow_p50", 0)
    prev_week_inflow = grid_data[week_index - 1].get("inflow_p50", 0) if week_index > 0 else inflow
    
    if inflow < prev_week_inflow * 0.7:
        inflow_drop = prev_week_inflow - inflow
        causes.append({
            "cause": RedWeekCause.DELAYED_INFLOWS,
            "description": "Expected inflows dropped 30%+ from prior week",
            "impact_amount": inflow_drop,
            "impact_pct": round(min(100, (inflow_drop / shortfall) * 100), 1),
            "severity": "high" if inflow < prev_week_inflow * 0.5 else "medium",
            "recommendation": "Accelerate collections on top-priority invoices"
        })
    
    # 3. Check for concentrated outflows (one big payment)
    # This would require drill-down data, simulate with heuristic
    if outflow_total > threshold * 0.5:
        causes.append({
            "cause": RedWeekCause.CONCENTRATED_OUTFLOW,
            "description": "Large single payment may be concentrated this week",
            "impact_amount": outflow_total * 0.6,  # Estimate
            "impact_pct": round(min(100, ((outflow_total * 0.6) / shortfall) * 100), 1),
            "severity": "medium",
            "recommendation": "Check if any large payments can be split across weeks"
        })
    
    # 4. Opening balance contribution
    opening = week.get("opening_cash", 0)
    if opening < threshold:
        opening_gap = threshold - opening
        causes.append({
            "cause": RedWeekCause.OPENING_BALANCE_LOW,
            "description": "Week started below threshold",
            "impact_amount": opening_gap,
            "impact_pct": round(min(100, (opening_gap / shortfall) * 100), 1),
            "severity": "medium",
            "recommendation": "Review prior week's cash management"
        })
    
    # Sort by impact percentage
    causes.sort(key=lambda x: x["impact_pct"], reverse=True)
    
    # Calculate total attribution (should sum to ~100% but may not be exact)
    total_attributed = sum(c["impact_pct"] for c in causes)
    
    return {
        "is_red": True,
        "week_index": week_index,
        "week_label": week.get("week_label"),
        "closing_cash": closing_cash,
        "threshold": threshold,
        "shortfall": shortfall,
        "causes": causes,
        "total_attributed_pct": round(total_attributed, 1),
        "top_cause": causes[0] if causes else None,
        "action_summary": _generate_action_summary(causes)
    }


def _generate_action_summary(causes: List[Dict]) -> str:
    """Generate human-readable action summary"""
    if not causes:
        return "No specific cause identified. Review cash flow assumptions."
    
    top_cause = causes[0]
    cause_type = top_cause["cause"]
    
    summaries = {
        RedWeekCause.LARGE_OUTFLOW: "Consider delaying discretionary vendor payments.",
        RedWeekCause.CONCENTRATED_OUTFLOW: "Split large payments or negotiate payment terms.",
        RedWeekCause.DELAYED_INFLOWS: "Prioritize collections calls this week.",
        RedWeekCause.HIGH_RISK_RECEIVABLES: "Escalate collections on at-risk accounts.",
        RedWeekCause.OPENING_BALANCE_LOW: "Address prior week shortfall first.",
        RedWeekCause.FX_ADVERSE: "Consider FX hedging for major payments."
    }
    
    return summaries.get(cause_type, "Review week details for optimization opportunities.")


def get_all_red_weeks_analysis(
    db: Session,
    snapshot_id: int,
    threshold: float,
    grid_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze all red weeks in the 13-week forecast"""
    red_weeks = []
    
    for idx, week in enumerate(grid_data):
        if week.get("closing_cash", 0) < threshold:
            analysis = analyze_red_week_causes(db, snapshot_id, idx, threshold, grid_data)
            red_weeks.append(analysis)
    
    # Calculate aggregate statistics
    total_shortfall = sum(w["shortfall"] for w in red_weeks)
    
    # Aggregate cause frequency
    cause_frequency = {}
    for week in red_weeks:
        for cause in week.get("causes", []):
            cause_type = cause["cause"]
            if cause_type not in cause_frequency:
                cause_frequency[cause_type] = {"count": 0, "total_impact": 0}
            cause_frequency[cause_type]["count"] += 1
            cause_frequency[cause_type]["total_impact"] += cause["impact_amount"]
    
    return {
        "total_red_weeks": len(red_weeks),
        "red_week_indices": [w["week_index"] for w in red_weeks],
        "total_shortfall": total_shortfall,
        "cause_summary": cause_frequency,
        "weeks": red_weeks,
        "primary_recommendation": _get_primary_recommendation(cause_frequency)
    }


def _get_primary_recommendation(cause_frequency: Dict[str, Any]) -> str:
    """Get the most impactful recommendation based on cause frequency"""
    if not cause_frequency:
        return "No red weeks detected. Cash position is healthy."
    
    # Find cause with highest total impact
    top_cause = max(cause_frequency.items(), key=lambda x: x[1]["total_impact"])
    cause_type = top_cause[0]
    
    recommendations = {
        RedWeekCause.LARGE_OUTFLOW: "Focus on payment timing optimization - delay non-critical payments.",
        RedWeekCause.DELAYED_INFLOWS: "Aggressive collections push needed - contact top 10 accounts.",
        RedWeekCause.CONCENTRATED_OUTFLOW: "Negotiate payment splits with major vendors.",
        RedWeekCause.OPENING_BALANCE_LOW: "Build cash buffer in preceding weeks.",
    }
    
    return recommendations.get(cause_type, "Review detailed cash flow analysis.")


def get_week_drill_with_attribution(
    db: Session,
    snapshot_id: int,
    week_index: int,
    week_data: Dict[str, Any],
    threshold: float
) -> Dict[str, Any]:
    """Get drilldown details with cause attribution for a specific week"""
    # Get base cause analysis
    analysis = analyze_red_week_causes(db, snapshot_id, week_index, threshold, [week_data])
    
    # Add line-item breakdown (would be populated from actual drill-down data)
    analysis["line_items"] = {
        "inflows": [],  # Would be populated from actual data
        "outflows": [],  # Would be populated from actual data
    }
    
    return analysis




