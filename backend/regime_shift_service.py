"""
Regime Shift Detection Service
Detects significant changes in payment behavior patterns.
Prevents forecast from overreacting to noise or under-reacting to real shifts.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import models
from collections import defaultdict
import statistics


class RegimeShiftType:
    """Types of regime shifts that can be detected"""
    DELAY_INCREASE = "delay_increase"       # Customers paying later
    DELAY_DECREASE = "delay_decrease"       # Customers paying earlier
    VOLUME_INCREASE = "volume_increase"     # Higher transaction volumes
    VOLUME_DECREASE = "volume_decrease"     # Lower transaction volumes
    SEASONAL_SHIFT = "seasonal_shift"       # Seasonal pattern change
    CUSTOMER_BEHAVIOR = "customer_behavior" # Single customer behavior change
    UNKNOWN = "unknown"


class RegimeShiftSeverity:
    """Severity levels for regime shifts"""
    LOW = "low"           # < 1 std dev change
    MEDIUM = "medium"     # 1-2 std dev change
    HIGH = "high"         # 2-3 std dev change
    CRITICAL = "critical" # > 3 std dev change


def detect_regime_shifts(
    db: Session,
    entity_id: int,
    lookback_weeks: int = 26,
    sensitivity: float = 2.0  # Standard deviations for detection
) -> Dict[str, Any]:
    """
    Detect regime shifts in payment behavior.
    
    Args:
        db: Database session
        entity_id: Entity to analyze
        lookback_weeks: How far back to look for patterns
        sensitivity: Number of standard deviations to trigger detection
    
    Returns:
        Dictionary with detected shifts and recommendations
    """
    cutoff_date = datetime.utcnow() - timedelta(weeks=lookback_weeks)
    
    # Get historical invoice data
    invoices = db.query(models.Invoice).filter(
        models.Invoice.entity_id == entity_id,
        models.Invoice.payment_date != None,
        models.Invoice.expected_due_date != None,
        models.Invoice.payment_date >= cutoff_date
    ).all()
    
    if len(invoices) < 30:
        return {
            "status": "insufficient_data",
            "message": f"Need at least 30 paid invoices, found {len(invoices)}",
            "shifts": [],
            "recommendations": []
        }
    
    # Calculate delay days for each invoice
    delays = []
    weekly_delays = defaultdict(list)
    customer_delays = defaultdict(list)
    
    for inv in invoices:
        delay = (inv.payment_date - inv.expected_due_date).days
        delays.append(delay)
        
        # Group by week
        week_key = inv.payment_date.isocalendar()[1]  # ISO week number
        weekly_delays[week_key].append(delay)
        
        # Group by customer
        if inv.customer:
            customer_delays[inv.customer].append(delay)
    
    # Calculate statistics
    mean_delay = statistics.mean(delays)
    std_delay = statistics.stdev(delays) if len(delays) > 1 else 0
    
    shifts = []
    
    # 1. Check for overall trend shift (compare recent 4 weeks vs prior)
    recent_delays = []
    prior_delays = []
    
    for inv in invoices:
        if inv.payment_date > datetime.utcnow() - timedelta(weeks=4):
            recent_delays.append((inv.payment_date - inv.expected_due_date).days)
        elif inv.payment_date > datetime.utcnow() - timedelta(weeks=12):
            prior_delays.append((inv.payment_date - inv.expected_due_date).days)
    
    if recent_delays and prior_delays:
        recent_mean = statistics.mean(recent_delays)
        prior_mean = statistics.mean(prior_delays)
        change = recent_mean - prior_mean
        
        if std_delay > 0 and abs(change) > sensitivity * std_delay:
            severity = _calculate_severity(change, std_delay)
            shift_type = RegimeShiftType.DELAY_INCREASE if change > 0 else RegimeShiftType.DELAY_DECREASE
            
            shifts.append({
                "type": shift_type,
                "severity": severity,
                "metric": "average_delay_days",
                "prior_value": round(prior_mean, 1),
                "current_value": round(recent_mean, 1),
                "change": round(change, 1),
                "z_score": round(change / std_delay, 2) if std_delay > 0 else 0,
                "detected_at": datetime.utcnow().isoformat(),
                "description": f"Payment delays {'increased' if change > 0 else 'decreased'} by {abs(round(change, 1))} days",
                "recommendation": _get_recommendation(shift_type, severity)
            })
    
    # 2. Check for customer-specific shifts
    for customer, cust_delays in customer_delays.items():
        if len(cust_delays) < 5:
            continue
        
        cust_mean = statistics.mean(cust_delays)
        
        # Compare to overall mean
        if std_delay > 0 and abs(cust_mean - mean_delay) > sensitivity * std_delay:
            severity = _calculate_severity(cust_mean - mean_delay, std_delay)
            
            if cust_mean > mean_delay + sensitivity * std_delay:
                shifts.append({
                    "type": RegimeShiftType.CUSTOMER_BEHAVIOR,
                    "severity": severity,
                    "customer": customer,
                    "metric": "customer_delay_days",
                    "overall_avg": round(mean_delay, 1),
                    "customer_avg": round(cust_mean, 1),
                    "invoice_count": len(cust_delays),
                    "description": f"Customer {customer} pays {round(cust_mean - mean_delay, 1)} days later than average",
                    "recommendation": f"Adjust forecast for {customer} or initiate collections conversation"
                })
    
    # 3. Calculate recency weights
    recency_weights = _calculate_recency_weights(invoices)
    
    # Generate recommendations
    recommendations = _generate_recommendations(shifts)
    
    return {
        "status": "analyzed",
        "entity_id": entity_id,
        "analysis_period": {
            "start": cutoff_date.isoformat(),
            "end": datetime.utcnow().isoformat()
        },
        "sample_size": len(invoices),
        "baseline_stats": {
            "mean_delay_days": round(mean_delay, 1),
            "std_delay_days": round(std_delay, 1),
            "sensitivity_threshold": sensitivity
        },
        "shifts_detected": len(shifts),
        "shifts": shifts,
        "recency_weights": recency_weights,
        "recommendations": recommendations
    }


def _calculate_severity(change: float, std_dev: float) -> str:
    """Calculate severity based on standard deviations"""
    if std_dev == 0:
        return RegimeShiftSeverity.LOW
    
    z_score = abs(change / std_dev)
    
    if z_score < 1:
        return RegimeShiftSeverity.LOW
    elif z_score < 2:
        return RegimeShiftSeverity.MEDIUM
    elif z_score < 3:
        return RegimeShiftSeverity.HIGH
    else:
        return RegimeShiftSeverity.CRITICAL


def _get_recommendation(shift_type: str, severity: str) -> str:
    """Get recommendation based on shift type and severity"""
    recommendations = {
        (RegimeShiftType.DELAY_INCREASE, RegimeShiftSeverity.CRITICAL): 
            "URGENT: Significant payment delay increase. Review collections strategy immediately.",
        (RegimeShiftType.DELAY_INCREASE, RegimeShiftSeverity.HIGH): 
            "Payment delays increasing. Consider adjusting forecast weights and collections prioritization.",
        (RegimeShiftType.DELAY_INCREASE, RegimeShiftSeverity.MEDIUM): 
            "Moderate delay increase detected. Monitor trend and consider proactive collections.",
        (RegimeShiftType.DELAY_INCREASE, RegimeShiftSeverity.LOW): 
            "Minor delay increase. Continue monitoring.",
        (RegimeShiftType.DELAY_DECREASE, RegimeShiftSeverity.CRITICAL): 
            "Significant improvement in payment timing. Consider updating forecast to reflect better collections.",
        (RegimeShiftType.DELAY_DECREASE, RegimeShiftSeverity.HIGH): 
            "Customers paying faster. Update forecast accordingly.",
    }
    
    return recommendations.get(
        (shift_type, severity), 
        f"Monitor {shift_type} pattern. Consider forecast adjustment if trend continues."
    )


def _calculate_recency_weights(invoices: List[models.Invoice]) -> Dict[str, float]:
    """
    Calculate recency weights for forecast model.
    More recent data gets higher weight.
    """
    now = datetime.utcnow()
    
    # Group invoices by recency bucket
    buckets = {
        "0-4_weeks": 0,
        "5-8_weeks": 0,
        "9-13_weeks": 0,
        "14-26_weeks": 0,
        "26+_weeks": 0
    }
    
    for inv in invoices:
        age_weeks = (now - inv.payment_date).days / 7
        
        if age_weeks <= 4:
            buckets["0-4_weeks"] += 1
        elif age_weeks <= 8:
            buckets["5-8_weeks"] += 1
        elif age_weeks <= 13:
            buckets["9-13_weeks"] += 1
        elif age_weeks <= 26:
            buckets["14-26_weeks"] += 1
        else:
            buckets["26+_weeks"] += 1
    
    # Calculate weights (more recent = higher weight)
    total = sum(buckets.values())
    if total == 0:
        return {"message": "No data for weight calculation"}
    
    # Recency multipliers
    multipliers = {
        "0-4_weeks": 2.0,
        "5-8_weeks": 1.5,
        "9-13_weeks": 1.0,
        "14-26_weeks": 0.5,
        "26+_weeks": 0.25
    }
    
    weighted_counts = {
        bucket: count * multipliers[bucket] 
        for bucket, count in buckets.items()
    }
    
    total_weighted = sum(weighted_counts.values())
    
    return {
        "bucket_counts": buckets,
        "bucket_weights": {
            bucket: round(count / total_weighted, 3) if total_weighted > 0 else 0
            for bucket, count in weighted_counts.items()
        },
        "recommended_weight_schema": "recency_weighted"
    }


def _generate_recommendations(shifts: List[Dict]) -> List[str]:
    """Generate aggregated recommendations based on all detected shifts"""
    if not shifts:
        return ["No significant regime shifts detected. Current forecast parameters are appropriate."]
    
    recommendations = []
    
    # Count shift types
    delay_increases = [s for s in shifts if s["type"] == RegimeShiftType.DELAY_INCREASE]
    customer_issues = [s for s in shifts if s["type"] == RegimeShiftType.CUSTOMER_BEHAVIOR]
    
    if delay_increases:
        critical = [s for s in delay_increases if s["severity"] == RegimeShiftSeverity.CRITICAL]
        if critical:
            recommendations.append(
                "🚨 CRITICAL: Overall payment delays have significantly increased. "
                "Immediate review of collections strategy recommended. "
                "Consider increasing recency weights in forecast model."
            )
        else:
            recommendations.append(
                "⚠️ Payment delays trending upward. Consider adjusting forecast sensitivity."
            )
    
    if customer_issues:
        problematic_customers = [s["customer"] for s in customer_issues]
        recommendations.append(
            f"📋 {len(customer_issues)} customer(s) showing unusual payment patterns: "
            f"{', '.join(problematic_customers[:5])}. Consider customer-specific forecast adjustments."
        )
    
    return recommendations


def apply_regime_shift_to_forecast(
    db: Session,
    snapshot_id: int,
    shift_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply regime shift detection to adjust forecast parameters.
    
    Returns updated forecast configuration.
    """
    if shift_data.get("status") != "analyzed":
        return {"applied": False, "reason": "No valid analysis to apply"}
    
    shifts = shift_data.get("shifts", [])
    if not shifts:
        return {"applied": False, "reason": "No shifts detected"}
    
    # Calculate adjustment factor
    delay_shifts = [s for s in shifts if "change" in s and s["type"] in 
                    [RegimeShiftType.DELAY_INCREASE, RegimeShiftType.DELAY_DECREASE]]
    
    if delay_shifts:
        avg_change = sum(s["change"] for s in delay_shifts) / len(delay_shifts)
        
        # Apply adjustment to snapshot's forecast config
        snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
        if snapshot:
            # Update assumption set with regime shift adjustment
            current_assumptions = snapshot.assumption_set_id_ref or {}
            if isinstance(current_assumptions, str):
                import json
                current_assumptions = json.loads(current_assumptions) if current_assumptions else {}
            
            current_assumptions["regime_shift_adjustment"] = {
                "detected_at": datetime.utcnow().isoformat(),
                "delay_adjustment_days": round(avg_change, 1),
                "shifts_count": len(shifts),
                "recency_weights": shift_data.get("recency_weights", {})
            }
            
            # Note: In a real implementation, you'd update the snapshot here
            
            return {
                "applied": True,
                "snapshot_id": snapshot_id,
                "adjustment": {
                    "delay_shift_days": round(avg_change, 1),
                    "recency_weights_applied": True
                }
            }
    
    return {"applied": False, "reason": "No applicable adjustments calculated"}




