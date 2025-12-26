import models
from sqlalchemy.orm import Session
from bank_service import generate_cash_variance_narrative
from treasury_service import get_treasury_recommendations
from utils import predict_dispute_risk
from datetime import datetime

def generate_weekly_cash_pack(db: Session, snapshot_id: int, entity_id: int):
    # 1. KPIs
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    open_total = sum(inv.amount for inv in invoices if inv.payment_date is None)
    
    # 2. Variance Narrative
    variance = generate_cash_variance_narrative(db, entity_id, snapshot_id)
    
    # 3. Top Risks
    dispute_risks = predict_dispute_risk(db, snapshot_id)[:5]
    
    # 4. Recommended Actions
    actions = get_treasury_recommendations(db, snapshot_id)[:3]
    
    return {
        "report_date": datetime.now().isoformat(),
        "entity_id": entity_id,
        "executive_summary": f"Group cash position remains stable. Open receivables total €{open_total:,.0f}.",
        "variance_summary": variance,
        "top_blockage_risks": dispute_risks,
        "priority_actions": actions,
        "approval_status": "pending_cfo_signoff"
    }

class ReportingService:
    @staticmethod
    def sign_off_report(db: Session, report_id: int, user: str):
        # In a real app, we'd have a reports table
        # For MVP, we'll just return a success message
        return {"status": "signed_off", "by": user, "at": datetime.now().isoformat()}




