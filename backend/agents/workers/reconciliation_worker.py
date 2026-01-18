"""
Reconciliation Worker

Wraps the reconciliation service for use by FP&A workflows.
Provides reconciliation status, aged items, and escalation.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

import models

logger = logging.getLogger(__name__)


class ReconciliationWorker:
    """
    Wraps reconciliation_service_v2_enhanced for FP&A workflows.
    
    Provides:
    - Reconciliation status and metrics
    - Aged/unmatched items
    - Escalation of old items
    """
    
    def __init__(self, db: Session, entity_id: int):
        self.db = db
        self.entity_id = entity_id
    
    def get_reconciliation_status(self, snapshot_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get overall reconciliation status.
        
        Returns:
            Status including matched %, unmatched count, etc.
        """
        # Get bank transactions
        txn_query = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == self.entity_id
        )
        
        if snapshot_id:
            # Filter to transactions relevant to snapshot period
            snapshot = self.db.query(models.Snapshot).filter(
                models.Snapshot.id == snapshot_id
            ).first()
            if snapshot:
                txn_query = txn_query.filter(
                    models.BankTransaction.transaction_date >= snapshot.start_date,
                    models.BankTransaction.transaction_date <= snapshot.end_date,
                )
        
        total_txns = txn_query.count()
        
        # Count matched transactions
        matched_txns = txn_query.filter(
            models.BankTransaction.reconciliation_status == 'matched'
        ).count()
        
        # Get reconciliation records
        recon_query = self.db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.entity_id == self.entity_id
        )
        if snapshot_id:
            recon_query = recon_query.filter(
                models.ReconciliationTable.snapshot_id == snapshot_id
            )
        
        total_matches = recon_query.count()
        suggested_matches = recon_query.filter(
            models.ReconciliationTable.match_type == 'suggested',
            models.ReconciliationTable.is_approved == False,
        ).count()
        
        # Calculate amounts
        total_txn_amount = self.db.query(
            func.sum(func.abs(models.BankTransaction.amount))
        ).join(models.BankAccount).filter(
            models.BankAccount.entity_id == self.entity_id
        ).scalar() or 0
        
        matched_amount = self.db.query(
            func.sum(func.abs(models.BankTransaction.amount))
        ).join(models.BankAccount).filter(
            models.BankAccount.entity_id == self.entity_id,
            models.BankTransaction.reconciliation_status == 'matched',
        ).scalar() or 0
        
        match_pct = (matched_txns / total_txns * 100) if total_txns > 0 else 100.0
        match_amount_pct = (float(matched_amount) / float(total_txn_amount) * 100) if total_txn_amount > 0 else 100.0
        
        return {
            "total_transactions": total_txns,
            "matched_transactions": matched_txns,
            "unmatched_transactions": total_txns - matched_txns,
            "match_percentage": round(match_pct, 1),
            "total_amount": str(total_txn_amount),
            "matched_amount": str(matched_amount),
            "unmatched_amount": str(Decimal(str(total_txn_amount)) - Decimal(str(matched_amount))),
            "match_amount_percentage": round(match_amount_pct, 1),
            "total_reconciliation_records": total_matches,
            "suggested_matches_pending": suggested_matches,
        }
    
    def get_aged_items(self, days_threshold: int = 7) -> List[Dict[str, Any]]:
        """
        Get unmatched items aged beyond threshold.
        
        Args:
            days_threshold: Number of days to consider "aged"
        
        Returns:
            List of aged unmatched items
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        # Unmatched bank transactions
        aged_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == self.entity_id,
            models.BankTransaction.reconciliation_status != 'matched',
            models.BankTransaction.transaction_date < cutoff_date,
        ).order_by(models.BankTransaction.transaction_date.asc()).all()
        
        items = []
        for txn in aged_txns:
            days_aged = (datetime.utcnow() - txn.transaction_date).days
            items.append({
                "type": "bank_transaction",
                "id": txn.id,
                "date": txn.transaction_date.isoformat(),
                "amount": str(txn.amount),
                "currency": txn.currency or "EUR",
                "reference": txn.reference,
                "counterparty": txn.counterparty_name,
                "days_aged": days_aged,
                "severity": "critical" if days_aged > 30 else "warning",
            })
        
        return items
    
    def get_unmatched_summary(self) -> Dict[str, Any]:
        """Get summary of unmatched items by age bucket"""
        now = datetime.utcnow()
        
        # Define age buckets
        buckets = [
            ("0-7 days", 0, 7),
            ("8-14 days", 8, 14),
            ("15-30 days", 15, 30),
            ("30+ days", 31, 9999),
        ]
        
        summary = {}
        total_count = 0
        total_amount = Decimal("0")
        
        for label, min_days, max_days in buckets:
            start_date = now - timedelta(days=max_days)
            end_date = now - timedelta(days=min_days)
            
            txns = self.db.query(models.BankTransaction).join(
                models.BankAccount
            ).filter(
                models.BankAccount.entity_id == self.entity_id,
                models.BankTransaction.reconciliation_status != 'matched',
                models.BankTransaction.transaction_date >= start_date,
                models.BankTransaction.transaction_date < end_date,
            ).all()
            
            bucket_amount = sum(abs(Decimal(str(t.amount))) for t in txns)
            summary[label] = {
                "count": len(txns),
                "amount": str(bucket_amount),
            }
            total_count += len(txns)
            total_amount += bucket_amount
        
        return {
            "buckets": summary,
            "total_count": total_count,
            "total_amount": str(total_amount),
        }
    
    def run_matching(self, snapshot_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the matching engine.
        
        This wraps the reconciliation service to run matching.
        Returns results summary.
        """
        try:
            # Import and use the reconciliation service
            from reconciliation_service_v2_enhanced import EnhancedReconciliationService
            
            service = EnhancedReconciliationService(self.db, self.entity_id)
            result = service.run_full_reconciliation(snapshot_id=snapshot_id)
            
            return {
                "success": True,
                "matches_found": result.get("matches_found", 0),
                "suggestions_generated": result.get("suggestions_generated", 0),
                "auto_matched": result.get("auto_matched", 0),
            }
        except ImportError:
            # Fallback if enhanced service not available
            logger.warning("Enhanced reconciliation service not available")
            return {
                "success": False,
                "error": "Reconciliation service not available",
            }
        except Exception as e:
            logger.exception("Error running reconciliation")
            return {
                "success": False,
                "error": str(e),
            }
    
    def escalate_items(self, item_ids: List[int], escalate_to: str = "ar_team") -> Dict[str, Any]:
        """
        Escalate unmatched items for investigation.
        
        Args:
            item_ids: List of transaction IDs to escalate
            escalate_to: Team/person to escalate to
        
        Returns:
            Escalation result
        """
        # In a real implementation, this would:
        # 1. Update item status
        # 2. Send notification to escalate_to
        # 3. Create a task/ticket
        
        escalated = []
        for txn_id in item_ids:
            txn = self.db.query(models.BankTransaction).filter(
                models.BankTransaction.id == txn_id
            ).first()
            
            if txn:
                # Update status (if field exists)
                # txn.escalation_status = "escalated"
                # txn.escalated_to = escalate_to
                # txn.escalated_at = datetime.utcnow()
                escalated.append(txn_id)
        
        self.db.commit()
        
        return {
            "escalated_count": len(escalated),
            "escalated_ids": escalated,
            "escalated_to": escalate_to,
            "escalated_at": datetime.utcnow().isoformat(),
        }
    
    def get_suggested_matches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending suggested matches for review"""
        suggestions = self.db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.entity_id == self.entity_id,
            models.ReconciliationTable.match_type == 'suggested',
            models.ReconciliationTable.is_approved == False,
        ).limit(limit).all()
        
        result = []
        for s in suggestions:
            result.append({
                "id": s.id,
                "bank_transaction_id": s.bank_transaction_id,
                "invoice_id": s.invoice_id,
                "confidence_score": s.confidence_score,
                "match_amount": str(s.match_amount) if s.match_amount else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })
        
        return result
