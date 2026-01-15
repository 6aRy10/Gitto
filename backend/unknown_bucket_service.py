"""
Unknown Bucket Service
CFO Trust Feature: Explicit quantification of unforecastable items with severity categories.

Categories:
1. Missing Due Dates - invoices without expected_due_date
2. Held AP Bills - bills manually held by CFO
3. Unmatched Bank Cash - bank transactions not reconciled
4. Missing FX Rates - non-EUR items without exchange rate
5. Blocked/Disputed - items in dispute or blocked

Each category tracks:
- Count and amount
- Severity (critical/high/medium/low)
- SLA target (e.g., <5% of portfolio)
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import models


def get_unknown_bucket_summary(db: Session, snapshot_id: int) -> Dict[str, Any]:
    """
    Get complete unknown bucket breakdown with severity categories.
    This is the drill-down behind the Unknown badge.
    """
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        return {"error": "Snapshot not found"}
    
    # Get KPI target from snapshot config
    kpi_target_pct = snapshot.unknown_bucket_kpi_target or 5.0
    
    # Collect all unknown items by category
    categories = {
        "missing_due_date": _get_missing_due_dates(db, snapshot_id),
        "held_ap_bills": _get_held_ap_bills(db, snapshot_id),
        "unmatched_bank_cash": _get_unmatched_bank_cash(db, snapshot.entity_id),
        "missing_fx_rates": _get_missing_fx_rates(db, snapshot_id),
        "blocked_disputed": _get_blocked_disputed(db, snapshot_id)
    }
    
    # Calculate totals
    total_unknown_amount = sum(cat["amount"] for cat in categories.values())
    total_unknown_count = sum(cat["count"] for cat in categories.values())
    
    # Calculate portfolio total for percentage
    total_portfolio = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id
    ).with_entities(models.Invoice.amount).all()
    portfolio_amount = sum(inv[0] or 0 for inv in total_portfolio)
    
    unknown_pct = (total_unknown_amount / portfolio_amount * 100) if portfolio_amount > 0 else 0
    
    # Determine overall severity
    if unknown_pct > kpi_target_pct * 2:
        overall_severity = "critical"
    elif unknown_pct > kpi_target_pct:
        overall_severity = "high"
    elif unknown_pct > kpi_target_pct * 0.5:
        overall_severity = "medium"
    else:
        overall_severity = "low"
    
    return {
        "snapshot_id": snapshot_id,
        "categories": categories,
        "summary": {
            "total_count": total_unknown_count,
            "total_amount": total_unknown_amount,
            "portfolio_amount": portfolio_amount,
            "unknown_pct": round(unknown_pct, 2),
            "kpi_target_pct": kpi_target_pct,
            "meets_kpi": unknown_pct <= kpi_target_pct,
            "overall_severity": overall_severity
        },
        "trend": _calculate_trend(db, snapshot_id, unknown_pct)
    }


def _get_missing_due_dates(db: Session, snapshot_id: int) -> Dict[str, Any]:
    """Get invoices missing expected_due_date."""
    invoices = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.expected_due_date == None,
        models.Invoice.payment_date == None  # Only open invoices
    ).all()
    
    return {
        "count": len(invoices),
        "amount": sum(inv.amount or 0 for inv in invoices),
        "severity": "critical" if len(invoices) > 10 else "high" if len(invoices) > 5 else "medium",
        "reason": "Cannot forecast payment timing without due date",
        "action_required": "Upload missing due dates or use bulk update",
        "invoice_ids": [inv.id for inv in invoices[:50]]  # Limit for performance
    }


def _get_held_ap_bills(db: Session, snapshot_id: int) -> Dict[str, Any]:
    """Get AP bills manually held by CFO."""
    bills = db.query(models.VendorBill).filter(
        models.VendorBill.snapshot_id == snapshot_id,
        models.VendorBill.hold_status == 1
    ).all()
    
    return {
        "count": len(bills),
        "amount": sum(bill.amount or 0 for bill in bills),
        "severity": "low",  # Held bills are intentional
        "reason": "Bills held by CFO - excluded from outflow forecast",
        "action_required": "Review holds periodically - release or defer",
        "bill_ids": [bill.id for bill in bills[:50]]
    }


def _get_unmatched_bank_cash(db: Session, entity_id: Optional[int]) -> Dict[str, Any]:
    """Get unreconciled bank transactions."""
    if not entity_id:
        return {"count": 0, "amount": 0, "severity": "low", "reason": "No entity linked", "transaction_ids": []}
    
    txns = db.query(models.BankTransaction).join(
        models.BankAccount
    ).filter(
        models.BankAccount.entity_id == entity_id,
        models.BankTransaction.is_reconciled == 0
    ).all()
    
    # Separate by age for severity
    now = datetime.utcnow()
    old_txns = [t for t in txns if t.transaction_date and (now - t.transaction_date).days > 30]
    
    severity = "critical" if len(old_txns) > 5 else "high" if len(txns) > 10 else "medium" if len(txns) > 5 else "low"
    
    return {
        "count": len(txns),
        "amount": sum(abs(t.amount) for t in txns),
        "severity": severity,
        "reason": "Bank cash movements not matched to invoices",
        "action_required": "Review reconciliation suggestions or manual match",
        "transaction_ids": [t.id for t in txns[:50]],
        "aging": {
            "0-7_days": len([t for t in txns if t.transaction_date and (now - t.transaction_date).days <= 7]),
            "8-30_days": len([t for t in txns if t.transaction_date and 7 < (now - t.transaction_date).days <= 30]),
            "31+_days": len(old_txns)
        }
    }


def _get_missing_fx_rates(db: Session, snapshot_id: int) -> Dict[str, Any]:
    """Get non-EUR invoices without FX rates."""
    # Get all FX rates for this snapshot
    fx_rates = db.query(models.WeeklyFXRate).filter(
        models.WeeklyFXRate.snapshot_id == snapshot_id
    ).all()
    available_currencies = {r.from_currency for r in fx_rates}
    available_currencies.add("EUR")  # EUR is always available
    
    # Find invoices with currencies not in available list
    invoices = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.payment_date == None,
        ~models.Invoice.currency.in_(available_currencies)
    ).all()
    
    # Group by currency
    by_currency = {}
    for inv in invoices:
        curr = inv.currency or "UNKNOWN"
        if curr not in by_currency:
            by_currency[curr] = {"count": 0, "amount": 0}
        by_currency[curr]["count"] += 1
        by_currency[curr]["amount"] += inv.amount or 0
    
    return {
        "count": len(invoices),
        "amount": sum(inv.amount or 0 for inv in invoices),
        "severity": "high" if len(invoices) > 5 else "medium" if len(invoices) > 0 else "low",
        "reason": "Cannot convert to reporting currency without FX rate",
        "action_required": "Set FX rates for missing currencies",
        "invoice_ids": [inv.id for inv in invoices[:50]],
        "currencies_missing": by_currency
    }


def _get_blocked_disputed(db: Session, snapshot_id: int) -> Dict[str, Any]:
    """Get blocked or disputed invoices."""
    blocked = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.payment_date == None,
        models.Invoice.is_blocked == 1
    ).all()
    
    disputed = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.payment_date == None,
        models.Invoice.dispute_status == "open"
    ).all()
    
    # Deduplicate (invoice could be both blocked and disputed)
    all_ids = set()
    all_invoices = []
    for inv in blocked + disputed:
        if inv.id not in all_ids:
            all_ids.add(inv.id)
            all_invoices.append(inv)
    
    # Group by reason
    by_reason = {}
    for inv in all_invoices:
        reason = inv.blocked_reason or "in_dispute"
        if reason not in by_reason:
            by_reason[reason] = {"count": 0, "amount": 0}
        by_reason[reason]["count"] += 1
        by_reason[reason]["amount"] += inv.amount or 0
    
    return {
        "count": len(all_invoices),
        "amount": sum(inv.amount or 0 for inv in all_invoices),
        "severity": "high" if sum(inv.amount or 0 for inv in all_invoices) > 100000 else "medium",
        "reason": "Payment timing uncertain due to dispute or blockage",
        "action_required": "Resolve disputes and unblock to enable forecasting",
        "invoice_ids": [inv.id for inv in all_invoices[:50]],
        "by_reason": by_reason
    }


def _calculate_trend(db: Session, snapshot_id: int, current_pct: float) -> Dict[str, Any]:
    """Calculate week-over-week trend in unknown bucket percentage."""
    # Find previous snapshot
    current = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not current:
        return {"change": 0, "direction": "flat"}
    
    previous = db.query(models.Snapshot).filter(
        models.Snapshot.entity_id == current.entity_id,
        models.Snapshot.id < snapshot_id
    ).order_by(models.Snapshot.id.desc()).first()
    
    if not previous:
        return {"change": 0, "direction": "flat", "previous_pct": None}
    
    # Calculate previous unknown percentage
    prev_summary = get_unknown_bucket_summary(db, previous.id)
    prev_pct = prev_summary.get("summary", {}).get("unknown_pct", current_pct)
    
    change = current_pct - prev_pct
    direction = "improving" if change < 0 else "worsening" if change > 0 else "flat"
    
    return {
        "change": round(change, 2),
        "direction": direction,
        "previous_pct": prev_pct,
        "previous_snapshot_id": previous.id
    }


def get_unknown_bucket_kpi(db: Session, entity_id: int) -> Dict[str, Any]:
    """
    Get Unknown Bucket KPI for entity dashboard.
    Shows current % and target with trend.
    """
    # Get latest snapshot for entity
    latest = db.query(models.Snapshot).filter(
        models.Snapshot.entity_id == entity_id
    ).order_by(models.Snapshot.created_at.desc()).first()
    
    if not latest:
        return {
            "current_pct": 0,
            "target_pct": 5.0,
            "meets_target": True,
            "trend": "flat"
        }
    
    summary = get_unknown_bucket_summary(db, latest.id)
    
    return {
        "snapshot_id": latest.id,
        "current_pct": summary["summary"]["unknown_pct"],
        "target_pct": summary["summary"]["kpi_target_pct"],
        "meets_target": summary["summary"]["meets_kpi"],
        "severity": summary["summary"]["overall_severity"],
        "trend": summary["trend"]["direction"],
        "trend_change": summary["trend"]["change"]
    }


def set_unknown_bucket_kpi_target(db: Session, snapshot_id: int, kpi_target: float) -> Dict[str, Any]:
    """
    Set KPI target for unknown bucket percentage.
    """
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        return {"error": "Snapshot not found"}
    
    snapshot.unknown_bucket_kpi_target = kpi_target
    db.commit()
    
    return {
        "snapshot_id": snapshot_id,
        "kpi_target": kpi_target,
        "message": "KPI target updated"
    }



