import models
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime, timedelta

def get_treasury_recommendations(db: Session, snapshot_id: int):
    # Fetch top invoices landing in next 4 weeks
    today = datetime.now()
    four_weeks_later = today + timedelta(weeks=4)
    
    invoices = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.payment_date == None,
        models.Invoice.predicted_payment_date <= four_weeks_later
    ).all()
    
    recommendations = []
    
    for inv in invoices:
        # Action 1: Early-pay discount
        # Rule: If lateness risk > 10 days and amount > 10k
        lateness_risk = (pd.to_datetime(inv.confidence_p75) - pd.to_datetime(inv.predicted_payment_date)).days
        if lateness_risk > 10 and inv.amount > 10000:
            savings = inv.amount * 0.02 # 2% discount
            recommendations.append({
                "type": "early_pay_discount",
                "invoice": inv.document_number,
                "customer": inv.customer,
                "impact": f"Pull €{inv.amount:,.0f} forward by {lateness_risk} days",
                "cost": f"€{savings:,.0f} (2%)",
                "roi": lateness_risk / savings if savings > 0 else 0
            })
            
        # Action 2: Split Invoice
        # Rule: If amount > 100k, suggest split to reduce approval threshold
        if inv.amount > 100000:
            recommendations.append({
                "type": "split_invoice",
                "invoice": inv.document_number,
                "customer": inv.customer,
                "impact": "Reduce approval friction by splitting into €50k chunks",
                "cost": "Administrative time",
                "roi": 10.0 # High internal ROI
            })
            
    return sorted(recommendations, key=lambda x: x['roi'], reverse=True)

def simulate_financing(db: Session, snapshot_id: int, config: dict):
    # config: {"factoring_fee": 0.03, "credit_line_apr": 0.08, "draw_amount": 50000}
    draw_amount = config.get("draw_amount", 0)
    apr = config.get("credit_line_apr", 0.08)
    fee = config.get("factoring_fee", 0.03)
    
    # 1. Factoring math
    factoring_impact = draw_amount * (1 - fee)
    factoring_cost = draw_amount * fee
    
    # 2. Credit line math (assuming 30-day draw)
    credit_cost = (draw_amount * apr) / 12
    
    return {
        "factoring": {
            "net_cash_gained": factoring_impact,
            "total_cost": factoring_cost,
            "speed": "Immediate (24h)"
        },
        "credit_line": {
            "net_cash_gained": draw_amount,
            "total_cost": credit_cost,
            "speed": "Standard (3-5 days)"
        }
    }







