"""
Board Pack Autopilot Service

Generates 10-slide board pack from snapshot + plan outputs.
All numbers deterministically derived. Narratives describe computed results only.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

import models
from board_pack_models import (
    BoardPack, BoardPackSlide, BoardPackRisk, BoardPackAction, BoardPackAuditLog,
    BoardPackStatus, SlideType, RiskSeverity
)
from startup_planning_models import StartupPlanningScenario, PlanningOutput
from cash_plan_bridge_models import CashToPlanBridge


class BoardPackService:
    """
    Service for generating board packs.
    
    10-Slide Structure:
    1. Cover
    2. Executive Summary
    3. Key Highlights
    4. Runway Analysis
    5. Forecast vs Actual/Last Month
    6. Revenue Drivers
    7. Expense Drivers
    8. Risks & Mitigations
    9. Action Plan
    10. Appendix
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_board_pack(
        self,
        entity_id: int,
        snapshot_id: int,
        plan_id: Optional[int] = None,
        previous_pack_id: Optional[int] = None,
        generated_by: Optional[str] = None,
        base_currency: str = "USD"
    ) -> BoardPack:
        """
        Generate a complete board pack from snapshot and plan data.
        All numbers are deterministically computed.
        """
        # Load source data
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        # Load plan output if provided
        plan_output = None
        plan_scenario = None
        if plan_id:
            plan_scenario = self.db.query(StartupPlanningScenario).filter(
                StartupPlanningScenario.id == plan_id
            ).first()
            plan_output = self.db.query(PlanningOutput).filter(
                PlanningOutput.scenario_id == plan_id
            ).first()
        
        # Load previous pack for comparison
        previous_pack = None
        if previous_pack_id:
            previous_pack = self.db.query(BoardPack).filter(
                BoardPack.id == previous_pack_id
            ).first()
        
        # Compute all metrics from source data
        metrics = self._compute_all_metrics(snapshot, plan_output, previous_pack)
        
        # Create pack
        period_label = snapshot.created_at.strftime("%B %Y") if snapshot.created_at else "Current Period"
        
        pack = BoardPack(
            entity_id=entity_id,
            snapshot_id=snapshot_id,
            plan_id=plan_id,
            previous_pack_id=previous_pack_id,
            title=f"Board Pack - {period_label}",
            period_label=period_label,
            as_of_date=snapshot.created_at.date() if snapshot.created_at else date.today(),
            status=BoardPackStatus.DRAFT,
            generated_at=datetime.utcnow(),
            generated_by=generated_by,
            base_currency=base_currency,
            # Summary metrics
            runway_months=metrics.get("runway_months", 0),
            ending_cash=Decimal(str(metrics.get("ending_cash", 0))),
            ending_arr=Decimal(str(metrics.get("ending_arr", 0))),
            monthly_burn=Decimal(str(metrics.get("monthly_burn", 0))),
            headcount=metrics.get("headcount", 0),
            arr_change_pct=Decimal(str(metrics.get("arr_change_pct", 0))),
            burn_change_pct=Decimal(str(metrics.get("burn_change_pct", 0))),
            runway_change_months=metrics.get("runway_change_months", 0)
        )
        self.db.add(pack)
        self.db.flush()
        
        # Generate all 10 slides
        slides = self._generate_all_slides(pack, metrics, snapshot, plan_output, previous_pack)
        for slide in slides:
            self.db.add(slide)
        
        # Identify risks from data
        risks = self._identify_risks(pack, metrics)
        for risk in risks:
            self.db.add(risk)
        pack.critical_risks_count = len([r for r in risks if r.severity == RiskSeverity.CRITICAL])
        pack.high_risks_count = len([r for r in risks if r.severity == RiskSeverity.HIGH])
        
        # Generate action items from risks and metrics
        actions = self._generate_actions(pack, metrics, risks)
        for action in actions:
            self.db.add(action)
        
        # Store full pack data
        pack.pack_data_json = self._build_pack_data_json(pack, metrics, slides, risks, actions)
        
        # Create audit log entry
        audit = BoardPackAuditLog(
            pack_id=pack.id,
            action="created",
            actor=generated_by or "system",
            details_json={
                "snapshot_id": snapshot_id,
                "plan_id": plan_id,
                "previous_pack_id": previous_pack_id
            }
        )
        self.db.add(audit)
        
        self.db.commit()
        return pack
    
    def _compute_all_metrics(
        self,
        snapshot: models.Snapshot,
        plan_output: Optional[PlanningOutput],
        previous_pack: Optional[BoardPack]
    ) -> Dict[str, Any]:
        """Compute all metrics from source data."""
        metrics = {}
        
        # ═══════════════════════════════════════════════════════════════════
        # FROM SNAPSHOT (Bank Truth)
        # ═══════════════════════════════════════════════════════════════════
        
        # Cash position
        cash_balance = self.db.query(func.sum(models.BankAccount.balance)).filter(
            models.BankAccount.snapshot_id == snapshot.id
        ).scalar() or Decimal("0")
        metrics["ending_cash"] = float(cash_balance)
        
        # Invoices (AR)
        invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).all()
        
        total_ar = sum(float(inv.invoice_total_amount or 0) for inv in invoices)
        open_ar = sum(float(inv.open_amount or inv.invoice_total_amount or 0) 
                     for inv in invoices 
                     if hasattr(inv, 'reconciliation_status') and inv.reconciliation_status != 'matched')
        metrics["total_ar"] = total_ar
        metrics["open_ar"] = open_ar
        
        # Bank transactions for the period
        transactions = self.db.query(models.BankTransaction).filter(
            models.BankTransaction.snapshot_id == snapshot.id
        ).all()
        
        inflows = sum(float(t.transaction_amount or 0) for t in transactions if (t.transaction_amount or 0) > 0)
        outflows = abs(sum(float(t.transaction_amount or 0) for t in transactions if (t.transaction_amount or 0) < 0))
        metrics["period_inflows"] = inflows
        metrics["period_outflows"] = outflows
        metrics["net_cash_flow"] = inflows - outflows
        
        # ═══════════════════════════════════════════════════════════════════
        # FROM PLAN OUTPUT (if available)
        # ═══════════════════════════════════════════════════════════════════
        
        if plan_output:
            metrics["runway_months"] = plan_output.runway_months or 0
            metrics["ending_arr"] = float(plan_output.ending_arr or 0)
            metrics["ending_mrr"] = float(plan_output.ending_mrr or 0)
            metrics["total_revenue"] = float(plan_output.total_revenue or 0)
            metrics["total_expenses"] = float(plan_output.total_expenses or 0)
            metrics["monthly_burn"] = float(plan_output.total_burn or 0) / max(len(plan_output.monthly_pnl_json or []), 1)
            metrics["max_hires"] = plan_output.max_additional_hires or 0
            
            # Headcount from monthly data
            if plan_output.monthly_headcount_json:
                last_month = plan_output.monthly_headcount_json[-1] if plan_output.monthly_headcount_json else {}
                metrics["headcount"] = last_month.get("total_headcount", 0)
            
            # Monthly P&L for charts
            metrics["monthly_pnl"] = plan_output.monthly_pnl_json or []
            metrics["monthly_cashflow"] = plan_output.monthly_cashflow_json or []
            
            # Runway analysis
            metrics["runway_analysis"] = plan_output.runway_analysis_json or {}
            
        else:
            # Estimate from snapshot data
            metrics["runway_months"] = 0
            metrics["ending_arr"] = 0
            metrics["ending_mrr"] = 0
            metrics["monthly_burn"] = outflows - inflows
            metrics["headcount"] = 0
        
        # ═══════════════════════════════════════════════════════════════════
        # MONTH-OVER-MONTH CHANGES (vs previous pack)
        # ═══════════════════════════════════════════════════════════════════
        
        if previous_pack:
            prev_arr = float(previous_pack.ending_arr or 0)
            prev_burn = float(previous_pack.monthly_burn or 0)
            prev_runway = previous_pack.runway_months or 0
            prev_cash = float(previous_pack.ending_cash or 0)
            
            metrics["arr_change"] = metrics.get("ending_arr", 0) - prev_arr
            metrics["arr_change_pct"] = ((metrics.get("ending_arr", 0) - prev_arr) / prev_arr * 100) if prev_arr else 0
            
            metrics["burn_change"] = metrics.get("monthly_burn", 0) - prev_burn
            metrics["burn_change_pct"] = ((metrics.get("monthly_burn", 0) - prev_burn) / abs(prev_burn) * 100) if prev_burn else 0
            
            metrics["runway_change_months"] = metrics.get("runway_months", 0) - prev_runway
            metrics["cash_change"] = metrics.get("ending_cash", 0) - prev_cash
        else:
            metrics["arr_change"] = 0
            metrics["arr_change_pct"] = 0
            metrics["burn_change"] = 0
            metrics["burn_change_pct"] = 0
            metrics["runway_change_months"] = 0
            metrics["cash_change"] = 0
        
        return metrics
    
    def _generate_all_slides(
        self,
        pack: BoardPack,
        metrics: Dict,
        snapshot: models.Snapshot,
        plan_output: Optional[PlanningOutput],
        previous_pack: Optional[BoardPack]
    ) -> List[BoardPackSlide]:
        """Generate all 10 slides."""
        slides = []
        
        # Slide 1: Cover
        slides.append(self._generate_cover_slide(pack, metrics, 1))
        
        # Slide 2: Executive Summary
        slides.append(self._generate_executive_summary_slide(pack, metrics, 2))
        
        # Slide 3: Key Highlights
        slides.append(self._generate_highlights_slide(pack, metrics, 3))
        
        # Slide 4: Runway Analysis
        slides.append(self._generate_runway_slide(pack, metrics, 4))
        
        # Slide 5: Forecast vs Last Month
        slides.append(self._generate_forecast_comparison_slide(pack, metrics, previous_pack, 5))
        
        # Slide 6: Revenue Drivers
        slides.append(self._generate_revenue_drivers_slide(pack, metrics, 6))
        
        # Slide 7: Expense Drivers
        slides.append(self._generate_expense_drivers_slide(pack, metrics, 7))
        
        # Slide 8: Risks & Mitigations
        slides.append(self._generate_risks_slide(pack, metrics, 8))
        
        # Slide 9: Action Plan
        slides.append(self._generate_action_plan_slide(pack, metrics, 9))
        
        # Slide 10: Appendix
        slides.append(self._generate_appendix_slide(pack, metrics, snapshot, 10))
        
        return slides
    
    def _generate_cover_slide(self, pack: BoardPack, metrics: Dict, slide_num: int) -> BoardPackSlide:
        """Generate cover slide."""
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.COVER,
            title=pack.title,
            headline=f"Financial Review: {pack.period_label}",
            narrative=f"As of {pack.as_of_date.strftime('%B %d, %Y') if pack.as_of_date else 'Current Date'}",
            metrics_json=[
                {"label": "Period", "value": pack.period_label},
                {"label": "Status", "value": pack.status.value}
            ]
        )
    
    def _generate_executive_summary_slide(self, pack: BoardPack, metrics: Dict, slide_num: int) -> BoardPackSlide:
        """Generate executive summary with key metrics."""
        runway = metrics.get("runway_months", 0)
        arr = metrics.get("ending_arr", 0)
        burn = metrics.get("monthly_burn", 0)
        cash = metrics.get("ending_cash", 0)
        
        # Generate narrative from computed data
        narrative_parts = []
        
        if runway > 0:
            narrative_parts.append(f"Current runway is {runway} months based on trailing burn rate.")
        
        if arr > 0:
            arr_change = metrics.get("arr_change_pct", 0)
            if arr_change > 0:
                narrative_parts.append(f"ARR grew {arr_change:.1f}% month-over-month to ${arr:,.0f}.")
            elif arr_change < 0:
                narrative_parts.append(f"ARR declined {abs(arr_change):.1f}% month-over-month to ${arr:,.0f}.")
            else:
                narrative_parts.append(f"ARR remained flat at ${arr:,.0f}.")
        
        if burn != 0:
            narrative_parts.append(f"Monthly burn is ${abs(burn):,.0f}.")
        
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.EXECUTIVE_SUMMARY,
            title="Executive Summary",
            headline=self._compute_headline(metrics),
            narrative=" ".join(narrative_parts),
            metrics_json=[
                {"label": "ARR", "value": arr, "format": "currency", "change_pct": metrics.get("arr_change_pct", 0)},
                {"label": "Monthly Burn", "value": abs(burn), "format": "currency", "change_pct": metrics.get("burn_change_pct", 0)},
                {"label": "Cash", "value": cash, "format": "currency"},
                {"label": "Runway", "value": runway, "format": "months", "change": metrics.get("runway_change_months", 0)},
                {"label": "Headcount", "value": metrics.get("headcount", 0), "format": "number"}
            ]
        )
    
    def _compute_headline(self, metrics: Dict) -> str:
        """Compute headline from metrics - no subjective language."""
        runway = metrics.get("runway_months", 0)
        arr_change = metrics.get("arr_change_pct", 0)
        
        if runway < 6:
            return f"Runway at {runway} months. Immediate action required."
        elif runway < 12:
            return f"Runway at {runway} months. Planning fundraise or cost reduction."
        elif arr_change > 10:
            return f"Strong growth: ARR up {arr_change:.1f}% with {runway} months runway."
        elif arr_change > 0:
            return f"Steady progress: ARR up {arr_change:.1f}% with {runway} months runway."
        else:
            return f"ARR flat/declining. {runway} months runway remaining."
    
    def _generate_highlights_slide(self, pack: BoardPack, metrics: Dict, slide_num: int) -> BoardPackSlide:
        """Generate key highlights slide - all derived from data."""
        bullets = []
        
        # Revenue highlight
        arr = metrics.get("ending_arr", 0)
        arr_change = metrics.get("arr_change", 0)
        if arr > 0:
            direction = "increased" if arr_change > 0 else "decreased" if arr_change < 0 else "remained at"
            bullets.append({
                "text": f"ARR {direction} to ${arr:,.0f} ({arr_change:+,.0f} vs last month)",
                "source": "computed from plan_output.ending_arr"
            })
        
        # Runway highlight
        runway = metrics.get("runway_months", 0)
        runway_change = metrics.get("runway_change_months", 0)
        if runway > 0:
            change_text = f" ({runway_change:+d} months)" if runway_change != 0 else ""
            bullets.append({
                "text": f"Runway stands at {runway} months{change_text}",
                "source": "computed from plan_output.runway_months"
            })
        
        # Cash highlight
        cash = metrics.get("ending_cash", 0)
        cash_change = metrics.get("cash_change", 0)
        if cash > 0:
            bullets.append({
                "text": f"Cash position: ${cash:,.0f} ({cash_change:+,.0f} change)",
                "source": "computed from bank_account.balance"
            })
        
        # Headcount highlight
        headcount = metrics.get("headcount", 0)
        max_hires = metrics.get("max_hires", 0)
        if headcount > 0:
            bullets.append({
                "text": f"Team size: {headcount} employees. Hiring capacity: {max_hires} additional.",
                "source": "computed from headcount_plan"
            })
        
        # Collections highlight
        inflows = metrics.get("period_inflows", 0)
        if inflows > 0:
            bullets.append({
                "text": f"Collections this period: ${inflows:,.0f}",
                "source": "computed from bank_transactions (inflows)"
            })
        
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.KEY_HIGHLIGHTS,
            title="Key Highlights",
            headline="Performance Summary",
            bullets_json=bullets[:6]  # Max 6 bullets
        )
    
    def _generate_runway_slide(self, pack: BoardPack, metrics: Dict, slide_num: int) -> BoardPackSlide:
        """Generate runway analysis slide."""
        runway_analysis = metrics.get("runway_analysis", {})
        monthly_burns = runway_analysis.get("monthly_burns", [])
        
        # Compute average burn
        avg_burn = sum(monthly_burns) / len(monthly_burns) if monthly_burns else 0
        
        narrative = f"Based on current burn rate of ${abs(avg_burn):,.0f}/month and cash of ${metrics.get('ending_cash', 0):,.0f}."
        
        if metrics.get("runway_months", 0) < 12:
            narrative += " Recommend initiating fundraise conversations or implementing cost reductions."
        
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.RUNWAY_ANALYSIS,
            title="Runway Analysis",
            headline=f"{metrics.get('runway_months', 0)} Months Runway",
            narrative=narrative,
            metrics_json=[
                {"label": "Current Cash", "value": metrics.get("ending_cash", 0), "format": "currency"},
                {"label": "Avg Monthly Burn", "value": abs(avg_burn), "format": "currency"},
                {"label": "Runway", "value": metrics.get("runway_months", 0), "format": "months"},
                {"label": "Cash Zero Date", "value": runway_analysis.get("cash_zero_date", "N/A")}
            ],
            charts_json=[
                {
                    "type": "line",
                    "title": "Cash Projection",
                    "data": [
                        {"month": f"M{i+1}", "burn": b, "cumulative": sum(monthly_burns[:i+1])}
                        for i, b in enumerate(monthly_burns[:12])
                    ]
                }
            ]
        )
    
    def _generate_forecast_comparison_slide(
        self, pack: BoardPack, metrics: Dict, previous_pack: Optional[BoardPack], slide_num: int
    ) -> BoardPackSlide:
        """Generate forecast vs last month comparison."""
        monthly_pnl = metrics.get("monthly_pnl", [])
        
        # Build comparison data
        comparison = []
        if previous_pack:
            comparison = [
                {"metric": "ARR", "current": metrics.get("ending_arr", 0), 
                 "previous": float(previous_pack.ending_arr or 0),
                 "variance": metrics.get("arr_change", 0)},
                {"metric": "Monthly Burn", "current": abs(metrics.get("monthly_burn", 0)),
                 "previous": abs(float(previous_pack.monthly_burn or 0)),
                 "variance": metrics.get("burn_change", 0)},
                {"metric": "Cash", "current": metrics.get("ending_cash", 0),
                 "previous": float(previous_pack.ending_cash or 0),
                 "variance": metrics.get("cash_change", 0)},
                {"metric": "Runway", "current": metrics.get("runway_months", 0),
                 "previous": previous_pack.runway_months or 0,
                 "variance": metrics.get("runway_change_months", 0)}
            ]
        
        narrative = "Comparison to previous period. "
        if metrics.get("arr_change_pct", 0) > 0:
            narrative += f"ARR improved by {metrics.get('arr_change_pct', 0):.1f}%. "
        if metrics.get("runway_change_months", 0) > 0:
            narrative += f"Runway extended by {metrics.get('runway_change_months', 0)} months."
        elif metrics.get("runway_change_months", 0) < 0:
            narrative += f"Runway decreased by {abs(metrics.get('runway_change_months', 0))} months."
        
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.FORECAST_VS_ACTUAL,
            title="Period-over-Period Comparison",
            headline=f"ARR {metrics.get('arr_change_pct', 0):+.1f}% | Runway {metrics.get('runway_change_months', 0):+d} months",
            narrative=narrative,
            tables_json=[
                {
                    "title": "Key Metrics Comparison",
                    "headers": ["Metric", "Current", "Previous", "Variance"],
                    "rows": [
                        [c["metric"], f"${c['current']:,.0f}" if c["metric"] != "Runway" else str(c["current"]),
                         f"${c['previous']:,.0f}" if c["metric"] != "Runway" else str(c["previous"]),
                         f"{c['variance']:+,.0f}" if c["metric"] != "Runway" else f"{c['variance']:+d}"]
                        for c in comparison
                    ]
                }
            ] if comparison else []
        )
    
    def _generate_revenue_drivers_slide(self, pack: BoardPack, metrics: Dict, slide_num: int) -> BoardPackSlide:
        """Generate revenue drivers slide."""
        monthly_pnl = metrics.get("monthly_pnl", [])
        
        # Extract revenue trend
        revenue_data = [
            {"month": p.get("month", "")[:7], "revenue": p.get("revenue", 0)}
            for p in monthly_pnl[-6:]  # Last 6 months
        ]
        
        mrr = metrics.get("ending_mrr", 0)
        arr = metrics.get("ending_arr", 0)
        
        narrative = f"Current MRR: ${mrr:,.0f} (${arr:,.0f} ARR). "
        if metrics.get("arr_change_pct", 0) > 0:
            narrative += f"Revenue grew {metrics.get('arr_change_pct', 0):.1f}% month-over-month."
        
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.REVENUE_DRIVERS,
            title="Revenue Drivers",
            headline=f"${arr:,.0f} ARR",
            narrative=narrative,
            metrics_json=[
                {"label": "MRR", "value": mrr, "format": "currency"},
                {"label": "ARR", "value": arr, "format": "currency"},
                {"label": "MoM Growth", "value": metrics.get("arr_change_pct", 0), "format": "percent"}
            ],
            charts_json=[
                {
                    "type": "bar",
                    "title": "Monthly Revenue Trend",
                    "data": revenue_data
                }
            ]
        )
    
    def _generate_expense_drivers_slide(self, pack: BoardPack, metrics: Dict, slide_num: int) -> BoardPackSlide:
        """Generate expense drivers slide."""
        monthly_pnl = metrics.get("monthly_pnl", [])
        
        # Get latest month breakdown
        latest = monthly_pnl[-1] if monthly_pnl else {}
        
        payroll = latest.get("payroll", 0)
        other_opex = latest.get("other_opex", 0)
        total_expenses = latest.get("total_expenses", 0)
        
        expense_breakdown = [
            {"category": "Payroll", "amount": payroll, "pct": (payroll / total_expenses * 100) if total_expenses else 0},
            {"category": "Other OpEx", "amount": other_opex, "pct": (other_opex / total_expenses * 100) if total_expenses else 0}
        ]
        
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.EXPENSE_DRIVERS,
            title="Expense Drivers",
            headline=f"${total_expenses:,.0f}/month Total Expenses",
            narrative=f"Payroll represents {expense_breakdown[0]['pct']:.0f}% of total expenses. Headcount: {metrics.get('headcount', 0)}.",
            metrics_json=[
                {"label": "Total Expenses", "value": total_expenses, "format": "currency"},
                {"label": "Payroll", "value": payroll, "format": "currency"},
                {"label": "Other OpEx", "value": other_opex, "format": "currency"},
                {"label": "Headcount", "value": metrics.get("headcount", 0), "format": "number"}
            ],
            charts_json=[
                {
                    "type": "pie",
                    "title": "Expense Breakdown",
                    "data": expense_breakdown
                }
            ]
        )
    
    def _generate_risks_slide(self, pack: BoardPack, metrics: Dict, slide_num: int) -> BoardPackSlide:
        """Generate risks slide - risks are identified in _identify_risks."""
        # Placeholder - risks are computed separately
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.RISKS_MITIGATIONS,
            title="Risks & Mitigations",
            headline="Risk Assessment",
            narrative="Risks identified from threshold analysis. See detailed risk table."
        )
    
    def _generate_action_plan_slide(self, pack: BoardPack, metrics: Dict, slide_num: int) -> BoardPackSlide:
        """Generate action plan slide - actions are generated separately."""
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.ACTION_PLAN,
            title="Action Plan",
            headline="Recommended Actions",
            narrative="Actions derived from risk analysis and metric thresholds."
        )
    
    def _generate_appendix_slide(
        self, pack: BoardPack, metrics: Dict, snapshot: models.Snapshot, slide_num: int
    ) -> BoardPackSlide:
        """Generate appendix with data sources and methodology."""
        return BoardPackSlide(
            pack_id=pack.id,
            slide_number=slide_num,
            slide_type=SlideType.APPENDIX,
            title="Appendix: Data Sources",
            headline="Methodology & Sources",
            narrative="All numbers derived deterministically from snapshot and plan data.",
            bullets_json=[
                {"text": f"Snapshot ID: {pack.snapshot_id}", "source": "snapshot reference"},
                {"text": f"Plan ID: {pack.plan_id}", "source": "plan reference"} if pack.plan_id else None,
                {"text": f"As-of Date: {pack.as_of_date}", "source": "snapshot.created_at"},
                {"text": "Cash balances from bank accounts", "source": "bank_account.balance"},
                {"text": "Revenue from plan outputs", "source": "planning_output.ending_arr"},
                {"text": "Runway computed from burn rate and cash", "source": "computed"}
            ],
            evidence_refs_json=[
                {"type": "snapshot", "id": pack.snapshot_id},
                {"type": "plan", "id": pack.plan_id} if pack.plan_id else None
            ]
        )
    
    def _identify_risks(self, pack: BoardPack, metrics: Dict) -> List[BoardPackRisk]:
        """Identify risks from computed metrics using defined thresholds."""
        risks = []
        
        # Risk: Low runway
        runway = metrics.get("runway_months", 0)
        if runway < 6:
            risks.append(BoardPackRisk(
                pack_id=pack.id,
                risk_title="Critical Runway",
                risk_description=f"Runway is {runway} months, below 6-month critical threshold.",
                severity=RiskSeverity.CRITICAL,
                exposure_amount=Decimal(str(metrics.get("ending_cash", 0))),
                detection_method="runway_months < 6",
                threshold_breached="6 months minimum runway",
                mitigation="Initiate emergency fundraise or implement immediate cost reductions."
            ))
        elif runway < 12:
            risks.append(BoardPackRisk(
                pack_id=pack.id,
                risk_title="Low Runway",
                risk_description=f"Runway is {runway} months, below 12-month recommended threshold.",
                severity=RiskSeverity.HIGH,
                exposure_amount=Decimal(str(metrics.get("ending_cash", 0))),
                detection_method="runway_months < 12",
                threshold_breached="12 months recommended runway",
                mitigation="Begin fundraise planning or cost optimization review."
            ))
        
        # Risk: Declining ARR
        arr_change = metrics.get("arr_change_pct", 0)
        if arr_change < -5:
            risks.append(BoardPackRisk(
                pack_id=pack.id,
                risk_title="Revenue Decline",
                risk_description=f"ARR declined {abs(arr_change):.1f}% month-over-month.",
                severity=RiskSeverity.HIGH if arr_change < -10 else RiskSeverity.MEDIUM,
                exposure_amount=Decimal(str(abs(metrics.get("arr_change", 0)))),
                detection_method="arr_change_pct < -5%",
                threshold_breached="5% ARR decline threshold",
                mitigation="Review churn drivers and customer success processes."
            ))
        
        # Risk: Increasing burn
        burn_change = metrics.get("burn_change_pct", 0)
        if burn_change > 20:
            risks.append(BoardPackRisk(
                pack_id=pack.id,
                risk_title="Burn Rate Increase",
                risk_description=f"Monthly burn increased {burn_change:.1f}% month-over-month.",
                severity=RiskSeverity.MEDIUM,
                exposure_amount=Decimal(str(abs(metrics.get("burn_change", 0)) * 12)),
                detection_method="burn_change_pct > 20%",
                threshold_breached="20% burn increase threshold",
                mitigation="Review hiring plan and discretionary spending."
            ))
        
        # Risk: High AR concentration
        open_ar = metrics.get("open_ar", 0)
        total_ar = metrics.get("total_ar", 0)
        if total_ar > 0 and open_ar / total_ar > 0.5:
            risks.append(BoardPackRisk(
                pack_id=pack.id,
                risk_title="AR Collection Risk",
                risk_description=f"Open AR is {open_ar/total_ar*100:.0f}% of total receivables.",
                severity=RiskSeverity.MEDIUM,
                exposure_amount=Decimal(str(open_ar)),
                detection_method="open_ar / total_ar > 50%",
                threshold_breached="50% open AR threshold",
                mitigation="Accelerate collections and review payment terms."
            ))
        
        return risks
    
    def _generate_actions(
        self, pack: BoardPack, metrics: Dict, risks: List[BoardPackRisk]
    ) -> List[BoardPackAction]:
        """Generate action items from risks and metrics."""
        actions = []
        
        for risk in risks:
            if risk.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]:
                actions.append(BoardPackAction(
                    pack_id=pack.id,
                    action_title=f"Address: {risk.risk_title}",
                    action_description=risk.mitigation,
                    priority="critical" if risk.severity == RiskSeverity.CRITICAL else "high",
                    triggered_by=risk.risk_title
                ))
        
        # Standard actions based on metrics
        if metrics.get("runway_months", 0) < 18:
            actions.append(BoardPackAction(
                pack_id=pack.id,
                action_title="Fundraise Planning",
                action_description="Prepare fundraise materials and begin investor outreach.",
                priority="high" if metrics.get("runway_months", 0) < 12 else "medium",
                triggered_by=f"Runway at {metrics.get('runway_months', 0)} months"
            ))
        
        return actions
    
    def _build_pack_data_json(
        self, pack: BoardPack, metrics: Dict, 
        slides: List[BoardPackSlide], risks: List[BoardPackRisk],
        actions: List[BoardPackAction]
    ) -> Dict:
        """Build complete pack data JSON."""
        return {
            "metadata": {
                "pack_id": pack.id,
                "title": pack.title,
                "period": pack.period_label,
                "as_of_date": pack.as_of_date.isoformat() if pack.as_of_date else None,
                "generated_at": pack.generated_at.isoformat() if pack.generated_at else None,
                "status": pack.status.value
            },
            "summary_metrics": {
                "runway_months": metrics.get("runway_months", 0),
                "ending_cash": metrics.get("ending_cash", 0),
                "ending_arr": metrics.get("ending_arr", 0),
                "monthly_burn": metrics.get("monthly_burn", 0),
                "headcount": metrics.get("headcount", 0)
            },
            "changes": {
                "arr_change_pct": metrics.get("arr_change_pct", 0),
                "burn_change_pct": metrics.get("burn_change_pct", 0),
                "runway_change_months": metrics.get("runway_change_months", 0),
                "cash_change": metrics.get("cash_change", 0)
            },
            "risk_summary": {
                "critical": len([r for r in risks if r.severity == RiskSeverity.CRITICAL]),
                "high": len([r for r in risks if r.severity == RiskSeverity.HIGH]),
                "medium": len([r for r in risks if r.severity == RiskSeverity.MEDIUM]),
                "low": len([r for r in risks if r.severity == RiskSeverity.LOW])
            },
            "action_count": len(actions)
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CFO SIGN-OFF
    # ═══════════════════════════════════════════════════════════════════════════
    
    def sign_off(
        self,
        pack_id: int,
        signed_off_by: str,
        signoff_statement: str,
        ip_address: Optional[str] = None
    ) -> BoardPack:
        """CFO sign-off on board pack."""
        pack = self.db.query(BoardPack).filter(BoardPack.id == pack_id).first()
        if not pack:
            raise ValueError(f"Board pack {pack_id} not found")
        
        if pack.status == BoardPackStatus.SIGNED_OFF:
            raise ValueError("Pack already signed off")
        
        # Require minimum statement length
        if len(signoff_statement.strip()) < 20:
            raise ValueError("Sign-off statement must be at least 20 characters")
        
        # Update pack
        pack.status = BoardPackStatus.SIGNED_OFF
        pack.signed_off_at = datetime.utcnow()
        pack.signed_off_by = signed_off_by
        pack.signoff_statement = signoff_statement
        
        # Create audit log
        audit = BoardPackAuditLog(
            pack_id=pack_id,
            action="signed_off",
            actor=signed_off_by,
            signoff_statement=signoff_statement,
            ip_address=ip_address,
            details_json={
                "status_before": "pending_signoff",
                "status_after": "signed_off"
            }
        )
        self.db.add(audit)
        
        self.db.commit()
        return pack
    
    def get_audit_log(self, pack_id: int) -> List[BoardPackAuditLog]:
        """Get audit log for a pack."""
        return self.db.query(BoardPackAuditLog).filter(
            BoardPackAuditLog.pack_id == pack_id
        ).order_by(desc(BoardPackAuditLog.timestamp)).all()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_pack(self, pack_id: int) -> Optional[BoardPack]:
        return self.db.query(BoardPack).filter(BoardPack.id == pack_id).first()
    
    def get_packs(self, entity_id: int) -> List[BoardPack]:
        return self.db.query(BoardPack).filter(
            BoardPack.entity_id == entity_id
        ).order_by(desc(BoardPack.created_at)).all()
    
    def get_slides(self, pack_id: int) -> List[BoardPackSlide]:
        return self.db.query(BoardPackSlide).filter(
            BoardPackSlide.pack_id == pack_id
        ).order_by(BoardPackSlide.slide_number).all()
    
    def get_risks(self, pack_id: int) -> List[BoardPackRisk]:
        return self.db.query(BoardPackRisk).filter(
            BoardPackRisk.pack_id == pack_id
        ).all()
    
    def get_actions(self, pack_id: int) -> List[BoardPackAction]:
        return self.db.query(BoardPackAction).filter(
            BoardPackAction.pack_id == pack_id
        ).all()
