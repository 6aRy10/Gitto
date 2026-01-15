from sqlalchemy.orm import Session
import models
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

def generate_cash_variance_narrative(db: Session, current_snapshot_id: int, previous_snapshot_id: int):
    """
    CFO-Grade Variance Narrative:
    Explains the Delta between two 13-week forecasts by linking to root-cause events.
    """
    curr_invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == current_snapshot_id).all()
    prev_invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == previous_snapshot_id).all()
    
    curr_map = {inv.canonical_id: inv for inv in curr_invoices}
    prev_map = {inv.canonical_id: inv for inv in prev_invoices}
    
    narratives = []
    
    # 1. New Items (Leakage or Surprise)
    new_items_sum = sum(inv.amount for cid, inv in curr_map.items() if cid not in prev_map)
    if abs(new_items_sum) > 0:
        narratives.append({
            "category": "New Liquidity",
            "impact": new_items_sum,
            "narrative": f"Found {len([cid for cid in curr_map if cid not in prev_map])} new invoices totaling {new_items_sum:.2f}."
        })

    # 2. Timing & Behavior Shifts
    timing_impact = 0
    behavior_shifts = 0
    for cid, curr_inv in curr_map.items():
        if cid in prev_map:
            prev_inv = prev_map[cid]
            
            # Behavioral Shift (Segment stats changed)
            if curr_inv.prediction_segment != prev_inv.prediction_segment:
                behavior_shifts += 1
                
            # Timing Shift (Predicted Date changed)
            if curr_inv.predicted_payment_date != prev_inv.predicted_payment_date:
                # We calculate the impact by looking at whether it moved across week boundaries
                # For simplicity in MVP, we just note the shift
                timing_impact += curr_inv.amount
                
    if behavior_shifts > 0:
        narratives.append({
            "category": "Behavioral Regime Shift",
            "impact": 0, # Impact depends on the date shift
            "narrative": f"{behavior_shifts} items experienced a change in prediction segment due to updated N>=15 thresholds."
        })

    # 3. Reconciliation Shifts (Cash Recognized)
    # Check if items in previous were open but are now paid in current
    reconciled_sum = sum(prev_inv.amount for cid, prev_inv in prev_map.items() 
                         if prev_inv.payment_date is None and cid in curr_map and curr_map[cid].payment_date is not None)
    
    if reconciled_sum > 0:
        narratives.append({
            "category": "Cash Recognition",
            "impact": reconciled_sum,
            "narrative": f"Reconciled €{reconciled_sum:,.0f} of previously open AR against bank truth."
        })

    # 4. Structural Policy Variance (Payment Runs)
    # Check if entity payment run day changed (Policy shift)
    curr_snap = db.query(models.Snapshot).filter(models.Snapshot.id == current_snapshot_id).first()
    prev_snap = db.query(models.Snapshot).filter(models.Snapshot.id == previous_snapshot_id).first()
    
    if curr_snap and prev_snap and curr_snap.entity and prev_snap.entity:
        if curr_snap.entity.payment_run_day != prev_snap.entity.payment_run_day:
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            narratives.append({
                "category": "Structural Policy Shift",
                "impact": 0,
                "narrative": f"Entity shifted payment cycle from {days[prev_snap.entity.payment_run_day]} to {days[curr_snap.entity.payment_run_day]}, causing liquidity timing resets."
            })

    return narratives

def get_snapshot_comparison_matrix(db: Session, current_id: int, previous_id: int):
    """Returns a structured matrix of forecast variance by week."""
    from cash_calendar_service import get_13_week_workspace
    
    curr = get_13_week_workspace(db, current_id)
    prev = get_13_week_workspace(db, previous_id)
    
    if not curr or not prev: return []
    
    matrix = []
    prev_grid_map = {g['start_date']: g for g in prev['grid']}
    
    for c_week in curr['grid']:
        p_week = prev_grid_map.get(c_week['start_date'], {"closing_cash": 0, "inflow_p50": 0})
        
        matrix.append({
            "week": c_week['week_label'],
            "date": c_week['start_date'],
            "curr_inflow": c_week['inflow_p50'],
            "prev_inflow": p_week.get('inflow_p50', 0),
            "delta_inflow": c_week['inflow_p50'] - p_week.get('inflow_p50', 0),
            "curr_cash": c_week['closing_cash'],
            "prev_cash": p_week.get('closing_cash', 0),
            "delta_cash": c_week['closing_cash'] - p_week.get('closing_cash', 0)
        })
        
    return matrix

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

def generate_cash_variance_narrative(db: Session, current_snapshot_id: int, previous_snapshot_id: int):
    """
    CFO-Grade Variance Narrative:
    Explains the Delta between two 13-week forecasts by linking to root-cause events.
    """
    curr_invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == current_snapshot_id).all()
    prev_invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == previous_snapshot_id).all()
    
    curr_map = {inv.canonical_id: inv for inv in curr_invoices}
    prev_map = {inv.canonical_id: inv for inv in prev_invoices}
    
    narratives = []
    
    # 1. New Items (Leakage or Surprise)
    new_items_sum = sum(inv.amount for cid, inv in curr_map.items() if cid not in prev_map)
    if abs(new_items_sum) > 0:
        narratives.append({
            "category": "New Liquidity",
            "impact": new_items_sum,
            "narrative": f"Found {len([cid for cid in curr_map if cid not in prev_map])} new invoices totaling {new_items_sum:.2f}."
        })

    # 2. Timing & Behavior Shifts
    timing_impact = 0
    behavior_shifts = 0
    for cid, curr_inv in curr_map.items():
        if cid in prev_map:
            prev_inv = prev_map[cid]
            
            # Behavioral Shift (Segment stats changed)
            if curr_inv.prediction_segment != prev_inv.prediction_segment:
                behavior_shifts += 1
                
            # Timing Shift (Predicted Date changed)
            if curr_inv.predicted_payment_date != prev_inv.predicted_payment_date:
                # We calculate the impact by looking at whether it moved across week boundaries
                # For simplicity in MVP, we just note the shift
                timing_impact += curr_inv.amount
                
    if behavior_shifts > 0:
        narratives.append({
            "category": "Behavioral Regime Shift",
            "impact": 0, # Impact depends on the date shift
            "narrative": f"{behavior_shifts} items experienced a change in prediction segment due to updated N>=15 thresholds."
        })

    # 3. Reconciliation Shifts (Cash Recognized)
    # Check if items in previous were open but are now paid in current
    reconciled_sum = sum(prev_inv.amount for cid, prev_inv in prev_map.items() 
                         if prev_inv.payment_date is None and cid in curr_map and curr_map[cid].payment_date is not None)
    
    if reconciled_sum > 0:
        narratives.append({
            "category": "Cash Recognition",
            "impact": reconciled_sum,
            "narrative": f"Reconciled €{reconciled_sum:,.0f} of previously open AR against bank truth."
        })

    # 4. Structural Policy Variance (Payment Runs)
    # Check if entity payment run day changed (Policy shift)
    curr_snap = db.query(models.Snapshot).filter(models.Snapshot.id == current_snapshot_id).first()
    prev_snap = db.query(models.Snapshot).filter(models.Snapshot.id == previous_snapshot_id).first()
    
    if curr_snap and prev_snap and curr_snap.entity and prev_snap.entity:
        if curr_snap.entity.payment_run_day != prev_snap.entity.payment_run_day:
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            narratives.append({
                "category": "Structural Policy Shift",
                "impact": 0,
                "narrative": f"Entity shifted payment cycle from {days[prev_snap.entity.payment_run_day]} to {days[curr_snap.entity.payment_run_day]}, causing liquidity timing resets."
            })

    return narratives

def get_snapshot_comparison_matrix(db: Session, current_id: int, previous_id: int):
    """Returns a structured matrix of forecast variance by week."""
    from cash_calendar_service import get_13_week_workspace
    
    curr = get_13_week_workspace(db, current_id)
    prev = get_13_week_workspace(db, previous_id)
    
    if not curr or not prev: return []
    
    matrix = []
    prev_grid_map = {g['start_date']: g for g in prev['grid']}
    
    for c_week in curr['grid']:
        p_week = prev_grid_map.get(c_week['start_date'], {"closing_cash": 0, "inflow_p50": 0})
        
        matrix.append({
            "week": c_week['week_label'],
            "date": c_week['start_date'],
            "curr_inflow": c_week['inflow_p50'],
            "prev_inflow": p_week.get('inflow_p50', 0),
            "delta_inflow": c_week['inflow_p50'] - p_week.get('inflow_p50', 0),
            "curr_cash": c_week['closing_cash'],
            "prev_cash": p_week.get('closing_cash', 0),
            "delta_cash": c_week['closing_cash'] - p_week.get('closing_cash', 0)
        })
        
    return matrix
