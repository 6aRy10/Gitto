"""
Cash-to-Plan Bridge Service

Computes accrual-to-cash bridge explaining how revenue/COGS/opex translate
into bank movement via working capital timing (AR delay distributions + AP payment runs).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

import models
from cash_plan_bridge_models import (
    FPAPlan, PlanDriver, CashToPlanBridge, BridgeLine, WeeklyPlanOverlay,
    PlanStatus, DriverType, BridgeLineType, EvidenceType
)


class CashToPlanBridgeService:
    """
    Service for computing Cash-to-Plan bridges.
    
    Key responsibilities:
    1. Convert accrual-based plan to cash timing using working capital adjustments
    2. Compare plan cash flows to actual bank truth from snapshot
    3. Generate weekly overlay showing red weeks / constraint violations
    4. Link every bridge line to evidence (invoice IDs, bank txn IDs, bill IDs)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_bridge(
        self,
        plan_id: int,
        snapshot_id: int,
        base_currency: str = "EUR"
    ) -> CashToPlanBridge:
        """
        Generate a complete Cash-to-Plan bridge.
        
        Args:
            plan_id: ID of the FP&A plan
            snapshot_id: ID of the locked snapshot (bank truth)
            base_currency: Currency for the bridge
            
        Returns:
            CashToPlanBridge with all lines and weekly overlay
        """
        # Load plan and snapshot
        plan = self.db.query(FPAPlan).filter(FPAPlan.id == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        # Create bridge record
        bridge = CashToPlanBridge(
            plan_id=plan_id,
            snapshot_id=snapshot_id,
            name=f"Bridge: {plan.name} vs Snapshot {snapshot.name}",
            base_currency=base_currency,
            generated_at=datetime.utcnow()
        )
        self.db.add(bridge)
        self.db.flush()  # Get bridge ID
        
        # Load plan drivers
        drivers = self.db.query(PlanDriver).filter(
            PlanDriver.plan_id == plan_id
        ).all()
        
        # Load actual data from snapshot
        invoices = self._load_invoices(snapshot_id)
        vendor_bills = self._load_vendor_bills(snapshot_id)
        bank_transactions = self._load_bank_transactions(snapshot_id)
        reconciliation_data = self._load_reconciliation_data(snapshot_id)
        
        # Get plan assumptions
        assumptions = plan.assumptions_json or {}
        default_dso = assumptions.get("dso_days", 45)
        default_dpo = assumptions.get("dpo_days", 30)
        min_cash = Decimal(str(assumptions.get("min_cash_balance", 500000)))
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 1: COMPUTE ACCRUAL-TO-CASH BRIDGE FOR REVENUE
        # ═══════════════════════════════════════════════════════════════════════
        revenue_lines = self._compute_revenue_bridge(
            bridge, drivers, invoices, bank_transactions, 
            reconciliation_data, default_dso
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 2: COMPUTE ACCRUAL-TO-CASH BRIDGE FOR EXPENSES (COGS + OPEX)
        # ═══════════════════════════════════════════════════════════════════════
        expense_lines = self._compute_expense_bridge(
            bridge, drivers, vendor_bills, bank_transactions,
            reconciliation_data, default_dpo
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 3: COMPUTE WORKING CAPITAL ADJUSTMENTS
        # ═══════════════════════════════════════════════════════════════════════
        wc_lines = self._compute_working_capital_adjustments(
            bridge, invoices, vendor_bills, plan
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 4: HANDLE UNKNOWN/UNEXPLAINED ITEMS
        # ═══════════════════════════════════════════════════════════════════════
        unknown_lines = self._compute_unknown_items(
            bridge, bank_transactions, reconciliation_data
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 5: GENERATE WEEKLY OVERLAY
        # ═══════════════════════════════════════════════════════════════════════
        weekly_overlay = self._generate_weekly_overlay(
            bridge, plan, snapshot, min_cash
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 6: COMPUTE SUMMARY METRICS
        # ═══════════════════════════════════════════════════════════════════════
        self._compute_summary_metrics(bridge, weekly_overlay)
        
        # Generate bridge output JSON for rendering
        bridge.bridge_output_json = self._generate_bridge_output_json(bridge)
        bridge.weekly_overlay_json = [
            self._overlay_to_dict(w) for w in weekly_overlay
        ]
        
        self.db.commit()
        return bridge
    
    def _load_invoices(self, snapshot_id: int) -> List[models.Invoice]:
        """Load AR invoices from snapshot."""
        return self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot_id
        ).all()
    
    def _load_vendor_bills(self, snapshot_id: int) -> List:
        """Load AP vendor bills from snapshot."""
        # Check if VendorBill model exists
        if hasattr(models, 'VendorBill'):
            return self.db.query(models.VendorBill).filter(
                models.VendorBill.snapshot_id == snapshot_id
            ).all()
        return []
    
    def _load_bank_transactions(self, snapshot_id: int) -> List[models.BankTransaction]:
        """Load bank transactions from snapshot."""
        return self.db.query(models.BankTransaction).filter(
            models.BankTransaction.snapshot_id == snapshot_id
        ).all()
    
    def _load_reconciliation_data(self, snapshot_id: int) -> Dict[str, Any]:
        """Load reconciliation/matching data from snapshot."""
        matches = self.db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.snapshot_id == snapshot_id
        ).all()
        
        # Index by invoice_id and bank_txn_id for lookup
        by_invoice = defaultdict(list)
        by_bank_txn = defaultdict(list)
        
        for m in matches:
            if m.invoice_id:
                by_invoice[m.invoice_id].append(m)
            if m.bank_transaction_id:
                by_bank_txn[m.bank_transaction_id].append(m)
        
        return {
            "matches": matches,
            "by_invoice": dict(by_invoice),
            "by_bank_txn": dict(by_bank_txn)
        }
    
    def _compute_revenue_bridge(
        self,
        bridge: CashToPlanBridge,
        drivers: List[PlanDriver],
        invoices: List[models.Invoice],
        bank_transactions: List[models.BankTransaction],
        reconciliation_data: Dict,
        default_dso: int
    ) -> List[BridgeLine]:
        """
        Compute revenue-to-cash bridge:
        Revenue (accrual) → AR → Cash Collection
        
        Uses AR delay distributions from actual invoice payment history.
        """
        lines = []
        
        # Group revenue drivers by month
        revenue_drivers = [d for d in drivers if d.driver_type == DriverType.REVENUE]
        by_month = defaultdict(list)
        for d in revenue_drivers:
            by_month[d.period_month].append(d)
        
        # Group invoices by issue month
        invoices_by_month = defaultdict(list)
        for inv in invoices:
            if hasattr(inv, 'invoice_issue_date') and inv.invoice_issue_date:
                month_start = inv.invoice_issue_date.replace(day=1)
                invoices_by_month[month_start].append(inv)
        
        # For each month, create bridge lines
        for month, month_drivers in by_month.items():
            total_plan_revenue = sum(Decimal(str(d.amount_plan or 0)) for d in month_drivers)
            
            # Get actual invoices for this month
            month_invoices = invoices_by_month.get(month, [])
            actual_revenue = sum(
                Decimal(str(inv.invoice_total_amount or 0)) 
                for inv in month_invoices
            )
            
            # Create Revenue Accrual line
            revenue_line = BridgeLine(
                bridge_id=bridge.id,
                line_type=BridgeLineType.REVENUE_TO_AR,
                category="Revenue",
                description=f"Revenue accrual for {month.strftime('%B %Y')}",
                period_month=month,
                plan_amount=total_plan_revenue,
                actual_amount=actual_revenue,
                variance=actual_revenue - total_plan_revenue,
                currency=bridge.base_currency,
                amount_base=total_plan_revenue,
                has_evidence=len(month_invoices) > 0,
                evidence_type=EvidenceType.INVOICE if month_invoices else EvidenceType.NONE,
                evidence_refs_json=[
                    {
                        "type": "invoice",
                        "id": inv.id,
                        "doc_number": inv.invoice_number,
                        "amount": float(inv.invoice_total_amount or 0),
                        "customer": inv.customer_name
                    }
                    for inv in month_invoices[:50]  # Limit for performance
                ],
                invoice_count=len(month_invoices),
                is_unknown=len(month_invoices) == 0 and actual_revenue > 0,
                drilldown_available=True
            )
            self.db.add(revenue_line)
            lines.append(revenue_line)
            
            # Compute AR-to-Cash conversion using payment timing
            cash_collected = self._compute_ar_cash_collection(
                bridge, month, month_invoices, reconciliation_data, default_dso
            )
            lines.extend(cash_collected)
        
        return lines
    
    def _compute_ar_cash_collection(
        self,
        bridge: CashToPlanBridge,
        accrual_month: date,
        invoices: List[models.Invoice],
        reconciliation_data: Dict,
        default_dso: int
    ) -> List[BridgeLine]:
        """
        Compute when AR invoices convert to cash based on actual payment history.
        """
        lines = []
        
        # Group by collection timing
        collections_by_week = defaultdict(list)
        unexplained_collections = []
        
        for inv in invoices:
            # Check if invoice has been paid (via reconciliation)
            matches = reconciliation_data["by_invoice"].get(inv.id, [])
            
            if matches:
                for match in matches:
                    # Get the bank transaction
                    bank_txn_id = match.bank_transaction_id
                    if bank_txn_id:
                        bank_txn = self.db.query(models.BankTransaction).filter(
                            models.BankTransaction.id == bank_txn_id
                        ).first()
                        if bank_txn and bank_txn.transaction_date:
                            # Calculate which week this falls into
                            week_start = bank_txn.transaction_date - timedelta(
                                days=bank_txn.transaction_date.weekday()
                            )
                            collections_by_week[week_start].append({
                                "invoice": inv,
                                "bank_txn": bank_txn,
                                "match": match,
                                "amount": float(match.allocated_amount or inv.invoice_total_amount or 0)
                            })
            else:
                # Invoice not yet collected - add to unexplained
                if hasattr(inv, 'reconciliation_status') and inv.reconciliation_status != 'matched':
                    unexplained_collections.append(inv)
        
        # Create AR-to-Cash lines by week
        for week_start, collections in collections_by_week.items():
            total_collected = sum(c["amount"] for c in collections)
            
            line = BridgeLine(
                bridge_id=bridge.id,
                line_type=BridgeLineType.AR_TO_CASH,
                category="AR Collection",
                description=f"Cash collected from {accrual_month.strftime('%b')} invoices",
                period_month=accrual_month,
                period_week=week_start,
                plan_cash_amount=Decimal(str(total_collected)),  # Actual becomes plan cash timing
                actual_amount=Decimal(str(total_collected)),
                variance=Decimal("0"),
                currency=bridge.base_currency,
                amount_base=Decimal(str(total_collected)),
                timing_days=self._calculate_timing_days(accrual_month, week_start),
                has_evidence=True,
                evidence_type=EvidenceType.BANK_TXN,
                evidence_refs_json=[
                    {
                        "type": "bank_txn",
                        "id": c["bank_txn"].id,
                        "reference": c["bank_txn"].reference,
                        "amount": c["amount"],
                        "linked_invoice_id": c["invoice"].id,
                        "linked_invoice_number": c["invoice"].invoice_number
                    }
                    for c in collections[:50]
                ],
                invoice_count=len(set(c["invoice"].id for c in collections)),
                bank_txn_count=len(set(c["bank_txn"].id for c in collections)),
                drilldown_available=True
            )
            self.db.add(line)
            lines.append(line)
        
        return lines
    
    def _compute_expense_bridge(
        self,
        bridge: CashToPlanBridge,
        drivers: List[PlanDriver],
        vendor_bills: List,
        bank_transactions: List[models.BankTransaction],
        reconciliation_data: Dict,
        default_dpo: int
    ) -> List[BridgeLine]:
        """
        Compute expense-to-cash bridge:
        COGS/Opex (accrual) → AP → Cash Payment
        
        Uses AP payment run timing from actual vendor bill payments.
        """
        lines = []
        
        # Group expense drivers by month and type
        expense_drivers = [
            d for d in drivers 
            if d.driver_type in (DriverType.COGS, DriverType.OPEX, DriverType.CAPEX)
        ]
        
        by_month_type = defaultdict(list)
        for d in expense_drivers:
            key = (d.period_month, d.driver_type)
            by_month_type[key].append(d)
        
        # Process each month/type combination
        for (month, driver_type), month_drivers in by_month_type.items():
            total_plan_expense = sum(Decimal(str(d.amount_plan or 0)) for d in month_drivers)
            
            # Find actual outflows from bank transactions
            # Filter bank transactions for this month that are outflows
            month_start = month
            month_end = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            actual_outflows = [
                txn for txn in bank_transactions
                if txn.transaction_date and 
                   month_start <= txn.transaction_date < month_end and
                   (txn.transaction_amount or 0) < 0
            ]
            
            actual_expense = abs(sum(
                Decimal(str(txn.transaction_amount or 0))
                for txn in actual_outflows
            ))
            
            # Determine line type based on driver type
            line_type_map = {
                DriverType.COGS: BridgeLineType.COGS_TO_AP,
                DriverType.OPEX: BridgeLineType.OPEX_ACCRUAL,
                DriverType.CAPEX: BridgeLineType.CAPEX_CASH
            }
            
            # Create expense accrual line
            expense_line = BridgeLine(
                bridge_id=bridge.id,
                line_type=line_type_map.get(driver_type, BridgeLineType.OPEX_ACCRUAL),
                category=driver_type.value.upper(),
                description=f"{driver_type.value.title()} for {month.strftime('%B %Y')}",
                period_month=month,
                plan_amount=total_plan_expense,
                actual_amount=actual_expense,
                variance=actual_expense - total_plan_expense,
                currency=bridge.base_currency,
                amount_base=total_plan_expense,
                timing_days=default_dpo,
                has_evidence=len(actual_outflows) > 0,
                evidence_type=EvidenceType.BANK_TXN if actual_outflows else EvidenceType.NONE,
                evidence_refs_json=[
                    {
                        "type": "bank_txn",
                        "id": txn.id,
                        "reference": txn.reference,
                        "amount": float(txn.transaction_amount or 0),
                        "date": txn.transaction_date.isoformat() if txn.transaction_date else None
                    }
                    for txn in actual_outflows[:50]
                ],
                bank_txn_count=len(actual_outflows),
                is_unknown=len(actual_outflows) == 0 and actual_expense > 0,
                drilldown_available=True
            )
            self.db.add(expense_line)
            lines.append(expense_line)
        
        return lines
    
    def _compute_working_capital_adjustments(
        self,
        bridge: CashToPlanBridge,
        invoices: List[models.Invoice],
        vendor_bills: List,
        plan: FPAPlan
    ) -> List[BridgeLine]:
        """
        Compute working capital timing adjustments:
        - AR timing adjustment (revenue recognized but not yet collected)
        - AP timing adjustment (expense recognized but not yet paid)
        """
        lines = []
        
        # Calculate AR timing adjustment
        # Open AR = invoices issued but not yet collected
        open_ar = sum(
            Decimal(str(inv.open_amount or inv.invoice_total_amount or 0))
            for inv in invoices
            if hasattr(inv, 'reconciliation_status') and inv.reconciliation_status != 'matched'
        )
        
        if open_ar > 0:
            ar_line = BridgeLine(
                bridge_id=bridge.id,
                line_type=BridgeLineType.AR_TIMING_ADJUSTMENT,
                category="Working Capital",
                description="AR timing adjustment - revenue recognized, cash pending",
                plan_amount=Decimal("0"),
                actual_amount=-open_ar,  # Negative impact on cash
                variance=-open_ar,
                timing_adjustment=-open_ar,
                currency=bridge.base_currency,
                amount_base=-open_ar,
                has_evidence=True,
                evidence_type=EvidenceType.INVOICE,
                evidence_refs_json=[
                    {
                        "type": "invoice",
                        "id": inv.id,
                        "doc_number": inv.invoice_number,
                        "open_amount": float(inv.open_amount or inv.invoice_total_amount or 0)
                    }
                    for inv in invoices
                    if hasattr(inv, 'reconciliation_status') and inv.reconciliation_status != 'matched'
                ][:50],
                invoice_count=len([
                    inv for inv in invoices
                    if hasattr(inv, 'reconciliation_status') and inv.reconciliation_status != 'matched'
                ]),
                drilldown_available=True
            )
            self.db.add(ar_line)
            lines.append(ar_line)
            
            bridge.ar_change = -open_ar
        
        # Calculate AP timing adjustment (if vendor bills available)
        if vendor_bills:
            open_ap = sum(
                Decimal(str(getattr(bill, 'open_amount', 0) or getattr(bill, 'total_amount', 0) or 0))
                for bill in vendor_bills
                if hasattr(bill, 'status') and bill.status != 'paid'
            )
            
            if open_ap > 0:
                ap_line = BridgeLine(
                    bridge_id=bridge.id,
                    line_type=BridgeLineType.AP_TIMING_ADJUSTMENT,
                    category="Working Capital",
                    description="AP timing adjustment - expense recognized, cash preserved",
                    plan_amount=Decimal("0"),
                    actual_amount=open_ap,  # Positive - cash preserved
                    variance=open_ap,
                    timing_adjustment=open_ap,
                    currency=bridge.base_currency,
                    amount_base=open_ap,
                    has_evidence=True,
                    evidence_type=EvidenceType.VENDOR_BILL,
                    evidence_refs_json=[
                        {
                            "type": "vendor_bill",
                            "id": bill.id,
                            "doc_number": getattr(bill, 'bill_number', 'N/A'),
                            "open_amount": float(getattr(bill, 'open_amount', 0) or 0)
                        }
                        for bill in vendor_bills
                        if hasattr(bill, 'status') and bill.status != 'paid'
                    ][:50],
                    vendor_bill_count=len([
                        bill for bill in vendor_bills
                        if hasattr(bill, 'status') and bill.status != 'paid'
                    ]),
                    drilldown_available=True
                )
                self.db.add(ap_line)
                lines.append(ap_line)
                
                bridge.ap_change = open_ap
        
        return lines
    
    def _compute_unknown_items(
        self,
        bridge: CashToPlanBridge,
        bank_transactions: List[models.BankTransaction],
        reconciliation_data: Dict
    ) -> List[BridgeLine]:
        """
        Identify and mark unknown/unexplained items.
        These are bank transactions not linked to any AR/AP.
        """
        lines = []
        
        # Find unmatched bank transactions
        matched_txn_ids = set(reconciliation_data["by_bank_txn"].keys())
        unmatched_txns = [
            txn for txn in bank_transactions
            if txn.id not in matched_txn_ids
        ]
        
        # Separate inflows and outflows
        unknown_inflows = [t for t in unmatched_txns if (t.transaction_amount or 0) > 0]
        unknown_outflows = [t for t in unmatched_txns if (t.transaction_amount or 0) < 0]
        
        if unknown_inflows:
            total_unknown_in = sum(Decimal(str(t.transaction_amount or 0)) for t in unknown_inflows)
            
            line = BridgeLine(
                bridge_id=bridge.id,
                line_type=BridgeLineType.UNKNOWN,
                category="Unknown Inflows",
                description="Bank inflows not linked to AR invoices",
                plan_amount=Decimal("0"),
                actual_amount=total_unknown_in,
                variance=total_unknown_in,
                currency=bridge.base_currency,
                amount_base=total_unknown_in,
                has_evidence=True,  # We have the txns, just not matched
                evidence_type=EvidenceType.BANK_TXN,
                evidence_refs_json=[
                    {
                        "type": "bank_txn",
                        "id": t.id,
                        "reference": t.reference,
                        "amount": float(t.transaction_amount or 0),
                        "date": t.transaction_date.isoformat() if t.transaction_date else None,
                        "status": "unmatched"
                    }
                    for t in unknown_inflows[:50]
                ],
                bank_txn_count=len(unknown_inflows),
                is_unknown=True,
                unknown_reason="Bank transactions not matched to AR invoices",
                drilldown_available=True
            )
            self.db.add(line)
            lines.append(line)
            
            bridge.unknown_inflows = total_unknown_in
        
        if unknown_outflows:
            total_unknown_out = abs(sum(Decimal(str(t.transaction_amount or 0)) for t in unknown_outflows))
            
            line = BridgeLine(
                bridge_id=bridge.id,
                line_type=BridgeLineType.UNKNOWN,
                category="Unknown Outflows",
                description="Bank outflows not linked to AP bills",
                plan_amount=Decimal("0"),
                actual_amount=-total_unknown_out,
                variance=-total_unknown_out,
                currency=bridge.base_currency,
                amount_base=-total_unknown_out,
                has_evidence=True,
                evidence_type=EvidenceType.BANK_TXN,
                evidence_refs_json=[
                    {
                        "type": "bank_txn",
                        "id": t.id,
                        "reference": t.reference,
                        "amount": float(t.transaction_amount or 0),
                        "date": t.transaction_date.isoformat() if t.transaction_date else None,
                        "status": "unmatched"
                    }
                    for t in unknown_outflows[:50]
                ],
                bank_txn_count=len(unknown_outflows),
                is_unknown=True,
                unknown_reason="Bank transactions not matched to AP bills",
                drilldown_available=True
            )
            self.db.add(line)
            lines.append(line)
            
            bridge.unknown_outflows = total_unknown_out
        
        return lines
    
    def _generate_weekly_overlay(
        self,
        bridge: CashToPlanBridge,
        plan: FPAPlan,
        snapshot: models.Snapshot,
        min_cash: Decimal
    ) -> List[WeeklyPlanOverlay]:
        """
        Generate weekly overlay showing plan cash flows mapped to 13-week view.
        Identifies red weeks where plan violates cash constraints.
        """
        overlays = []
        red_weeks = []
        
        # Get bridge lines grouped by week
        lines = self.db.query(BridgeLine).filter(
            BridgeLine.bridge_id == bridge.id
        ).all()
        
        # Determine 13-week range from snapshot
        snapshot_date = snapshot.created_at.date() if snapshot.created_at else date.today()
        week_start = snapshot_date - timedelta(days=snapshot_date.weekday())
        
        # Get opening balance from first bank account
        opening_balance = self._get_opening_balance(snapshot.id)
        current_balance = opening_balance
        
        for week_num in range(1, 14):
            week_end = week_start + timedelta(days=6)
            
            # Sum inflows and outflows for this week
            week_lines = [
                l for l in lines
                if l.period_week and l.period_week == week_start
            ]
            
            plan_inflows = sum(
                l.plan_cash_amount or Decimal("0") 
                for l in week_lines 
                if (l.plan_cash_amount or 0) > 0
            )
            plan_outflows = abs(sum(
                l.plan_cash_amount or Decimal("0")
                for l in week_lines
                if (l.plan_cash_amount or 0) < 0
            ))
            
            actual_inflows = sum(
                l.actual_amount or Decimal("0")
                for l in week_lines
                if (l.actual_amount or 0) > 0
            )
            actual_outflows = abs(sum(
                l.actual_amount or Decimal("0")
                for l in week_lines
                if (l.actual_amount or 0) < 0
            ))
            
            # Calculate closing balance
            closing_balance_plan = current_balance + plan_inflows - plan_outflows
            closing_balance_actual = current_balance + actual_inflows - actual_outflows
            
            # Check for red week
            is_red = closing_balance_plan < min_cash
            shortfall = min_cash - closing_balance_plan if is_red else Decimal("0")
            
            if is_red:
                red_weeks.append({
                    "week_number": week_num,
                    "week_start": week_start.isoformat(),
                    "shortfall": float(shortfall)
                })
            
            overlay = WeeklyPlanOverlay(
                bridge_id=bridge.id,
                week_number=week_num,
                week_start_date=week_start,
                week_end_date=week_end,
                opening_balance_plan=current_balance,
                opening_balance_actual=current_balance,
                plan_inflows=plan_inflows,
                actual_inflows=actual_inflows,
                inflow_variance=actual_inflows - plan_inflows,
                plan_outflows=plan_outflows,
                actual_outflows=actual_outflows,
                outflow_variance=actual_outflows - plan_outflows,
                closing_balance_plan=closing_balance_plan,
                closing_balance_actual=closing_balance_actual,
                min_cash_required=min_cash,
                is_red_week=is_red,
                cash_shortfall=shortfall,
                currency=bridge.base_currency
            )
            self.db.add(overlay)
            overlays.append(overlay)
            
            # Move to next week
            current_balance = closing_balance_plan
            week_start = week_start + timedelta(days=7)
        
        # Update bridge with red weeks info
        bridge.red_weeks_count = len(red_weeks)
        bridge.red_weeks_json = red_weeks
        bridge.min_cash_violation_amount = sum(
            Decimal(str(r["shortfall"])) for r in red_weeks
        )
        
        return overlays
    
    def _get_opening_balance(self, snapshot_id: int) -> Decimal:
        """Get opening cash balance from snapshot's bank accounts."""
        result = self.db.query(
            func.sum(models.BankAccount.balance)
        ).filter(
            models.BankAccount.snapshot_id == snapshot_id
        ).scalar()
        
        return Decimal(str(result or 0))
    
    def _compute_summary_metrics(
        self,
        bridge: CashToPlanBridge,
        weekly_overlay: List[WeeklyPlanOverlay]
    ) -> None:
        """Compute and store summary metrics on the bridge."""
        lines = self.db.query(BridgeLine).filter(
            BridgeLine.bridge_id == bridge.id
        ).all()
        
        # Revenue totals
        revenue_lines = [l for l in lines if l.line_type == BridgeLineType.REVENUE_TO_AR]
        bridge.total_plan_revenue = sum(l.plan_amount or Decimal("0") for l in revenue_lines)
        
        # Inflow totals
        inflow_lines = [l for l in lines if l.line_type == BridgeLineType.AR_TO_CASH]
        bridge.total_plan_cash_inflows = sum(l.plan_cash_amount or Decimal("0") for l in inflow_lines)
        bridge.total_actual_cash_inflows = sum(l.actual_amount or Decimal("0") for l in inflow_lines)
        
        # Expense totals
        expense_types = [BridgeLineType.COGS_TO_AP, BridgeLineType.OPEX_ACCRUAL, BridgeLineType.CAPEX_CASH]
        expense_lines = [l for l in lines if l.line_type in expense_types]
        bridge.total_plan_expenses = sum(l.plan_amount or Decimal("0") for l in expense_lines)
        bridge.total_plan_cash_outflows = sum(abs(l.plan_cash_amount or Decimal("0")) for l in expense_lines)
        bridge.total_actual_cash_outflows = sum(abs(l.actual_amount or Decimal("0")) for l in expense_lines)
        
        # Variance totals
        bridge.total_inflow_variance = bridge.total_actual_cash_inflows - bridge.total_plan_cash_inflows
        bridge.total_outflow_variance = bridge.total_actual_cash_outflows - bridge.total_plan_cash_outflows
        bridge.net_variance = bridge.total_inflow_variance - bridge.total_outflow_variance
    
    def _calculate_timing_days(self, accrual_date: date, cash_date: date) -> int:
        """Calculate days between accrual and cash."""
        if isinstance(cash_date, datetime):
            cash_date = cash_date.date()
        return (cash_date - accrual_date).days
    
    def _generate_bridge_output_json(self, bridge: CashToPlanBridge) -> Dict:
        """Generate structured JSON output for bridge rendering."""
        lines = self.db.query(BridgeLine).filter(
            BridgeLine.bridge_id == bridge.id
        ).all()
        
        return {
            "summary": {
                "plan_revenue": float(bridge.total_plan_revenue or 0),
                "plan_cash_inflows": float(bridge.total_plan_cash_inflows or 0),
                "actual_cash_inflows": float(bridge.total_actual_cash_inflows or 0),
                "plan_expenses": float(bridge.total_plan_expenses or 0),
                "plan_cash_outflows": float(bridge.total_plan_cash_outflows or 0),
                "actual_cash_outflows": float(bridge.total_actual_cash_outflows or 0),
                "inflow_variance": float(bridge.total_inflow_variance or 0),
                "outflow_variance": float(bridge.total_outflow_variance or 0),
                "net_variance": float(bridge.net_variance or 0),
                "ar_change": float(bridge.ar_change or 0),
                "ap_change": float(bridge.ap_change or 0),
                "unknown_inflows": float(bridge.unknown_inflows or 0),
                "unknown_outflows": float(bridge.unknown_outflows or 0),
            },
            "red_weeks": {
                "count": bridge.red_weeks_count,
                "total_shortfall": float(bridge.min_cash_violation_amount or 0),
                "weeks": bridge.red_weeks_json
            },
            "bridge_lines": [
                {
                    "id": l.id,
                    "type": l.line_type.value if l.line_type else None,
                    "category": l.category,
                    "description": l.description,
                    "period_month": l.period_month.isoformat() if l.period_month else None,
                    "period_week": l.period_week.isoformat() if l.period_week else None,
                    "plan_amount": float(l.plan_amount or 0),
                    "plan_cash_amount": float(l.plan_cash_amount or 0),
                    "actual_amount": float(l.actual_amount or 0),
                    "variance": float(l.variance or 0),
                    "timing_days": l.timing_days,
                    "has_evidence": l.has_evidence,
                    "evidence_type": l.evidence_type.value if l.evidence_type else None,
                    "is_unknown": l.is_unknown,
                    "evidence_count": {
                        "invoices": l.invoice_count,
                        "bank_txns": l.bank_txn_count,
                        "vendor_bills": l.vendor_bill_count
                    }
                }
                for l in lines
            ],
            "currency": bridge.base_currency
        }
    
    def _overlay_to_dict(self, overlay: WeeklyPlanOverlay) -> Dict:
        """Convert weekly overlay to dictionary."""
        return {
            "week_number": overlay.week_number,
            "week_start": overlay.week_start_date.isoformat() if overlay.week_start_date else None,
            "week_end": overlay.week_end_date.isoformat() if overlay.week_end_date else None,
            "opening_balance_plan": float(overlay.opening_balance_plan or 0),
            "plan_inflows": float(overlay.plan_inflows or 0),
            "plan_outflows": float(overlay.plan_outflows or 0),
            "closing_balance_plan": float(overlay.closing_balance_plan or 0),
            "actual_inflows": float(overlay.actual_inflows or 0),
            "actual_outflows": float(overlay.actual_outflows or 0),
            "closing_balance_actual": float(overlay.closing_balance_actual or 0),
            "min_cash_required": float(overlay.min_cash_required or 0),
            "is_red_week": overlay.is_red_week,
            "cash_shortfall": float(overlay.cash_shortfall or 0),
            "inflow_variance": float(overlay.inflow_variance or 0),
            "outflow_variance": float(overlay.outflow_variance or 0)
        }
    
    def get_bridge(self, bridge_id: int) -> Optional[CashToPlanBridge]:
        """Get a bridge by ID."""
        return self.db.query(CashToPlanBridge).filter(
            CashToPlanBridge.id == bridge_id
        ).first()
    
    def get_bridge_by_plan_and_snapshot(
        self,
        plan_id: int,
        snapshot_id: int
    ) -> Optional[CashToPlanBridge]:
        """Get existing bridge for plan/snapshot combination."""
        return self.db.query(CashToPlanBridge).filter(
            CashToPlanBridge.plan_id == plan_id,
            CashToPlanBridge.snapshot_id == snapshot_id
        ).order_by(CashToPlanBridge.generated_at.desc()).first()
    
    def get_bridge_lines(
        self,
        bridge_id: int,
        line_type: Optional[BridgeLineType] = None
    ) -> List[BridgeLine]:
        """Get bridge lines, optionally filtered by type."""
        query = self.db.query(BridgeLine).filter(BridgeLine.bridge_id == bridge_id)
        if line_type:
            query = query.filter(BridgeLine.line_type == line_type)
        return query.all()
    
    def get_weekly_overlay(self, bridge_id: int) -> List[WeeklyPlanOverlay]:
        """Get weekly overlay for a bridge."""
        return self.db.query(WeeklyPlanOverlay).filter(
            WeeklyPlanOverlay.bridge_id == bridge_id
        ).order_by(WeeklyPlanOverlay.week_number).all()
    
    def get_evidence_for_line(self, line_id: int) -> Dict[str, Any]:
        """Get detailed evidence for a bridge line."""
        line = self.db.query(BridgeLine).filter(BridgeLine.id == line_id).first()
        if not line:
            return {"error": "Line not found"}
        
        evidence = {
            "line_id": line.id,
            "line_type": line.line_type.value if line.line_type else None,
            "category": line.category,
            "has_evidence": line.has_evidence,
            "is_unknown": line.is_unknown,
            "evidence_refs": line.evidence_refs_json or [],
            "counts": {
                "invoices": line.invoice_count,
                "bank_txns": line.bank_txn_count,
                "vendor_bills": line.vendor_bill_count
            }
        }
        
        # Fetch full details for evidence items
        if line.evidence_refs_json:
            detailed_evidence = []
            for ref in line.evidence_refs_json[:100]:  # Limit for performance
                if ref.get("type") == "invoice":
                    inv = self.db.query(models.Invoice).filter(
                        models.Invoice.id == ref.get("id")
                    ).first()
                    if inv:
                        detailed_evidence.append({
                            "type": "invoice",
                            "id": inv.id,
                            "doc_number": inv.invoice_number,
                            "customer": inv.customer_name,
                            "amount": float(inv.invoice_total_amount or 0),
                            "currency": inv.invoice_currency,
                            "issue_date": inv.invoice_issue_date.isoformat() if inv.invoice_issue_date else None,
                            "due_date": inv.invoice_due_date.isoformat() if inv.invoice_due_date else None,
                            "status": inv.reconciliation_status
                        })
                elif ref.get("type") == "bank_txn":
                    txn = self.db.query(models.BankTransaction).filter(
                        models.BankTransaction.id == ref.get("id")
                    ).first()
                    if txn:
                        detailed_evidence.append({
                            "type": "bank_txn",
                            "id": txn.id,
                            "reference": txn.reference,
                            "amount": float(txn.transaction_amount or 0),
                            "currency": txn.currency,
                            "date": txn.transaction_date.isoformat() if txn.transaction_date else None,
                            "counterparty": txn.counterparty_name
                        })
            
            evidence["detailed_evidence"] = detailed_evidence
        
        return evidence
