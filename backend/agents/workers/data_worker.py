"""
Data Worker

Fetches and validates data from existing Gitto services.
Provides the raw data needed for FP&A workflows.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

import models
from ..models.briefings import CashMovement, CashPosition, ExpectedMovement, MovementType

logger = logging.getLogger(__name__)


class DataWorker:
    """
    Fetches and validates data from existing Gitto services.
    
    This worker wraps access to:
    - Bank transactions
    - Invoices (AR)
    - Vendor bills (AP)
    - FX rates
    - Snapshots
    """
    
    def __init__(self, db: Session, entity_id: int):
        self.db = db
        self.entity_id = entity_id
    
    # =========================================================================
    # CASH POSITION
    # =========================================================================
    
    def get_cash_position(
        self,
        as_of: Optional[datetime] = None,
        account_id: Optional[int] = None,
    ) -> CashPosition:
        """
        Get current cash position with breakdown.
        
        Args:
            as_of: Point in time (default: now)
            account_id: Specific account (default: all accounts)
        
        Returns:
            CashPosition with current balance and breakdown
        """
        as_of = as_of or datetime.utcnow()
        
        # Get bank accounts
        accounts_query = self.db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == self.entity_id
        )
        if account_id:
            accounts_query = accounts_query.filter(models.BankAccount.id == account_id)
        accounts = accounts_query.all()
        
        if not accounts:
            # Return empty position
            return CashPosition(
                as_of=as_of,
                opening_balance=Decimal("0"),
                total_inflows=Decimal("0"),
                total_outflows=Decimal("0"),
                current_balance=Decimal("0"),
                expected_balance=Decimal("0"),
                variance_from_expected=Decimal("0"),
                currency="EUR",
            )
        
        # Calculate balances
        total_balance = Decimal("0")
        by_account = {}
        
        for account in accounts:
            # Get latest balance
            latest_txn = self.db.query(models.BankTransaction).filter(
                models.BankTransaction.bank_account_id == account.id,
                models.BankTransaction.transaction_date <= as_of,
            ).order_by(models.BankTransaction.transaction_date.desc()).first()
            
            balance = Decimal(str(account.current_balance or 0))
            total_balance += balance
            by_account[account.account_name] = balance
        
        # Get today's movements for opening balance calculation
        today_start = datetime.combine(as_of.date(), datetime.min.time())
        
        inflows = self.get_transactions_since(today_start, as_of, "inflow")
        outflows = self.get_transactions_since(today_start, as_of, "outflow")
        
        total_inflows = sum(m.amount for m in inflows)
        total_outflows = sum(m.amount for m in outflows)
        opening = total_balance - total_inflows + total_outflows
        
        # Get expected (from forecast if available)
        expected = self._get_expected_balance(as_of)
        
        return CashPosition(
            as_of=as_of,
            opening_balance=opening,
            total_inflows=total_inflows,
            total_outflows=total_outflows,
            current_balance=total_balance,
            expected_balance=expected,
            variance_from_expected=total_balance - expected,
            currency="EUR",  # TODO: Support multi-currency
            inflows=inflows,
            outflows=outflows,
            by_account=by_account,
        )
    
    def _get_expected_balance(self, as_of: datetime) -> Decimal:
        """Get expected balance from forecast"""
        # Try to get from latest forecast
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.entity_id == self.entity_id
        ).order_by(models.Snapshot.created_at.desc()).first()
        
        if not snapshot:
            return Decimal("0")
        
        # For now, use a simple calculation
        # In production, this would query the forecast service
        return Decimal(str(snapshot.forecast_total_amount or 0))
    
    # =========================================================================
    # TRANSACTIONS
    # =========================================================================
    
    def get_transactions_since(
        self,
        since: datetime,
        until: Optional[datetime] = None,
        direction: Optional[str] = None,  # "inflow" or "outflow"
    ) -> List[CashMovement]:
        """
        Get bank transactions within a time range.
        
        Args:
            since: Start of range
            until: End of range (default: now)
            direction: Filter by direction
        
        Returns:
            List of CashMovement objects
        """
        until = until or datetime.utcnow()
        
        query = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == self.entity_id,
            models.BankTransaction.transaction_date >= since,
            models.BankTransaction.transaction_date <= until,
        )
        
        if direction == "inflow":
            query = query.filter(models.BankTransaction.amount > 0)
        elif direction == "outflow":
            query = query.filter(models.BankTransaction.amount < 0)
        
        transactions = query.order_by(models.BankTransaction.transaction_date.desc()).all()
        
        movements = []
        for txn in transactions:
            amount = Decimal(str(txn.amount))
            movements.append(CashMovement(
                movement_type=MovementType.INFLOW if amount > 0 else MovementType.OUTFLOW,
                amount=abs(amount),
                currency=txn.currency or "EUR",
                description=txn.reference or txn.description or "",
                counterparty=txn.counterparty_name,
                transaction_id=txn.id,
                timestamp=txn.transaction_date,
            ))
        
        return movements
    
    def get_overnight_transactions(self, as_of: Optional[date] = None) -> Tuple[List[CashMovement], List[CashMovement]]:
        """
        Get overnight transactions (since previous business day close).
        
        Returns:
            Tuple of (inflows, outflows)
        """
        as_of = as_of or date.today()
        
        # Assume "overnight" is since 5pm previous business day
        # This is simplified - real implementation would use business calendar
        yesterday = as_of - timedelta(days=1)
        if yesterday.weekday() >= 5:  # Weekend
            yesterday = yesterday - timedelta(days=yesterday.weekday() - 4)
        
        overnight_start = datetime.combine(yesterday, datetime.min.time().replace(hour=17))
        overnight_end = datetime.combine(as_of, datetime.min.time().replace(hour=7))
        
        inflows = self.get_transactions_since(overnight_start, overnight_end, "inflow")
        outflows = self.get_transactions_since(overnight_start, overnight_end, "outflow")
        
        return inflows, outflows
    
    # =========================================================================
    # EXPECTED MOVEMENTS
    # =========================================================================
    
    def get_expected_inflows(
        self,
        for_date: Optional[date] = None,
        days_ahead: int = 1,
    ) -> List[ExpectedMovement]:
        """
        Get expected inflows (from AR invoices due).
        
        Args:
            for_date: Target date (default: today)
            days_ahead: How many days to look ahead
        
        Returns:
            List of expected inflow movements
        """
        for_date = for_date or date.today()
        end_date = for_date + timedelta(days=days_ahead)
        
        # Query invoices due in the date range
        invoices = self.db.query(models.Invoice).filter(
            models.Invoice.entity_id == self.entity_id,
            models.Invoice.due_date >= for_date,
            models.Invoice.due_date <= end_date,
            models.Invoice.status != 'paid',
        ).all()
        
        movements = []
        for inv in invoices:
            # Calculate probability based on historical payment behavior
            # This is simplified - real implementation would use payment probability model
            confidence = 0.8 if inv.days_overdue <= 0 else max(0.3, 0.8 - inv.days_overdue * 0.05)
            
            movements.append(ExpectedMovement(
                movement_type=MovementType.INFLOW,
                amount=Decimal(str(inv.amount)),
                currency=inv.currency or "EUR",
                description=f"Invoice {inv.invoice_number}",
                counterparty=inv.customer_name,
                expected_date=inv.due_date,
                invoice_id=inv.id,
                confidence=confidence,
            ))
        
        return movements
    
    def get_expected_outflows(
        self,
        for_date: Optional[date] = None,
        days_ahead: int = 1,
    ) -> List[ExpectedMovement]:
        """
        Get expected outflows (from AP bills due).
        
        Args:
            for_date: Target date (default: today)
            days_ahead: How many days to look ahead
        
        Returns:
            List of expected outflow movements
        """
        for_date = for_date or date.today()
        end_date = for_date + timedelta(days=days_ahead)
        
        # Query vendor bills due in the date range
        bills = self.db.query(models.VendorBill).filter(
            models.VendorBill.entity_id == self.entity_id,
            models.VendorBill.due_date >= for_date,
            models.VendorBill.due_date <= end_date,
            models.VendorBill.status != 'paid',
        ).all()
        
        movements = []
        for bill in bills:
            movements.append(ExpectedMovement(
                movement_type=MovementType.OUTFLOW,
                amount=Decimal(str(bill.amount)),
                currency=bill.currency or "EUR",
                description=f"Bill {bill.bill_number}",
                counterparty=bill.vendor_name,
                expected_date=bill.due_date,
                bill_id=bill.id,
                confidence=0.95,  # Bills are usually paid as scheduled
            ))
        
        return movements
    
    # =========================================================================
    # DATA COMPLETENESS
    # =========================================================================
    
    def check_data_completeness(self, period: str = "today") -> Dict[str, Any]:
        """
        Check if data is complete for a period.
        
        Args:
            period: "today", "week", "month", or specific date
        
        Returns:
            Completeness report
        """
        today = date.today()
        
        if period == "today":
            start_date = today
            end_date = today
        elif period == "week":
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == "month":
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = datetime.strptime(period, "%Y-%m-%d").date()
            end_date = start_date
        
        # Check bank feeds
        bank_accounts = self.db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == self.entity_id
        ).all()
        
        bank_feed_status = []
        for account in bank_accounts:
            latest = self.db.query(func.max(models.BankTransaction.transaction_date)).filter(
                models.BankTransaction.bank_account_id == account.id
            ).scalar()
            
            bank_feed_status.append({
                "account": account.account_name,
                "last_transaction": latest.isoformat() if latest else None,
                "is_current": latest and latest.date() >= start_date if latest else False,
            })
        
        # Check AR/AP
        ar_count = self.db.query(func.count(models.Invoice.id)).filter(
            models.Invoice.entity_id == self.entity_id,
            models.Invoice.created_at >= datetime.combine(start_date, datetime.min.time()),
        ).scalar()
        
        ap_count = self.db.query(func.count(models.VendorBill.id)).filter(
            models.VendorBill.entity_id == self.entity_id,
            models.VendorBill.created_at >= datetime.combine(start_date, datetime.min.time()),
        ).scalar()
        
        return {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "bank_feeds": bank_feed_status,
            "all_bank_feeds_current": all(b["is_current"] for b in bank_feed_status),
            "ar_records": ar_count,
            "ap_records": ap_count,
            "is_complete": all(b["is_current"] for b in bank_feed_status),
        }
    
    def get_data_freshness(self) -> Dict[str, Any]:
        """Get data freshness metrics"""
        now = datetime.utcnow()
        
        # Bank data freshness
        latest_bank_txn = self.db.query(func.max(models.BankTransaction.transaction_date)).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == self.entity_id
        ).scalar()
        
        bank_hours_old = (
            (now - latest_bank_txn).total_seconds() / 3600
            if latest_bank_txn else None
        )
        
        # ERP data freshness (invoices/bills)
        latest_invoice = self.db.query(func.max(models.Invoice.created_at)).filter(
            models.Invoice.entity_id == self.entity_id
        ).scalar()
        
        erp_hours_old = (
            (now - latest_invoice).total_seconds() / 3600
            if latest_invoice else None
        )
        
        return {
            "bank_latest": latest_bank_txn.isoformat() if latest_bank_txn else None,
            "bank_hours_old": round(bank_hours_old, 1) if bank_hours_old else None,
            "erp_latest": latest_invoice.isoformat() if latest_invoice else None,
            "erp_hours_old": round(erp_hours_old, 1) if erp_hours_old else None,
            "freshness_mismatch_hours": abs((bank_hours_old or 0) - (erp_hours_old or 0)),
        }
    
    # =========================================================================
    # SNAPSHOT DATA
    # =========================================================================
    
    def get_latest_snapshot(self) -> Optional[models.Snapshot]:
        """Get the latest snapshot for this entity"""
        return self.db.query(models.Snapshot).filter(
            models.Snapshot.entity_id == self.entity_id
        ).order_by(models.Snapshot.created_at.desc()).first()
    
    def get_snapshot(self, snapshot_id: int) -> Optional[models.Snapshot]:
        """Get a specific snapshot"""
        return self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id,
            models.Snapshot.entity_id == self.entity_id,
        ).first()
