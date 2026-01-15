"""
Startup/Midmarket Driver-Based Planning Service

Computes P&L, Cashflow Bridge, Runway, and Hiring Capacity
from opinionated driver inputs.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from startup_planning_models import (
    StartupPlanningScenario, PlanningAssumptions, HeadcountPlan,
    SaaSRevenueDriver, VendorCommitment, PlanningOutput, ScenarioComparison,
    PlanningScenarioStatus, Department, RevenueType, ExpenseCategory
)


class StartupPlanningService:
    """
    Service for computing startup planning outputs.
    
    Takes opinionated driver inputs and generates:
    - P&L (Income Statement)
    - Cashflow Bridge
    - Runway Months
    - Hiring Capacity
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCENARIO MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_scenario(
        self,
        entity_id: int,
        name: str,
        start_month: date,
        end_month: date,
        is_base: bool = False,
        parent_scenario_id: Optional[int] = None,
        description: Optional[str] = None,
        base_currency: str = "USD"
    ) -> StartupPlanningScenario:
        """Create a new planning scenario."""
        scenario = StartupPlanningScenario(
            entity_id=entity_id,
            name=name,
            description=description,
            start_month=start_month,
            end_month=end_month,
            is_base=is_base,
            parent_scenario_id=parent_scenario_id,
            base_currency=base_currency,
            status=PlanningScenarioStatus.DRAFT
        )
        self.db.add(scenario)
        self.db.flush()
        
        # Create default assumptions
        assumptions = PlanningAssumptions(
            scenario_id=scenario.id,
            avg_salaries_by_dept_json={
                "engineering": 150000,
                "product": 140000,
                "sales": 120000,
                "marketing": 110000,
                "customer_success": 90000,
                "g_and_a": 100000,
                "operations": 85000,
                "executive": 200000
            }
        )
        self.db.add(assumptions)
        self.db.commit()
        
        return scenario
    
    def branch_scenario(
        self,
        parent_scenario_id: int,
        branch_name: str,
        branch_reason: str
    ) -> StartupPlanningScenario:
        """Create a branch from an existing scenario."""
        parent = self.db.query(StartupPlanningScenario).filter(
            StartupPlanningScenario.id == parent_scenario_id
        ).first()
        
        if not parent:
            raise ValueError(f"Parent scenario {parent_scenario_id} not found")
        
        # Create new scenario as branch
        branch = StartupPlanningScenario(
            entity_id=parent.entity_id,
            name=branch_name,
            description=f"Branch of: {parent.name}",
            start_month=parent.start_month,
            end_month=parent.end_month,
            is_base=False,
            parent_scenario_id=parent_scenario_id,
            branch_reason=branch_reason,
            base_currency=parent.base_currency,
            status=PlanningScenarioStatus.DRAFT
        )
        self.db.add(branch)
        self.db.flush()
        
        # Copy assumptions
        if parent.assumptions:
            new_assumptions = PlanningAssumptions(
                scenario_id=branch.id,
                starting_mrr=parent.assumptions.starting_mrr,
                mrr_growth_rate_pct=parent.assumptions.mrr_growth_rate_pct,
                monthly_churn_rate_pct=parent.assumptions.monthly_churn_rate_pct,
                average_contract_value=parent.assumptions.average_contract_value,
                customer_acquisition_cost=parent.assumptions.customer_acquisition_cost,
                ltv_to_cac_target=parent.assumptions.ltv_to_cac_target,
                benefits_pct_of_salary=parent.assumptions.benefits_pct_of_salary,
                payroll_tax_pct=parent.assumptions.payroll_tax_pct,
                annual_raise_pct=parent.assumptions.annual_raise_pct,
                avg_salaries_by_dept_json=parent.assumptions.avg_salaries_by_dept_json,
                dso_days=parent.assumptions.dso_days,
                dpo_days=parent.assumptions.dpo_days,
                annual_prepay_pct=parent.assumptions.annual_prepay_pct,
                saas_cost_per_employee=parent.assumptions.saas_cost_per_employee,
                infra_pct_of_revenue=parent.assumptions.infra_pct_of_revenue,
                marketing_pct_of_new_arr=parent.assumptions.marketing_pct_of_new_arr,
                office_cost_per_employee=parent.assumptions.office_cost_per_employee,
                starting_cash=parent.assumptions.starting_cash,
                min_cash_buffer=parent.assumptions.min_cash_buffer
            )
            self.db.add(new_assumptions)
        
        # Copy headcount plan
        for hc in parent.headcount_plan:
            new_hc = HeadcountPlan(
                scenario_id=branch.id,
                department=hc.department,
                role_title=hc.role_title,
                seniority_level=hc.seniority_level,
                annual_salary=hc.annual_salary,
                start_month=hc.start_month,
                end_month=hc.end_month,
                headcount=hc.headcount,
                is_backfill=hc.is_backfill,
                notes=hc.notes
            )
            self.db.add(new_hc)
        
        # Copy vendor commitments
        for vc in parent.vendor_commitments:
            new_vc = VendorCommitment(
                scenario_id=branch.id,
                vendor_name=vc.vendor_name,
                category=vc.category,
                monthly_amount=vc.monthly_amount,
                annual_amount=vc.annual_amount,
                payment_frequency=vc.payment_frequency,
                payment_terms_days=vc.payment_terms_days,
                start_date=vc.start_date,
                end_date=vc.end_date,
                auto_renews=vc.auto_renews,
                notes=vc.notes
            )
            self.db.add(new_vc)
        
        self.db.commit()
        return branch
    
    def submit_for_approval(
        self,
        scenario_id: int,
        submitted_by: str
    ) -> StartupPlanningScenario:
        """Submit a scenario for approval."""
        scenario = self.db.query(StartupPlanningScenario).filter(
            StartupPlanningScenario.id == scenario_id
        ).first()
        
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        scenario.status = PlanningScenarioStatus.PENDING_APPROVAL
        scenario.submitted_at = datetime.utcnow()
        scenario.submitted_by = submitted_by
        
        self.db.commit()
        return scenario
    
    def approve_scenario(
        self,
        scenario_id: int,
        approved_by: str,
        approval_notes: Optional[str] = None,
        snapshot_id: Optional[int] = None
    ) -> StartupPlanningScenario:
        """Approve a scenario."""
        scenario = self.db.query(StartupPlanningScenario).filter(
            StartupPlanningScenario.id == scenario_id
        ).first()
        
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        scenario.status = PlanningScenarioStatus.APPROVED
        scenario.approved_at = datetime.utcnow()
        scenario.approved_by = approved_by
        scenario.approval_notes = approval_notes
        scenario.snapshot_id = snapshot_id
        scenario.version += 1  # Increment version on approval
        
        self.db.commit()
        return scenario
    
    # ═══════════════════════════════════════════════════════════════════════════
    # OUTPUT GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_outputs(self, scenario_id: int) -> PlanningOutput:
        """
        Generate all outputs for a scenario:
        - P&L
        - Cashflow Bridge
        - Runway
        - Hiring Capacity
        """
        scenario = self.db.query(StartupPlanningScenario).filter(
            StartupPlanningScenario.id == scenario_id
        ).first()
        
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        assumptions = scenario.assumptions
        if not assumptions:
            raise ValueError(f"Scenario {scenario_id} has no assumptions")
        
        # Get month range
        months = self._get_month_range(scenario.start_month, scenario.end_month)
        
        # Compute revenue projections
        revenue_by_month = self._compute_revenue(scenario, assumptions, months)
        
        # Compute headcount and payroll
        headcount_by_month = self._compute_headcount(scenario, months)
        payroll_by_month = self._compute_payroll(scenario, assumptions, headcount_by_month)
        
        # Compute other expenses
        opex_by_month = self._compute_opex(scenario, assumptions, revenue_by_month, headcount_by_month, months)
        
        # Generate P&L
        monthly_pnl = self._generate_pnl(revenue_by_month, payroll_by_month, opex_by_month, months)
        
        # Generate Cashflow Bridge
        monthly_cashflow = self._generate_cashflow_bridge(
            monthly_pnl, assumptions, Decimal(str(assumptions.starting_cash or 0))
        )
        
        # Compute Runway
        runway_analysis = self._compute_runway(monthly_cashflow, assumptions)
        
        # Compute Hiring Capacity
        hiring_analysis = self._compute_hiring_capacity(
            monthly_cashflow, assumptions, headcount_by_month
        )
        
        # Get summary metrics
        last_month_pnl = monthly_pnl[-1] if monthly_pnl else {}
        last_month_cf = monthly_cashflow[-1] if monthly_cashflow else {}
        last_revenue = revenue_by_month.get(months[-1], {}) if months else {}
        
        # Create or update output
        output = self.db.query(PlanningOutput).filter(
            PlanningOutput.scenario_id == scenario_id
        ).first()
        
        if not output:
            output = PlanningOutput(scenario_id=scenario_id)
            self.db.add(output)
        
        output.generated_at = datetime.utcnow()
        output.assumptions_version = assumptions.version
        
        # Summary metrics
        output.runway_months = runway_analysis.get("runway_months", 0)
        output.cash_zero_date = runway_analysis.get("cash_zero_date")
        output.max_additional_hires = hiring_analysis.get("max_total_hires", 0)
        output.hiring_capacity_details_json = hiring_analysis
        
        output.ending_mrr = Decimal(str(last_revenue.get("ending_mrr", 0)))
        output.ending_arr = Decimal(str(last_revenue.get("ending_mrr", 0) * 12))
        output.ending_customers = last_revenue.get("ending_customers", 0)
        
        output.total_revenue = sum(Decimal(str(p.get("revenue", 0))) for p in monthly_pnl)
        output.total_expenses = sum(Decimal(str(p.get("total_expenses", 0))) for p in monthly_pnl)
        output.total_burn = output.total_expenses - output.total_revenue
        output.ending_cash = Decimal(str(last_month_cf.get("ending_cash", 0)))
        
        # Detailed outputs
        output.monthly_pnl_json = monthly_pnl
        output.monthly_cashflow_json = monthly_cashflow
        output.monthly_headcount_json = [
            {"month": m.isoformat(), **headcount_by_month.get(m, {})}
            for m in months
        ]
        output.runway_analysis_json = runway_analysis
        output.hiring_analysis_json = hiring_analysis
        
        self.db.commit()
        return output
    
    def _get_month_range(self, start: date, end: date) -> List[date]:
        """Get list of months between start and end."""
        months = []
        current = start.replace(day=1)
        end_month = end.replace(day=1)
        
        while current <= end_month:
            months.append(current)
            current = current + relativedelta(months=1)
        
        return months
    
    def _compute_revenue(
        self,
        scenario: StartupPlanningScenario,
        assumptions: PlanningAssumptions,
        months: List[date]
    ) -> Dict[date, Dict]:
        """Compute revenue projections by month."""
        revenue_by_month = {}
        
        # Check if there are explicit revenue drivers
        existing_drivers = {
            d.period_month: d 
            for d in scenario.revenue_drivers
        }
        
        # Start with assumptions
        current_mrr = Decimal(str(assumptions.starting_mrr or 0))
        current_customers = 0  # Will be estimated from ACV
        
        if assumptions.average_contract_value and assumptions.average_contract_value > 0:
            acv_monthly = Decimal(str(assumptions.average_contract_value)) / 12
            if acv_monthly > 0:
                current_customers = int(current_mrr / acv_monthly)
        
        growth_rate = Decimal(str(assumptions.mrr_growth_rate_pct or 0)) / 100
        churn_rate = Decimal(str(assumptions.monthly_churn_rate_pct or 0)) / 100
        cac = Decimal(str(assumptions.customer_acquisition_cost or 0))
        
        for month in months:
            if month in existing_drivers:
                # Use explicit driver
                driver = existing_drivers[month]
                revenue_by_month[month] = {
                    "starting_mrr": float(driver.starting_mrr or 0),
                    "new_mrr": float(driver.new_mrr or 0),
                    "expansion_mrr": float(driver.expansion_mrr or 0),
                    "churned_mrr": float(driver.churned_mrr or 0),
                    "ending_mrr": float(driver.ending_mrr or 0),
                    "starting_customers": driver.starting_customers or 0,
                    "new_customers": driver.new_customers or 0,
                    "churned_customers": driver.churned_customers or 0,
                    "ending_customers": driver.ending_customers or 0,
                    "cac_spend": float(driver.cac_spend or 0)
                }
                current_mrr = Decimal(str(driver.ending_mrr or 0))
                current_customers = driver.ending_customers or 0
            else:
                # Compute from assumptions
                starting_mrr = current_mrr
                starting_customers = current_customers
                
                # New MRR from growth
                new_mrr = starting_mrr * growth_rate
                new_customers = int(starting_customers * float(growth_rate)) if starting_customers > 0 else 1
                
                # Churn
                churned_mrr = starting_mrr * churn_rate
                churned_customers = max(1, int(starting_customers * float(churn_rate)))
                
                ending_mrr = starting_mrr + new_mrr - churned_mrr
                ending_customers = max(0, starting_customers + new_customers - churned_customers)
                
                cac_spend = cac * new_customers
                
                revenue_by_month[month] = {
                    "starting_mrr": float(starting_mrr),
                    "new_mrr": float(new_mrr),
                    "expansion_mrr": 0,
                    "churned_mrr": float(churned_mrr),
                    "ending_mrr": float(ending_mrr),
                    "starting_customers": starting_customers,
                    "new_customers": new_customers,
                    "churned_customers": churned_customers,
                    "ending_customers": ending_customers,
                    "cac_spend": float(cac_spend)
                }
                
                current_mrr = ending_mrr
                current_customers = ending_customers
        
        return revenue_by_month
    
    def _compute_headcount(
        self,
        scenario: StartupPlanningScenario,
        months: List[date]
    ) -> Dict[date, Dict]:
        """Compute headcount by department by month."""
        headcount_by_month = {}
        
        for month in months:
            by_dept = defaultdict(lambda: {"count": 0, "salary_total": 0})
            
            for hc in scenario.headcount_plan:
                # Check if this role is active in this month
                if hc.start_month <= month:
                    if hc.end_month is None or hc.end_month >= month:
                        dept = hc.department.value
                        by_dept[dept]["count"] += hc.headcount
                        by_dept[dept]["salary_total"] += float(hc.annual_salary or 0) * hc.headcount
            
            total_count = sum(d["count"] for d in by_dept.values())
            total_salary = sum(d["salary_total"] for d in by_dept.values())
            
            headcount_by_month[month] = {
                "by_department": dict(by_dept),
                "total_headcount": total_count,
                "total_annual_salary": total_salary
            }
        
        return headcount_by_month
    
    def _compute_payroll(
        self,
        scenario: StartupPlanningScenario,
        assumptions: PlanningAssumptions,
        headcount_by_month: Dict[date, Dict]
    ) -> Dict[date, Dict]:
        """Compute payroll expense by month."""
        payroll_by_month = {}
        
        benefits_pct = Decimal(str(assumptions.benefits_pct_of_salary or 25)) / 100
        payroll_tax_pct = Decimal(str(assumptions.payroll_tax_pct or 10)) / 100
        
        for month, hc_data in headcount_by_month.items():
            annual_salary = Decimal(str(hc_data.get("total_annual_salary", 0)))
            monthly_salary = annual_salary / 12
            
            benefits = monthly_salary * benefits_pct
            payroll_tax = monthly_salary * payroll_tax_pct
            
            total_payroll = monthly_salary + benefits + payroll_tax
            
            payroll_by_month[month] = {
                "base_salary": float(monthly_salary),
                "benefits": float(benefits),
                "payroll_tax": float(payroll_tax),
                "total_payroll": float(total_payroll),
                "headcount": hc_data.get("total_headcount", 0)
            }
        
        return payroll_by_month
    
    def _compute_opex(
        self,
        scenario: StartupPlanningScenario,
        assumptions: PlanningAssumptions,
        revenue_by_month: Dict[date, Dict],
        headcount_by_month: Dict[date, Dict],
        months: List[date]
    ) -> Dict[date, Dict]:
        """Compute operating expenses by month."""
        opex_by_month = {}
        
        saas_per_emp = Decimal(str(assumptions.saas_cost_per_employee or 500))
        infra_pct = Decimal(str(assumptions.infra_pct_of_revenue or 5)) / 100
        marketing_pct = Decimal(str(assumptions.marketing_pct_of_new_arr or 30)) / 100
        office_per_emp = Decimal(str(assumptions.office_cost_per_employee or 500))
        
        for month in months:
            rev_data = revenue_by_month.get(month, {})
            hc_data = headcount_by_month.get(month, {})
            
            headcount = hc_data.get("total_headcount", 0)
            mrr = Decimal(str(rev_data.get("ending_mrr", 0)))
            new_arr = Decimal(str(rev_data.get("new_mrr", 0))) * 12
            
            # Calculate each expense category
            saas_tools = saas_per_emp * headcount
            infrastructure = mrr * infra_pct
            marketing = new_arr * marketing_pct + Decimal(str(rev_data.get("cac_spend", 0)))
            office = office_per_emp * headcount
            
            # Add vendor commitments
            vendor_total = Decimal("0")
            for vc in scenario.vendor_commitments:
                if vc.start_date <= month:
                    if vc.end_date is None or vc.end_date >= month:
                        vendor_total += Decimal(str(vc.monthly_amount or 0))
            
            opex_by_month[month] = {
                "saas_tools": float(saas_tools),
                "infrastructure": float(infrastructure),
                "marketing_spend": float(marketing),
                "office": float(office),
                "vendor_commitments": float(vendor_total),
                "total_opex": float(saas_tools + infrastructure + marketing + office + vendor_total)
            }
        
        return opex_by_month
    
    def _generate_pnl(
        self,
        revenue_by_month: Dict[date, Dict],
        payroll_by_month: Dict[date, Dict],
        opex_by_month: Dict[date, Dict],
        months: List[date]
    ) -> List[Dict]:
        """Generate monthly P&L."""
        pnl = []
        
        for month in months:
            rev_data = revenue_by_month.get(month, {})
            pay_data = payroll_by_month.get(month, {})
            opex_data = opex_by_month.get(month, {})
            
            revenue = rev_data.get("ending_mrr", 0)
            
            # COGS (simplified - infrastructure + some support costs)
            cogs = opex_data.get("infrastructure", 0) * 0.5  # 50% of infra is COGS
            gross_profit = revenue - cogs
            gross_margin_pct = (gross_profit / revenue * 100) if revenue > 0 else 0
            
            # OpEx
            payroll = pay_data.get("total_payroll", 0)
            other_opex = opex_data.get("total_opex", 0)
            total_opex = payroll + other_opex
            
            # EBITDA
            ebitda = gross_profit - total_opex + cogs  # Add back COGS we subtracted
            net_income = revenue - payroll - other_opex
            
            pnl.append({
                "month": month.isoformat(),
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross_profit,
                "gross_margin_pct": round(gross_margin_pct, 1),
                "payroll": payroll,
                "other_opex": other_opex,
                "total_expenses": payroll + other_opex,
                "ebitda": ebitda,
                "net_income": net_income,
                "headcount": pay_data.get("headcount", 0),
                "ending_mrr": rev_data.get("ending_mrr", 0),
                "ending_arr": rev_data.get("ending_mrr", 0) * 12
            })
        
        return pnl
    
    def _generate_cashflow_bridge(
        self,
        monthly_pnl: List[Dict],
        assumptions: PlanningAssumptions,
        starting_cash: Decimal
    ) -> List[Dict]:
        """Generate monthly cashflow bridge."""
        cashflow = []
        current_cash = starting_cash
        
        dso_days = assumptions.dso_days or 30
        dpo_days = assumptions.dpo_days or 30
        prepay_pct = Decimal(str(assumptions.annual_prepay_pct or 20)) / 100
        
        # Simplified working capital model
        ar_balance = Decimal("0")
        ap_balance = Decimal("0")
        deferred_revenue = Decimal("0")
        
        for pnl in monthly_pnl:
            revenue = Decimal(str(pnl.get("revenue", 0)))
            expenses = Decimal(str(pnl.get("total_expenses", 0)))
            
            # Cash collections
            # Prepaid customers pay upfront, others based on DSO
            prepaid_collection = revenue * prepay_pct
            regular_collection = ar_balance * Decimal(30 / max(dso_days, 1))
            cash_collected = prepaid_collection + regular_collection
            
            # Update AR
            new_ar = revenue * (1 - prepay_pct)
            ar_change = new_ar - regular_collection
            ar_balance = max(Decimal("0"), ar_balance + ar_change)
            
            # Cash payments
            # Pay based on DPO
            cash_paid = ap_balance * Decimal(30 / max(dpo_days, 1)) + expenses * Decimal("0.7")  # 70% paid immediately
            
            # Update AP
            new_ap = expenses * Decimal("0.3")  # 30% goes to AP
            ap_change = new_ap - (ap_balance * Decimal(30 / max(dpo_days, 1)))
            ap_balance = max(Decimal("0"), ap_balance + ap_change)
            
            # Deferred revenue (from annual prepays)
            deferred_addition = prepaid_collection * Decimal("11")  # 11 months of prepaid revenue
            deferred_recognition = deferred_revenue / 12 if deferred_revenue > 0 else Decimal("0")
            deferred_revenue = deferred_revenue + deferred_addition - deferred_recognition
            
            # Net cash flow
            operating_cash_flow = cash_collected - cash_paid
            ending_cash = current_cash + operating_cash_flow
            
            cashflow.append({
                "month": pnl.get("month"),
                "starting_cash": float(current_cash),
                "revenue_collected": float(cash_collected),
                "expenses_paid": float(cash_paid),
                "ar_change": float(ar_change),
                "ap_change": float(ap_change),
                "deferred_revenue_change": float(deferred_addition - deferred_recognition),
                "operating_cash_flow": float(operating_cash_flow),
                "ending_cash": float(ending_cash),
                "ar_balance": float(ar_balance),
                "ap_balance": float(ap_balance),
                "deferred_revenue": float(deferred_revenue)
            })
            
            current_cash = ending_cash
        
        return cashflow
    
    def _compute_runway(
        self,
        monthly_cashflow: List[Dict],
        assumptions: PlanningAssumptions
    ) -> Dict:
        """Compute runway analysis."""
        min_buffer = Decimal(str(assumptions.min_cash_buffer or 100000))
        
        runway_months = 0
        cash_zero_date = None
        monthly_burns = []
        
        for i, cf in enumerate(monthly_cashflow):
            ending_cash = Decimal(str(cf.get("ending_cash", 0)))
            burn = Decimal(str(cf.get("operating_cash_flow", 0)))
            
            monthly_burns.append(float(burn))
            
            if ending_cash > min_buffer:
                runway_months = i + 1
            elif cash_zero_date is None and ending_cash <= min_buffer:
                # First month below buffer
                cash_zero_date = cf.get("month")
        
        # Calculate average burn (last 3 months or all if less)
        recent_burns = monthly_burns[-3:] if len(monthly_burns) >= 3 else monthly_burns
        avg_monthly_burn = sum(recent_burns) / len(recent_burns) if recent_burns else 0
        
        return {
            "runway_months": runway_months,
            "cash_zero_date": cash_zero_date,
            "avg_monthly_burn": avg_monthly_burn,
            "monthly_burns": monthly_burns,
            "min_cash_buffer": float(min_buffer)
        }
    
    def _compute_hiring_capacity(
        self,
        monthly_cashflow: List[Dict],
        assumptions: PlanningAssumptions,
        headcount_by_month: Dict[date, Dict]
    ) -> Dict:
        """Compute hiring capacity - how many more people can be hired."""
        # Get current state
        if not monthly_cashflow:
            return {"max_total_hires": 0, "by_department": {}}
        
        last_cf = monthly_cashflow[-1]
        ending_cash = Decimal(str(last_cf.get("ending_cash", 0)))
        min_buffer = Decimal(str(assumptions.min_cash_buffer or 100000))
        available_cash = max(Decimal("0"), ending_cash - min_buffer)
        
        # Get average salaries by department
        avg_salaries = assumptions.avg_salaries_by_dept_json or {}
        benefits_pct = Decimal(str(assumptions.benefits_pct_of_salary or 25)) / 100
        payroll_tax_pct = Decimal(str(assumptions.payroll_tax_pct or 10)) / 100
        
        # Calculate cost per hire by department (annualized)
        cost_per_hire = {}
        for dept, salary in avg_salaries.items():
            base = Decimal(str(salary))
            total_annual = base * (1 + benefits_pct + payroll_tax_pct)
            cost_per_hire[dept] = float(total_annual)
        
        # Calculate max hires assuming 12 months of runway
        runway_factor = 12  # Plan for 12 months
        max_hires_by_dept = {}
        
        for dept, annual_cost in cost_per_hire.items():
            if annual_cost > 0:
                max_hires = int(float(available_cash) / annual_cost)
                max_hires_by_dept[dept] = max_hires
        
        # Total hiring capacity (using average cost)
        avg_cost = sum(cost_per_hire.values()) / len(cost_per_hire) if cost_per_hire else 0
        max_total_hires = int(float(available_cash) / avg_cost) if avg_cost > 0 else 0
        
        return {
            "available_cash": float(available_cash),
            "min_cash_buffer": float(min_buffer),
            "cost_per_hire_annual": cost_per_hire,
            "max_hires_by_department": max_hires_by_dept,
            "max_total_hires": max_total_hires
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCENARIO COMPARISON
    # ═══════════════════════════════════════════════════════════════════════════
    
    def compare_scenarios(
        self,
        base_scenario_id: int,
        compare_scenario_id: int
    ) -> ScenarioComparison:
        """Compare two scenarios and generate delta report."""
        base = self.db.query(StartupPlanningScenario).filter(
            StartupPlanningScenario.id == base_scenario_id
        ).first()
        compare = self.db.query(StartupPlanningScenario).filter(
            StartupPlanningScenario.id == compare_scenario_id
        ).first()
        
        if not base or not compare:
            raise ValueError("One or both scenarios not found")
        
        # Get outputs (generate if needed)
        base_output = self.db.query(PlanningOutput).filter(
            PlanningOutput.scenario_id == base_scenario_id
        ).first()
        compare_output = self.db.query(PlanningOutput).filter(
            PlanningOutput.scenario_id == compare_scenario_id
        ).first()
        
        if not base_output:
            base_output = self.generate_outputs(base_scenario_id)
        if not compare_output:
            compare_output = self.generate_outputs(compare_scenario_id)
        
        # Compute deltas
        comparison_data = {
            "revenue_delta": float((compare_output.total_revenue or 0) - (base_output.total_revenue or 0)),
            "expense_delta": float((compare_output.total_expenses or 0) - (base_output.total_expenses or 0)),
            "burn_delta": float((compare_output.total_burn or 0) - (base_output.total_burn or 0)),
            "runway_delta": (compare_output.runway_months or 0) - (base_output.runway_months or 0),
            "mrr_delta": float((compare_output.ending_mrr or 0) - (base_output.ending_mrr or 0)),
            "arr_delta": float((compare_output.ending_arr or 0) - (base_output.ending_arr or 0)),
            "cash_delta": float((compare_output.ending_cash or 0) - (base_output.ending_cash or 0)),
            "hiring_capacity_delta": (compare_output.max_additional_hires or 0) - (base_output.max_additional_hires or 0)
        }
        
        comparison = ScenarioComparison(
            base_scenario_id=base_scenario_id,
            compare_scenario_id=compare_scenario_id,
            comparison_json=comparison_data,
            summary=self._generate_comparison_summary(comparison_data)
        )
        self.db.add(comparison)
        self.db.commit()
        
        return comparison
    
    def _generate_comparison_summary(self, data: Dict) -> str:
        """Generate human-readable comparison summary."""
        parts = []
        
        if data["runway_delta"] != 0:
            direction = "extends" if data["runway_delta"] > 0 else "reduces"
            parts.append(f"Runway {direction} by {abs(data['runway_delta'])} months")
        
        if data["burn_delta"] != 0:
            direction = "increases" if data["burn_delta"] > 0 else "decreases"
            parts.append(f"Burn {direction} by ${abs(data['burn_delta']):,.0f}")
        
        if data["arr_delta"] != 0:
            direction = "higher" if data["arr_delta"] > 0 else "lower"
            parts.append(f"ARR is ${abs(data['arr_delta']):,.0f} {direction}")
        
        return ". ".join(parts) if parts else "No significant differences"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_scenario(self, scenario_id: int) -> Optional[StartupPlanningScenario]:
        return self.db.query(StartupPlanningScenario).filter(
            StartupPlanningScenario.id == scenario_id
        ).first()
    
    def get_scenarios(self, entity_id: int) -> List[StartupPlanningScenario]:
        return self.db.query(StartupPlanningScenario).filter(
            StartupPlanningScenario.entity_id == entity_id
        ).order_by(StartupPlanningScenario.created_at.desc()).all()
    
    def get_output(self, scenario_id: int) -> Optional[PlanningOutput]:
        return self.db.query(PlanningOutput).filter(
            PlanningOutput.scenario_id == scenario_id
        ).first()
