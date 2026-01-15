import models
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, List

def calculate_realized_impact(db: Session, action_id: int):
    """
    Closes the loop between a treasury decision and bank reality.
    """
    action = db.query(models.TreasuryAction).filter(models.TreasuryAction.id == action_id).first()
    if not action or action.status == "Realized":
        return None

    # Logic depends on action type
    if action.action_type == "AP Hold":
        # Check if the target bill was actually delayed beyond the meeting week
        bill = db.query(models.VendorBill).filter(models.VendorBill.id == action.target_id).first()
        if bill and bill.hold_status == 1:
            action.realized_impact = action.expected_impact
            action.status = "Realized"
            
    elif action.action_type == "Collection Push":
        # Check if the target invoice was paid within the target week
        invoice = db.query(models.Invoice).filter(models.Invoice.id == action.target_id).first()
        if invoice and invoice.payment_date:
            # If it was paid, it's a realized impact
            action.realized_impact = action.expected_impact
            action.status = "Realized"

    db.commit()
    return action.realized_impact

def get_realized_summary(db: Session, snapshot_id: int):
    """
    Aggregates realized vs expected impact for the weekly cash meeting.
    """
    actions = db.query(models.TreasuryAction).filter(models.TreasuryAction.snapshot_id == snapshot_id).all()
    
    # Trigger a refresh of realized impact for all open actions
    for a in actions:
        if a.status != "Realized":
            calculate_realized_impact(db, a.id)
            
    expected = sum(a.expected_impact for a in actions)
    realized = sum(a.realized_impact or 0 for a in actions)
    
    return {
        "expected_impact": expected,
        "realized_impact": realized,
        "performance": (realized / expected) if expected > 0 else 0,
        "actions": actions
    }

def create_collection_action(db: Session, data: Dict[str, Any]):
    """
    Create a new collection action (call/email/escalate) for an invoice.
    """
    action = models.CollectionAction(
        invoice_id=data.get("invoice_id"),
        snapshot_id=data.get("snapshot_id"),
        action_type=data.get("action_type", "called"),
        expected_pullforward_days=data.get("expected_pullforward_days", 0),
        expected_pullforward_amount=data.get("expected_pullforward_amount", 0),
        owner=data.get("owner"),
        notes=data.get("notes")
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action

def update_collection_outcome(db: Session, action_id: int, outcome: str, outcome_amount: float = None):
    """
    Record the outcome of a collection action.
    outcome: "paid", "partial", "no_change"
    """
    action = db.query(models.CollectionAction).filter(models.CollectionAction.id == action_id).first()
    if not action:
        return None
    
    action.outcome = outcome
    action.outcome_date = datetime.now()
    action.outcome_amount = outcome_amount
    db.commit()
    
    return action

def get_collection_outcomes_summary(db: Session, snapshot_id: int):
    """
    CFO Trust Feature: Collections outcome tracking summary.
    Shows expected vs actual for the weekly meeting.
    
    Returns: {
        summary: { total_actions, outcomes_breakdown, expected_vs_actual },
        actions: [ ... ],
        performance_metrics: { hit_rate, avg_pullforward_achieved }
    }
    """
    # Get all collection actions for this snapshot
    actions = db.query(models.CollectionAction).filter(
        models.CollectionAction.snapshot_id == snapshot_id
    ).order_by(models.CollectionAction.created_at.desc()).all()
    
    # Also get actions from prior week that should be tracked
    one_week_ago = datetime.now() - timedelta(days=7)
    prior_actions = db.query(models.CollectionAction).filter(
        models.CollectionAction.created_at >= one_week_ago,
        models.CollectionAction.created_at < datetime.now() - timedelta(days=1),
        models.CollectionAction.outcome != None
    ).all()
    
    # Outcome breakdown
    outcomes_breakdown = {
        "paid": 0,
        "partial": 0,
        "no_change": 0,
        "pending": 0
    }
    
    total_expected_pullforward = 0.0
    total_actual_outcome = 0.0
    
    for action in actions:
        if action.outcome:
            outcomes_breakdown[action.outcome] = outcomes_breakdown.get(action.outcome, 0) + 1
            if action.outcome_amount:
                total_actual_outcome += action.outcome_amount
        else:
            outcomes_breakdown["pending"] += 1
        
        total_expected_pullforward += action.expected_pullforward_amount or 0
    
    # Calculate hit rate (% of actions that resulted in paid/partial)
    total_with_outcome = sum(1 for a in actions if a.outcome)
    positive_outcomes = outcomes_breakdown["paid"] + outcomes_breakdown["partial"]
    hit_rate = (positive_outcomes / total_with_outcome * 100) if total_with_outcome > 0 else 0.0
    
    # Calculate avg pullforward achieved
    avg_pullforward = 0.0
    if positive_outcomes > 0:
        realized_pullforwards = []
        for a in actions:
            if a.outcome in ["paid", "partial"] and a.invoice_id:
                inv = db.query(models.Invoice).filter(models.Invoice.id == a.invoice_id).first()
                if inv and inv.payment_date and inv.expected_due_date:
                    original_due = inv.expected_due_date
                    actual_payment = inv.payment_date
                    pullforward = (original_due - actual_payment).days
                    realized_pullforwards.append(pullforward)
        if realized_pullforwards:
            avg_pullforward = sum(realized_pullforwards) / len(realized_pullforwards)
    
    return {
        "summary": {
            "total_actions": len(actions),
            "outcomes_breakdown": outcomes_breakdown,
            "expected_pullforward_total": total_expected_pullforward,
            "actual_outcome_total": total_actual_outcome
        },
        "actions": [{
            "id": a.id,
            "invoice_id": a.invoice_id,
            "action_type": a.action_type,
            "expected_pullforward_days": a.expected_pullforward_days,
            "expected_pullforward_amount": a.expected_pullforward_amount,
            "outcome": a.outcome,
            "outcome_amount": a.outcome_amount,
            "outcome_date": a.outcome_date.isoformat() if a.outcome_date else None,
            "owner": a.owner,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in actions],
        "prior_week_outcomes": [{
            "id": a.id,
            "action_type": a.action_type,
            "outcome": a.outcome,
            "outcome_amount": a.outcome_amount,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in prior_actions],
        "performance_metrics": {
            "hit_rate": round(hit_rate, 1),
            "avg_pullforward_achieved": round(avg_pullforward, 1)
        }
    }

def get_collection_actions_for_invoice(db: Session, invoice_id: int):
    """
    Get all collection actions for a specific invoice.
    """
    actions = db.query(models.CollectionAction).filter(
        models.CollectionAction.invoice_id == invoice_id
    ).order_by(models.CollectionAction.created_at.desc()).all()
    
    return [{
        "id": a.id,
        "action_type": a.action_type,
        "expected_pullforward_days": a.expected_pullforward_days,
        "expected_pullforward_amount": a.expected_pullforward_amount,
        "outcome": a.outcome,
        "outcome_amount": a.outcome_amount,
        "outcome_date": a.outcome_date.isoformat() if a.outcome_date else None,
        "owner": a.owner,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None
    } for a in actions]


def create_collection_action(db: Session, data: Dict[str, Any]):
    """
    Create a new collection action (call/email/escalate) for an invoice.
    """
    action = models.CollectionAction(
        invoice_id=data.get("invoice_id"),
        snapshot_id=data.get("snapshot_id"),
        action_type=data.get("action_type", "called"),
        expected_pullforward_days=data.get("expected_pullforward_days", 0),
        expected_pullforward_amount=data.get("expected_pullforward_amount", 0),
        owner=data.get("owner"),
        notes=data.get("notes")
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action

def update_collection_outcome(db: Session, action_id: int, outcome: str, outcome_amount: float = None):
    """
    Record the outcome of a collection action.
    outcome: "paid", "partial", "no_change"
    """
    action = db.query(models.CollectionAction).filter(models.CollectionAction.id == action_id).first()
    if not action:
        return None
    
    action.outcome = outcome
    action.outcome_date = datetime.now()
    action.outcome_amount = outcome_amount
    db.commit()
    
    return action

def get_collection_outcomes_summary(db: Session, snapshot_id: int):
    """
    CFO Trust Feature: Collections outcome tracking summary.
    Shows expected vs actual for the weekly meeting.
    
    Returns: {
        summary: { total_actions, outcomes_breakdown, expected_vs_actual },
        actions: [ ... ],
        performance_metrics: { hit_rate, avg_pullforward_achieved }
    }
    """
    # Get all collection actions for this snapshot
    actions = db.query(models.CollectionAction).filter(
        models.CollectionAction.snapshot_id == snapshot_id
    ).order_by(models.CollectionAction.created_at.desc()).all()
    
    # Also get actions from prior week that should be tracked
    one_week_ago = datetime.now() - timedelta(days=7)
    prior_actions = db.query(models.CollectionAction).filter(
        models.CollectionAction.created_at >= one_week_ago,
        models.CollectionAction.created_at < datetime.now() - timedelta(days=1),
        models.CollectionAction.outcome != None
    ).all()
    
    # Outcome breakdown
    outcomes_breakdown = {
        "paid": 0,
        "partial": 0,
        "no_change": 0,
        "pending": 0
    }
    
    total_expected_pullforward = 0.0
    total_actual_outcome = 0.0
    
    for action in actions:
        if action.outcome:
            outcomes_breakdown[action.outcome] = outcomes_breakdown.get(action.outcome, 0) + 1
            if action.outcome_amount:
                total_actual_outcome += action.outcome_amount
        else:
            outcomes_breakdown["pending"] += 1
        
        total_expected_pullforward += action.expected_pullforward_amount or 0
    
    # Calculate hit rate (% of actions that resulted in paid/partial)
    total_with_outcome = sum(1 for a in actions if a.outcome)
    positive_outcomes = outcomes_breakdown["paid"] + outcomes_breakdown["partial"]
    hit_rate = (positive_outcomes / total_with_outcome * 100) if total_with_outcome > 0 else 0.0
    
    # Calculate avg pullforward achieved
    avg_pullforward = 0.0
    if positive_outcomes > 0:
        realized_pullforwards = []
        for a in actions:
            if a.outcome in ["paid", "partial"] and a.invoice_id:
                inv = db.query(models.Invoice).filter(models.Invoice.id == a.invoice_id).first()
                if inv and inv.payment_date and inv.expected_due_date:
                    original_due = inv.expected_due_date
                    actual_payment = inv.payment_date
                    pullforward = (original_due - actual_payment).days
                    realized_pullforwards.append(pullforward)
        if realized_pullforwards:
            avg_pullforward = sum(realized_pullforwards) / len(realized_pullforwards)
    
    return {
        "summary": {
            "total_actions": len(actions),
            "outcomes_breakdown": outcomes_breakdown,
            "expected_pullforward_total": total_expected_pullforward,
            "actual_outcome_total": total_actual_outcome
        },
        "actions": [{
            "id": a.id,
            "invoice_id": a.invoice_id,
            "action_type": a.action_type,
            "expected_pullforward_days": a.expected_pullforward_days,
            "expected_pullforward_amount": a.expected_pullforward_amount,
            "outcome": a.outcome,
            "outcome_amount": a.outcome_amount,
            "outcome_date": a.outcome_date.isoformat() if a.outcome_date else None,
            "owner": a.owner,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in actions],
        "prior_week_outcomes": [{
            "id": a.id,
            "action_type": a.action_type,
            "outcome": a.outcome,
            "outcome_amount": a.outcome_amount,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in prior_actions],
        "performance_metrics": {
            "hit_rate": round(hit_rate, 1),
            "avg_pullforward_achieved": round(avg_pullforward, 1)
        }
    }

def get_collection_actions_for_invoice(db: Session, invoice_id: int):
    """
    Get all collection actions for a specific invoice.
    """
    actions = db.query(models.CollectionAction).filter(
        models.CollectionAction.invoice_id == invoice_id
    ).order_by(models.CollectionAction.created_at.desc()).all()
    
    return [{
        "id": a.id,
        "action_type": a.action_type,
        "expected_pullforward_days": a.expected_pullforward_days,
        "expected_pullforward_amount": a.expected_pullforward_amount,
        "outcome": a.outcome,
        "outcome_amount": a.outcome_amount,
        "outcome_date": a.outcome_date.isoformat() if a.outcome_date else None,
        "owner": a.owner,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None
    } for a in actions]