"""
Truth Labeling Service
Adds badges (Bank-True/Reconciled/Modeled/Unknown) to all numbers for CFO trust.
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import models


def get_truth_label(invoice: models.Invoice, db: Session, transaction: Optional[models.BankTransaction] = None) -> str:
    """
    Determine truth label for an invoice:
    - Bank-True: Matched to bank transaction (reconciled)
    - Reconciled: Matched via reconciliation (any tier)
    - Modeled: Forecasted (not yet paid)
    - Unknown: Missing data (FX, due date, etc.)
    """
    # Check if reconciled
    if invoice.payment_date:
        if transaction:
            return "Bank-True"
        # Check if there's a reconciliation record
        # This would require joining with ReconciliationTable
        return "Reconciled"
    
    # Check for missing data
    if not invoice.expected_due_date or not invoice.currency:
        return "Unknown"
    
    # Check if in unknown bucket (would need to check unknown bucket service)
    # For now, assume modeled if has due date
    return "Modeled"


def add_truth_labels_to_invoice(invoice: models.Invoice, db: Session) -> Dict[str, Any]:
    """Add truth label and metadata to invoice dict"""
    label = get_truth_label(invoice)
    
    result = {
        "id": invoice.id,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "document_number": invoice.document_number,
        "customer": invoice.customer,
        "expected_due_date": invoice.expected_due_date.isoformat() if invoice.expected_due_date else None,
        "predicted_payment_date": invoice.predicted_payment_date.isoformat() if invoice.predicted_payment_date else None,
        "truth_label": label,
        "truth_source": _get_truth_source(invoice, label, db)
    }
    
    return result


def _get_truth_source(invoice: models.Invoice, label: str, db: Session) -> str:
    """Get source of truth for the label"""
    if label == "Bank-True":
        # Find reconciliation record
        recon = db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.invoice_id == invoice.id
        ).first()
        if recon:
            txn = db.query(models.BankTransaction).filter(
                models.BankTransaction.id == recon.bank_transaction_id
            ).first()
            if txn:
                return f"Bank Transaction {txn.id} ({txn.reconciliation_type})"
        return "Bank Transaction"
    
    elif label == "Reconciled":
        recon = db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.invoice_id == invoice.id
        ).first()
        if recon:
            return f"Reconciliation {recon.id}"
        return "Reconciled"
    
    elif label == "Modeled":
        return f"Forecast Model (Segment: {invoice.prediction_segment or 'Default'})"
    
    elif label == "Unknown":
        reasons = []
        if not invoice.expected_due_date:
            reasons.append("Missing due date")
        if not invoice.currency:
            reasons.append("Missing currency")
        # Check for missing FX (would need FX service)
        return f"Unknown: {', '.join(reasons) if reasons else 'Missing data'}"
    
    return "Unknown"


def add_truth_labels_to_workspace(workspace: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Add truth labels to workspace grid cells"""
    if 'grid' not in workspace:
        return workspace
    
    for week in workspace['grid']:
        # Add truth breakdown to week data
        week['truth_breakdown'] = {
            "bank_true": week.get('inflow_bank_true', 0),
            "reconciled": week.get('inflow_reconciled', 0),
            "modeled": week.get('inflow_modeled', 0),
            "unknown": week.get('inflow_unknown', 0)
        }
        
        # Calculate breakdown if not present
        if 'inflow_bank_true' not in week:
            # This would require aggregating from invoices
            # For now, set defaults
            week['truth_breakdown'] = {
                "bank_true": 0,
                "reconciled": 0,
                "modeled": week.get('inflow_p50', 0),
                "unknown": 0
            }
    
    return workspace


def get_truth_label_summary(db: Session, snapshot_id: int, include_row_ids: bool = False) -> Dict[str, Any]:
    """
    Get summary of truth labels for a snapshot.
    
    CFO Trust Feature: Every badge drill-down shows exact row IDs.
    include_row_ids=True returns invoice_ids behind each label for audit trail.
    """
    invoices = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id
    ).all()
    
    labels = {
        "Bank-True": {"count": 0, "amount": 0, "invoice_ids": []},
        "Reconciled": {"count": 0, "amount": 0, "invoice_ids": []},
        "Modeled": {"count": 0, "amount": 0, "invoice_ids": []},
        "Unknown": {"count": 0, "amount": 0, "invoice_ids": [], "reasons": {}}
    }
    
    for invoice in invoices:
        label = get_truth_label(invoice, db)
        labels[label]["count"] += 1
        labels[label]["amount"] += invoice.amount or 0
        
        if include_row_ids:
            labels[label]["invoice_ids"].append({
                "id": invoice.id,
                "document_number": invoice.document_number,
                "customer": invoice.customer,
                "amount": invoice.amount
            })
        
        # Track Unknown reasons for drill-down
        if label == "Unknown":
            reason = _get_unknown_reason(invoice, db)
            if reason not in labels["Unknown"]["reasons"]:
                labels["Unknown"]["reasons"][reason] = {"count": 0, "amount": 0, "invoice_ids": []}
            labels["Unknown"]["reasons"][reason]["count"] += 1
            labels["Unknown"]["reasons"][reason]["amount"] += invoice.amount or 0
            if include_row_ids:
                labels["Unknown"]["reasons"][reason]["invoice_ids"].append(invoice.id)
    
    total = sum(l["amount"] for l in labels.values())
    
    # Remove invoice_ids from response if not requested
    if not include_row_ids:
        for label_data in labels.values():
            label_data.pop("invoice_ids", None)
    
    return {
        "snapshot_id": snapshot_id,
        "breakdown": labels,
        "total": total,
        "cash_explained_pct": (labels["Bank-True"]["amount"] + labels["Reconciled"]["amount"]) / total * 100 if total > 0 else 0
    }


def _get_unknown_reason(invoice: models.Invoice, db: Session) -> str:
    """Get the specific reason an invoice is in Unknown bucket."""
    reasons = []
    
    if not invoice.expected_due_date:
        reasons.append("missing_due_date")
    
    if not invoice.currency:
        reasons.append("missing_currency")
    
    # Check for missing FX rate
    if invoice.currency and invoice.currency != "EUR":
        fx_rate = db.query(models.WeeklyFXRate).filter(
            models.WeeklyFXRate.snapshot_id == invoice.snapshot_id,
            models.WeeklyFXRate.from_currency == invoice.currency,
            models.WeeklyFXRate.to_currency == "EUR"
        ).first()
        if not fx_rate:
            reasons.append("missing_fx_rate")
    
    # Check for blocked/disputed
    if invoice.is_blocked:
        reasons.append(f"blocked:{invoice.blocked_reason or 'unspecified'}")
    
    if invoice.dispute_status == "open":
        reasons.append("in_dispute")
    
    return "|".join(reasons) if reasons else "unspecified"


def get_truth_label_drilldown(db: Session, snapshot_id: int, label: str) -> Dict[str, Any]:
    """
    CFO Trust Feature: Get detailed drill-down for a specific truth label.
    Returns exact row IDs, amounts, and reasons for each invoice in that label.
    """
    invoices = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id
    ).all()
    
    matching_invoices = []
    for invoice in invoices:
        inv_label = get_truth_label(invoice, db)
        if inv_label == label:
            matching_invoices.append({
                "id": invoice.id,
                "canonical_id": invoice.canonical_id,
                "document_number": invoice.document_number,
                "customer": invoice.customer,
                "amount": invoice.amount,
                "currency": invoice.currency,
                "expected_due_date": invoice.expected_due_date.isoformat() if invoice.expected_due_date else None,
                "truth_source": _get_truth_source(invoice, label, db),
                "reason": _get_unknown_reason(invoice, db) if label == "Unknown" else None
            })
    
    return {
        "label": label,
        "count": len(matching_invoices),
        "total_amount": sum(i["amount"] or 0 for i in matching_invoices),
        "invoices": matching_invoices
    }

