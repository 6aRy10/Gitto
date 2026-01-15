from sqlalchemy.orm import Session
import models
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

def simulate_revolver_draw(current_cash: float, min_threshold: float, revolver_limit: float, interest_rate_annual: float):
    """
    Models the cost and impact of drawing on a revolving credit line.
    """
    shortfall = max(0, min_threshold - current_cash)
    draw_amount = min(shortfall, revolver_limit)
    
    # Weekly interest cost calculation
    weekly_rate = interest_rate_annual / 52
    interest_cost = draw_amount * weekly_rate
    
    return {
        "shortfall": shortfall,
        "recommended_draw": draw_amount,
        "remaining_limit": revolver_limit - draw_amount,
        "weekly_interest_cost": interest_cost,
        "impact_on_cash": draw_amount - interest_cost
    }

def simulate_factoring_impact(invoices: List[models.Invoice], factoring_fee_pct: float, advance_rate_pct: float):
    """
    Models the immediate cash benefit vs cost of factoring specific invoices.
    """
    total_face_value = sum(inv.amount for inv in invoices)
    immediate_advance = total_face_value * advance_rate_pct
    total_fees = total_face_value * factoring_fee_pct
    
    return {
        "total_face_value": total_face_value,
        "immediate_liquidity_gain": immediate_advance,
        "total_cost_of_capital": total_fees,
        "net_proceeds": total_face_value - total_fees,
        "advance_rate": advance_rate_pct,
        "fee_pct": factoring_fee_pct
    }

def get_liquidity_action_plan(db: Session, snapshot_id: int):
    """
    Suggests treasury actions based on the 13-week forecast.
    """
    from cash_calendar_service import get_13_week_workspace
    workspace = get_13_week_workspace(db, snapshot_id)
    
    if not workspace: return []
    
    actions = []
    grid = workspace['grid']
    
    # Check for critical cash weeks
    critical_weeks = [w for w in grid if w['is_critical']]
    
    if critical_weeks:
        first_critical = critical_weeks[0]
        # 1. Suggest Revolver Draw
        actions.append({
            "type": "REVOLVER_DRAW",
            "priority": "HIGH",
            "week": first_critical['week_label'],
            "description": f"Cash projected to drop to {first_critical['closing_cash']:.2f} in {first_critical['week_label']}. Draw from credit facility recommended.",
            "suggestion_logic": simulate_revolver_draw(first_critical['closing_cash'], workspace['summary']['min_threshold'], 1000000, 0.08)
        })
        
        # 2. Suggest Factoring (Target largest upcoming invoices)
        large_invoices = db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot_id,
            models.Invoice.payment_date == None
        ).order_by(models.Invoice.amount.desc()).limit(5).all()
        
        if large_invoices:
            actions.append({
                "type": "FACTORING",
                "priority": "MEDIUM",
                "description": "Factor top 5 open invoices to pull forward liquidity.",
                "suggestion_logic": simulate_factoring_impact(large_invoices, 0.03, 0.85)
            })

    return actions

def get_or_create_lever_policy(db: Session, entity_id: int):
    """
    Get the lever policy for an entity, or create a default one.
    """
    policy = db.query(models.LeverPolicy).filter(models.LeverPolicy.entity_id == entity_id).first()
    
    if not policy:
        policy = models.LeverPolicy(
            entity_id=entity_id,
            max_vendor_delay_days=14,
            min_cash_threshold=0.0,
            approval_threshold=100000.0,
            protected_vendors=[]
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
    
    return policy

def validate_lever_action(db: Session, entity_id: int, action: Dict[str, Any]):
    """
    CFO Policy Guardrails for Liquidity Levers.
    Validates an action against entity-level policy rules.
    
    Action format: {
        "type": "delay_vendor" | "collections_push" | "financing",
        "vendor_name": str (optional),
        "delay_days": int (optional),
        "amount": float,
        "resulting_cash": float (optional)
    }
    
    Returns: {
        "valid": bool,
        "requires_approval": bool,
        "errors": [],
        "warnings": [],
        "policy": { ... }
    }
    """
    policy = get_or_create_lever_policy(db, entity_id)
    
    errors = []
    warnings = []
    requires_approval = False
    
    action_type = action.get("type", "")
    amount = action.get("amount", 0)
    vendor_name = action.get("vendor_name", "")
    delay_days = action.get("delay_days", 0)
    resulting_cash = action.get("resulting_cash")
    
    # Rule 1: Check max vendor delay days
    if action_type == "delay_vendor" and delay_days > 0:
        if delay_days > policy.max_vendor_delay_days:
            errors.append(f"Delay of {delay_days} days exceeds maximum allowed ({policy.max_vendor_delay_days} days)")
    
    # Rule 2: Check protected vendors
    protected = policy.protected_vendors or []
    if action_type == "delay_vendor" and vendor_name:
        if vendor_name.lower() in [v.lower() for v in protected]:
            errors.append(f"Vendor '{vendor_name}' is protected and cannot be delayed")
    
    # Rule 3: Check approval threshold
    if amount > policy.approval_threshold:
        requires_approval = True
        warnings.append(f"Action amount ({amount:,.0f}) exceeds approval threshold ({policy.approval_threshold:,.0f}). CFO approval required.")
    
    # Rule 4: Check minimum cash threshold
    if resulting_cash is not None and resulting_cash < policy.min_cash_threshold:
        errors.append(f"Action would result in cash ({resulting_cash:,.0f}) below minimum threshold ({policy.min_cash_threshold:,.0f})")
    
    return {
        "valid": len(errors) == 0,
        "requires_approval": requires_approval,
        "errors": errors,
        "warnings": warnings,
        "policy": {
            "max_vendor_delay_days": policy.max_vendor_delay_days,
            "min_cash_threshold": policy.min_cash_threshold,
            "approval_threshold": policy.approval_threshold,
            "protected_vendors": policy.protected_vendors or []
        }
    }

def get_lever_policy(db: Session, entity_id: int):
    """
    Get the current lever policy for an entity.
    """
    policy = get_or_create_lever_policy(db, entity_id)
    return {
        "id": policy.id,
        "entity_id": policy.entity_id,
        "max_vendor_delay_days": policy.max_vendor_delay_days,
        "min_cash_threshold": policy.min_cash_threshold,
        "approval_threshold": policy.approval_threshold,
        "protected_vendors": policy.protected_vendors or []
    }

def update_lever_policy(db: Session, entity_id: int, updates: Dict[str, Any]):
    """
    Update the lever policy for an entity.
    """
    policy = get_or_create_lever_policy(db, entity_id)
    
    if "max_vendor_delay_days" in updates:
        policy.max_vendor_delay_days = updates["max_vendor_delay_days"]
    if "min_cash_threshold" in updates:
        policy.min_cash_threshold = updates["min_cash_threshold"]
    if "approval_threshold" in updates:
        policy.approval_threshold = updates["approval_threshold"]
    if "protected_vendors" in updates:
        policy.protected_vendors = updates["protected_vendors"]
    
    db.commit()
    return get_lever_policy(db, entity_id)

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

def simulate_revolver_draw(current_cash: float, min_threshold: float, revolver_limit: float, interest_rate_annual: float):
    """
    Models the cost and impact of drawing on a revolving credit line.
    """
    shortfall = max(0, min_threshold - current_cash)
    draw_amount = min(shortfall, revolver_limit)
    
    # Weekly interest cost calculation
    weekly_rate = interest_rate_annual / 52
    interest_cost = draw_amount * weekly_rate
    
    return {
        "shortfall": shortfall,
        "recommended_draw": draw_amount,
        "remaining_limit": revolver_limit - draw_amount,
        "weekly_interest_cost": interest_cost,
        "impact_on_cash": draw_amount - interest_cost
    }

def simulate_factoring_impact(invoices: List[models.Invoice], factoring_fee_pct: float, advance_rate_pct: float):
    """
    Models the immediate cash benefit vs cost of factoring specific invoices.
    """
    total_face_value = sum(inv.amount for inv in invoices)
    immediate_advance = total_face_value * advance_rate_pct
    total_fees = total_face_value * factoring_fee_pct
    
    return {
        "total_face_value": total_face_value,
        "immediate_liquidity_gain": immediate_advance,
        "total_cost_of_capital": total_fees,
        "net_proceeds": total_face_value - total_fees,
        "advance_rate": advance_rate_pct,
        "fee_pct": factoring_fee_pct
    }

def get_liquidity_action_plan(db: Session, snapshot_id: int):
    """
    Suggests treasury actions based on the 13-week forecast.
    """
    from cash_calendar_service import get_13_week_workspace
    workspace = get_13_week_workspace(db, snapshot_id)
    
    if not workspace: return []
    
    actions = []
    grid = workspace['grid']
    
    # Check for critical cash weeks
    critical_weeks = [w for w in grid if w['is_critical']]
    
    if critical_weeks:
        first_critical = critical_weeks[0]
        # 1. Suggest Revolver Draw
        actions.append({
            "type": "REVOLVER_DRAW",
            "priority": "HIGH",
            "week": first_critical['week_label'],
            "description": f"Cash projected to drop to {first_critical['closing_cash']:.2f} in {first_critical['week_label']}. Draw from credit facility recommended.",
            "suggestion_logic": simulate_revolver_draw(first_critical['closing_cash'], workspace['summary']['min_threshold'], 1000000, 0.08)
        })
        
        # 2. Suggest Factoring (Target largest upcoming invoices)
        large_invoices = db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot_id,
            models.Invoice.payment_date == None
        ).order_by(models.Invoice.amount.desc()).limit(5).all()
        
        if large_invoices:
            actions.append({
                "type": "FACTORING",
                "priority": "MEDIUM",
                "description": "Factor top 5 open invoices to pull forward liquidity.",
                "suggestion_logic": simulate_factoring_impact(large_invoices, 0.03, 0.85)
            })

    return actions

def get_or_create_lever_policy(db: Session, entity_id: int):
    """
    Get the lever policy for an entity, or create a default one.
    """
    policy = db.query(models.LeverPolicy).filter(models.LeverPolicy.entity_id == entity_id).first()
    
    if not policy:
        policy = models.LeverPolicy(
            entity_id=entity_id,
            max_vendor_delay_days=14,
            min_cash_threshold=0.0,
            approval_threshold=100000.0,
            protected_vendors=[]
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
    
    return policy

def validate_lever_action(db: Session, entity_id: int, action: Dict[str, Any]):
    """
    CFO Policy Guardrails for Liquidity Levers.
    Validates an action against entity-level policy rules.
    
    Action format: {
        "type": "delay_vendor" | "collections_push" | "financing",
        "vendor_name": str (optional),
        "delay_days": int (optional),
        "amount": float,
        "resulting_cash": float (optional)
    }
    
    Returns: {
        "valid": bool,
        "requires_approval": bool,
        "errors": [],
        "warnings": [],
        "policy": { ... }
    }
    """
    policy = get_or_create_lever_policy(db, entity_id)
    
    errors = []
    warnings = []
    requires_approval = False
    
    action_type = action.get("type", "")
    amount = action.get("amount", 0)
    vendor_name = action.get("vendor_name", "")
    delay_days = action.get("delay_days", 0)
    resulting_cash = action.get("resulting_cash")
    
    # Rule 1: Check max vendor delay days
    if action_type == "delay_vendor" and delay_days > 0:
        if delay_days > policy.max_vendor_delay_days:
            errors.append(f"Delay of {delay_days} days exceeds maximum allowed ({policy.max_vendor_delay_days} days)")
    
    # Rule 2: Check protected vendors
    protected = policy.protected_vendors or []
    if action_type == "delay_vendor" and vendor_name:
        if vendor_name.lower() in [v.lower() for v in protected]:
            errors.append(f"Vendor '{vendor_name}' is protected and cannot be delayed")
    
    # Rule 3: Check approval threshold
    if amount > policy.approval_threshold:
        requires_approval = True
        warnings.append(f"Action amount ({amount:,.0f}) exceeds approval threshold ({policy.approval_threshold:,.0f}). CFO approval required.")
    
    # Rule 4: Check minimum cash threshold
    if resulting_cash is not None and resulting_cash < policy.min_cash_threshold:
        errors.append(f"Action would result in cash ({resulting_cash:,.0f}) below minimum threshold ({policy.min_cash_threshold:,.0f})")
    
    return {
        "valid": len(errors) == 0,
        "requires_approval": requires_approval,
        "errors": errors,
        "warnings": warnings,
        "policy": {
            "max_vendor_delay_days": policy.max_vendor_delay_days,
            "min_cash_threshold": policy.min_cash_threshold,
            "approval_threshold": policy.approval_threshold,
            "protected_vendors": policy.protected_vendors or []
        }
    }

def get_lever_policy(db: Session, entity_id: int):
    """
    Get the current lever policy for an entity.
    """
    policy = get_or_create_lever_policy(db, entity_id)
    return {
        "id": policy.id,
        "entity_id": policy.entity_id,
        "max_vendor_delay_days": policy.max_vendor_delay_days,
        "min_cash_threshold": policy.min_cash_threshold,
        "approval_threshold": policy.approval_threshold,
        "protected_vendors": policy.protected_vendors or []
    }

def update_lever_policy(db: Session, entity_id: int, updates: Dict[str, Any]):
    """
    Update the lever policy for an entity.
    """
    policy = get_or_create_lever_policy(db, entity_id)
    
    if "max_vendor_delay_days" in updates:
        policy.max_vendor_delay_days = updates["max_vendor_delay_days"]
    if "min_cash_threshold" in updates:
        policy.min_cash_threshold = updates["min_cash_threshold"]
    if "approval_threshold" in updates:
        policy.approval_threshold = updates["approval_threshold"]
    if "protected_vendors" in updates:
        policy.protected_vendors = updates["protected_vendors"]
    
    db.commit()
    return get_lever_policy(db, entity_id)
