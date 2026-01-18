"""
Deterministic FP&A Compute Engine

Produces P&L, Cash Bridge, Runway, and KPIs from actuals + assumptions.
Key invariant: same inputs = same outputs (reproducible).
"""

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
import hashlib
import json
import logging

from sqlalchemy.orm import Session

from fpa_models import (
    Plan, AssumptionSet, Driver, ActualsSnapshot, ForecastRun
)

logger = logging.getLogger(__name__)


# =============================================================================
# OUTPUT DATA STRUCTURES
# =============================================================================

@dataclass
class PLLineItem:
    """A single P&L line item"""
    category: str  # "revenue", "cogs", "opex"
    subcategory: str
    label: str
    monthly_values: Dict[str, Decimal]  # {YYYY-MM: amount}
    total: Decimal = Decimal("0")
    evidence_refs: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "label": self.label,
            "monthly_values": {k: str(v) for k, v in self.monthly_values.items()},
            "total": str(self.total),
            "evidence_refs": self.evidence_refs,
        }


@dataclass
class PLOutput:
    """P&L statement output"""
    period_start: date
    period_end: date
    line_items: List[PLLineItem]
    
    # Computed totals by month
    revenue_by_month: Dict[str, Decimal] = field(default_factory=dict)
    cogs_by_month: Dict[str, Decimal] = field(default_factory=dict)
    opex_by_month: Dict[str, Decimal] = field(default_factory=dict)
    gross_profit_by_month: Dict[str, Decimal] = field(default_factory=dict)
    ebitda_by_month: Dict[str, Decimal] = field(default_factory=dict)
    
    # Grand totals
    total_revenue: Decimal = Decimal("0")
    total_cogs: Decimal = Decimal("0")
    total_opex: Decimal = Decimal("0")
    total_gross_profit: Decimal = Decimal("0")
    total_ebitda: Decimal = Decimal("0")
    
    def to_dict(self) -> Dict:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "line_items": [li.to_dict() for li in self.line_items],
            "revenue_by_month": {k: str(v) for k, v in self.revenue_by_month.items()},
            "cogs_by_month": {k: str(v) for k, v in self.cogs_by_month.items()},
            "opex_by_month": {k: str(v) for k, v in self.opex_by_month.items()},
            "gross_profit_by_month": {k: str(v) for k, v in self.gross_profit_by_month.items()},
            "ebitda_by_month": {k: str(v) for k, v in self.ebitda_by_month.items()},
            "total_revenue": str(self.total_revenue),
            "total_cogs": str(self.total_cogs),
            "total_opex": str(self.total_opex),
            "total_gross_profit": str(self.total_gross_profit),
            "total_ebitda": str(self.total_ebitda),
        }


@dataclass
class CashBridgeItem:
    """A single cash bridge line item"""
    category: str  # "operating", "working_capital", "investing", "financing"
    label: str
    monthly_values: Dict[str, Decimal]  # Weekly overlay can be nested
    weekly_values: Optional[Dict[str, Decimal]] = None
    total: Decimal = Decimal("0")
    evidence_refs: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "label": self.label,
            "monthly_values": {k: str(v) for k, v in self.monthly_values.items()},
            "weekly_values": {k: str(v) for k, v in (self.weekly_values or {}).items()},
            "total": str(self.total),
            "evidence_refs": self.evidence_refs,
        }


@dataclass
class CashBridgeOutput:
    """Cash bridge (EBITDA to ending cash)"""
    period_start: date
    period_end: date
    items: List[CashBridgeItem]
    
    # Key positions by month
    ebitda_by_month: Dict[str, Decimal] = field(default_factory=dict)
    working_capital_change_by_month: Dict[str, Decimal] = field(default_factory=dict)
    operating_cash_flow_by_month: Dict[str, Decimal] = field(default_factory=dict)
    ending_cash_by_month: Dict[str, Decimal] = field(default_factory=dict)
    
    # Weekly overlay for near-term
    ending_cash_by_week: Dict[str, Decimal] = field(default_factory=dict)
    
    # Starting and ending
    starting_cash: Decimal = Decimal("0")
    ending_cash: Decimal = Decimal("0")
    
    def to_dict(self) -> Dict:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "items": [i.to_dict() for i in self.items],
            "ebitda_by_month": {k: str(v) for k, v in self.ebitda_by_month.items()},
            "working_capital_change_by_month": {k: str(v) for k, v in self.working_capital_change_by_month.items()},
            "operating_cash_flow_by_month": {k: str(v) for k, v in self.operating_cash_flow_by_month.items()},
            "ending_cash_by_month": {k: str(v) for k, v in self.ending_cash_by_month.items()},
            "ending_cash_by_week": {k: str(v) for k, v in self.ending_cash_by_week.items()},
            "starting_cash": str(self.starting_cash),
            "ending_cash": str(self.ending_cash),
        }


@dataclass
class RunwayOutput:
    """Cash runway calculation"""
    runway_months: int
    runway_date: Optional[date]  # When cash goes below threshold
    min_cash_threshold: Decimal
    current_cash: Decimal
    average_monthly_burn: Decimal
    burn_trend: str  # "increasing", "stable", "decreasing"
    confidence: str  # "high", "medium", "low"
    
    # Monthly cash positions
    projected_cash_by_month: Dict[str, Decimal] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "runway_months": self.runway_months,
            "runway_date": self.runway_date.isoformat() if self.runway_date else None,
            "min_cash_threshold": str(self.min_cash_threshold),
            "current_cash": str(self.current_cash),
            "average_monthly_burn": str(self.average_monthly_burn),
            "burn_trend": self.burn_trend,
            "confidence": self.confidence,
            "projected_cash_by_month": {k: str(v) for k, v in self.projected_cash_by_month.items()},
        }


@dataclass
class KPIOutput:
    """Key performance indicators"""
    # SaaS metrics (if applicable)
    arr: Optional[Decimal] = None
    mrr: Optional[Decimal] = None
    arr_growth_pct: Optional[Decimal] = None
    churn_rate_pct: Optional[Decimal] = None
    net_revenue_retention_pct: Optional[Decimal] = None
    
    # Unit economics
    cac: Optional[Decimal] = None
    ltv: Optional[Decimal] = None
    ltv_cac_ratio: Optional[Decimal] = None
    payback_months: Optional[int] = None
    
    # Profitability
    gross_margin_pct: Decimal = Decimal("0")
    ebitda_margin_pct: Decimal = Decimal("0")
    
    # Cash efficiency
    burn_multiple: Optional[Decimal] = None
    rule_of_40: Optional[Decimal] = None
    
    # Trends
    kpi_by_month: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        result = {
            "gross_margin_pct": str(self.gross_margin_pct),
            "ebitda_margin_pct": str(self.ebitda_margin_pct),
            "kpi_by_month": self.kpi_by_month,
        }
        # Add optional fields
        for field_name in ['arr', 'mrr', 'arr_growth_pct', 'churn_rate_pct', 
                           'net_revenue_retention_pct', 'cac', 'ltv', 'ltv_cac_ratio',
                           'payback_months', 'burn_multiple', 'rule_of_40']:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = str(value) if isinstance(value, Decimal) else value
        return result


@dataclass
class ForecastOutput:
    """Complete forecast output"""
    pl: PLOutput
    cash_bridge: CashBridgeOutput
    runway: RunwayOutput
    kpis: KPIOutput
    
    # Metadata
    computed_at: datetime = field(default_factory=datetime.utcnow)
    compute_time_ms: int = 0
    output_hash: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "pl": self.pl.to_dict(),
            "cash_bridge": self.cash_bridge.to_dict(),
            "runway": self.runway.to_dict(),
            "kpis": self.kpis.to_dict(),
            "computed_at": self.computed_at.isoformat(),
            "compute_time_ms": self.compute_time_ms,
            "output_hash": self.output_hash,
        }


# =============================================================================
# COMPUTE ENGINE
# =============================================================================

class FPAComputeEngine:
    """
    Deterministic FP&A compute engine.
    
    Produces reproducible forecasts from actuals + assumptions.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def run_forecast(self, forecast_run_id: int) -> ForecastOutput:
        """
        Run a complete forecast computation.
        
        This is the main entry point. It:
        1. Loads the inputs (actuals + assumptions)
        2. Computes P&L
        3. Computes cash bridge
        4. Computes runway
        5. Computes KPIs
        6. Stores results
        """
        start_time = datetime.utcnow()
        
        # Load forecast run
        forecast_run = self.db.query(ForecastRun).filter(
            ForecastRun.id == forecast_run_id
        ).first()
        
        if not forecast_run:
            raise ValueError(f"Forecast run {forecast_run_id} not found")
        
        # Load plan
        plan = self.db.query(Plan).filter(Plan.id == forecast_run.plan_id).first()
        
        # Load assumptions
        assumption_set = self.db.query(AssumptionSet).filter(
            AssumptionSet.id == forecast_run.assumption_set_id
        ).first()
        
        # Load actuals (if provided)
        actuals = None
        if forecast_run.actuals_snapshot_id:
            actuals = self.db.query(ActualsSnapshot).filter(
                ActualsSnapshot.id == forecast_run.actuals_snapshot_id
            ).first()
        
        # Get drivers as dict
        drivers = self._get_drivers_dict(assumption_set)
        
        # Determine forecast period
        period_start = plan.period_start
        period_end = plan.period_end
        
        # Compute P&L
        pl_output = self.compute_pl(
            period_start, period_end,
            drivers, actuals
        )
        
        # Compute cash bridge
        cash_bridge_output = self.compute_cash_bridge(
            period_start, period_end,
            pl_output, drivers, actuals
        )
        
        # Compute runway
        runway_output = self.compute_runway(
            cash_bridge_output, drivers
        )
        
        # Compute KPIs
        kpi_output = self.compute_kpis(
            pl_output, cash_bridge_output, drivers
        )
        
        # Create output
        compute_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        output = ForecastOutput(
            pl=pl_output,
            cash_bridge=cash_bridge_output,
            runway=runway_output,
            kpis=kpi_output,
            computed_at=datetime.utcnow(),
            compute_time_ms=compute_time_ms,
        )
        
        # Compute hash for integrity
        output.output_hash = self._compute_output_hash(output)
        
        # Store results
        forecast_run.outputs_json = output.to_dict()
        forecast_run.metrics_json = {
            "total_revenue": str(pl_output.total_revenue),
            "total_ebitda": str(pl_output.total_ebitda),
            "ending_cash": str(cash_bridge_output.ending_cash),
            "runway_months": runway_output.runway_months,
        }
        forecast_run.total_revenue = pl_output.total_revenue
        forecast_run.total_ebitda = pl_output.total_ebitda
        forecast_run.ending_cash = cash_bridge_output.ending_cash
        forecast_run.runway_months = runway_output.runway_months
        forecast_run.outputs_hash = output.output_hash
        forecast_run.compute_time_ms = compute_time_ms
        
        self.db.commit()
        
        logger.info(f"Forecast {forecast_run_id} computed in {compute_time_ms}ms")
        
        return output
    
    def compute_pl(
        self,
        period_start: date,
        period_end: date,
        drivers: Dict[str, Any],
        actuals: Optional[ActualsSnapshot],
    ) -> PLOutput:
        """
        Compute P&L statement.
        
        Revenue, COGS, Opex, EBITDA by month.
        """
        months = self._get_months_in_range(period_start, period_end)
        line_items = []
        
        # === REVENUE ===
        revenue_items = self._compute_revenue(months, drivers, actuals)
        line_items.extend(revenue_items)
        
        # === COGS ===
        cogs_items = self._compute_cogs(months, drivers, actuals)
        line_items.extend(cogs_items)
        
        # === OPEX ===
        opex_items = self._compute_opex(months, drivers, actuals)
        line_items.extend(opex_items)
        
        # Calculate totals
        revenue_by_month = {}
        cogs_by_month = {}
        opex_by_month = {}
        
        for month in months:
            month_key = month.strftime("%Y-%m")
            revenue_by_month[month_key] = sum(
                li.monthly_values.get(month_key, Decimal("0"))
                for li in line_items if li.category == "revenue"
            )
            cogs_by_month[month_key] = sum(
                li.monthly_values.get(month_key, Decimal("0"))
                for li in line_items if li.category == "cogs"
            )
            opex_by_month[month_key] = sum(
                li.monthly_values.get(month_key, Decimal("0"))
                for li in line_items if li.category == "opex"
            )
        
        # Gross profit = Revenue - COGS
        gross_profit_by_month = {
            m: revenue_by_month[m] - cogs_by_month[m]
            for m in months_keys(months)
        }
        
        # EBITDA = Gross Profit - Opex
        ebitda_by_month = {
            m: gross_profit_by_month[m] - opex_by_month[m]
            for m in months_keys(months)
        }
        
        return PLOutput(
            period_start=period_start,
            period_end=period_end,
            line_items=line_items,
            revenue_by_month=revenue_by_month,
            cogs_by_month=cogs_by_month,
            opex_by_month=opex_by_month,
            gross_profit_by_month=gross_profit_by_month,
            ebitda_by_month=ebitda_by_month,
            total_revenue=sum(revenue_by_month.values()),
            total_cogs=sum(cogs_by_month.values()),
            total_opex=sum(opex_by_month.values()),
            total_gross_profit=sum(gross_profit_by_month.values()),
            total_ebitda=sum(ebitda_by_month.values()),
        )
    
    def _compute_revenue(
        self,
        months: List[date],
        drivers: Dict[str, Any],
        actuals: Optional[ActualsSnapshot],
    ) -> List[PLLineItem]:
        """Compute revenue line items"""
        items = []
        
        # Starting revenue (from actuals or driver)
        base_revenue = Decimal(str(drivers.get("base_monthly_revenue", 100000)))
        growth_rate = Decimal(str(drivers.get("revenue_growth_pct", 0))) / 100
        churn_rate = Decimal(str(drivers.get("churn_rate_pct", 0))) / 100
        
        if actuals and actuals.revenue_total:
            base_revenue = actuals.revenue_total
        
        # Compute monthly revenue with growth
        monthly_values = {}
        current_revenue = base_revenue
        
        for i, month in enumerate(months):
            month_key = month.strftime("%Y-%m")
            
            if i == 0:
                monthly_values[month_key] = current_revenue
            else:
                # Apply growth and churn
                gross_new = current_revenue * growth_rate
                churned = current_revenue * churn_rate
                current_revenue = current_revenue + gross_new - churned
                monthly_values[month_key] = current_revenue.quantize(Decimal("0.01"))
        
        items.append(PLLineItem(
            category="revenue",
            subcategory="subscription",
            label="Recurring Revenue",
            monthly_values=monthly_values,
            total=sum(monthly_values.values()),
        ))
        
        # One-time revenue (if driver exists)
        one_time_revenue = Decimal(str(drivers.get("one_time_revenue_monthly", 0)))
        if one_time_revenue > 0:
            monthly_values = {
                month.strftime("%Y-%m"): one_time_revenue
                for month in months
            }
            items.append(PLLineItem(
                category="revenue",
                subcategory="one_time",
                label="One-Time Revenue",
                monthly_values=monthly_values,
                total=sum(monthly_values.values()),
            ))
        
        return items
    
    def _compute_cogs(
        self,
        months: List[date],
        drivers: Dict[str, Any],
        actuals: Optional[ActualsSnapshot],
    ) -> List[PLLineItem]:
        """Compute COGS line items"""
        items = []
        
        # COGS as percentage of revenue
        cogs_pct = Decimal(str(drivers.get("cogs_pct", 20))) / 100
        
        # Get revenue to calculate COGS
        base_revenue = Decimal(str(drivers.get("base_monthly_revenue", 100000)))
        growth_rate = Decimal(str(drivers.get("revenue_growth_pct", 0))) / 100
        churn_rate = Decimal(str(drivers.get("churn_rate_pct", 0))) / 100
        
        if actuals and actuals.revenue_total:
            base_revenue = actuals.revenue_total
        
        monthly_values = {}
        current_revenue = base_revenue
        
        for i, month in enumerate(months):
            month_key = month.strftime("%Y-%m")
            
            if i > 0:
                gross_new = current_revenue * growth_rate
                churned = current_revenue * churn_rate
                current_revenue = current_revenue + gross_new - churned
            
            # COGS is negative (expense)
            monthly_values[month_key] = -(current_revenue * cogs_pct).quantize(Decimal("0.01"))
        
        items.append(PLLineItem(
            category="cogs",
            subcategory="direct",
            label="Cost of Revenue",
            monthly_values=monthly_values,
            total=sum(monthly_values.values()),
        ))
        
        return items
    
    def _compute_opex(
        self,
        months: List[date],
        drivers: Dict[str, Any],
        actuals: Optional[ActualsSnapshot],
    ) -> List[PLLineItem]:
        """Compute operating expense line items"""
        items = []
        
        # === PEOPLE COSTS ===
        # Headcount by department
        headcount_eng = int(drivers.get("headcount_engineering", 10))
        headcount_sales = int(drivers.get("headcount_sales", 5))
        headcount_gna = int(drivers.get("headcount_gna", 5))
        
        # Salary bands
        salary_eng = Decimal(str(drivers.get("salary_engineering_annual", 100000))) / 12
        salary_sales = Decimal(str(drivers.get("salary_sales_annual", 80000))) / 12
        salary_gna = Decimal(str(drivers.get("salary_gna_annual", 70000))) / 12
        
        # Burden rate (benefits, taxes)
        burden_rate = Decimal(str(drivers.get("burden_rate_pct", 25))) / 100
        
        # Headcount growth
        headcount_growth_rate = Decimal(str(drivers.get("headcount_growth_pct", 0))) / 100 / 12
        
        for dept, base_count, salary, label in [
            ("engineering", headcount_eng, salary_eng, "Engineering"),
            ("sales", headcount_sales, salary_sales, "Sales & Marketing"),
            ("gna", headcount_gna, salary_gna, "G&A"),
        ]:
            monthly_values = {}
            current_count = Decimal(str(base_count))
            
            for i, month in enumerate(months):
                month_key = month.strftime("%Y-%m")
                
                if i > 0:
                    current_count = current_count * (1 + headcount_growth_rate)
                
                # Total cost = count * salary * (1 + burden)
                cost = -(current_count * salary * (1 + burden_rate)).quantize(Decimal("0.01"))
                monthly_values[month_key] = cost
            
            items.append(PLLineItem(
                category="opex",
                subcategory="people",
                label=f"People - {label}",
                monthly_values=monthly_values,
                total=sum(monthly_values.values()),
            ))
        
        # === NON-PEOPLE COSTS ===
        # SaaS/software
        software_monthly = Decimal(str(drivers.get("software_spend_monthly", 5000)))
        if software_monthly > 0:
            monthly_values = {
                month.strftime("%Y-%m"): -software_monthly
                for month in months
            }
            items.append(PLLineItem(
                category="opex",
                subcategory="software",
                label="Software & Tools",
                monthly_values=monthly_values,
                total=sum(monthly_values.values()),
            ))
        
        # Office/facilities
        facilities_monthly = Decimal(str(drivers.get("facilities_spend_monthly", 0)))
        if facilities_monthly > 0:
            monthly_values = {
                month.strftime("%Y-%m"): -facilities_monthly
                for month in months
            }
            items.append(PLLineItem(
                category="opex",
                subcategory="facilities",
                label="Facilities & Office",
                monthly_values=monthly_values,
                total=sum(monthly_values.values()),
            ))
        
        # Marketing spend
        marketing_monthly = Decimal(str(drivers.get("marketing_spend_monthly", 0)))
        if marketing_monthly > 0:
            monthly_values = {
                month.strftime("%Y-%m"): -marketing_monthly
                for month in months
            }
            items.append(PLLineItem(
                category="opex",
                subcategory="marketing",
                label="Marketing & Advertising",
                monthly_values=monthly_values,
                total=sum(monthly_values.values()),
            ))
        
        # Other opex
        other_opex = Decimal(str(drivers.get("other_opex_monthly", 0)))
        if other_opex > 0:
            monthly_values = {
                month.strftime("%Y-%m"): -other_opex
                for month in months
            }
            items.append(PLLineItem(
                category="opex",
                subcategory="other",
                label="Other Operating Expenses",
                monthly_values=monthly_values,
                total=sum(monthly_values.values()),
            ))
        
        return items
    
    def compute_cash_bridge(
        self,
        period_start: date,
        period_end: date,
        pl: PLOutput,
        drivers: Dict[str, Any],
        actuals: Optional[ActualsSnapshot],
    ) -> CashBridgeOutput:
        """
        Compute cash bridge from EBITDA to ending cash.
        
        EBITDA
        +/- Change in AR (DSO)
        +/- Change in AP (DPO)
        +/- Other working capital
        = Operating cash flow
        +/- CapEx
        +/- Financing
        = Ending cash
        """
        months = self._get_months_in_range(period_start, period_end)
        items = []
        
        # Starting cash
        starting_cash = Decimal(str(drivers.get("starting_cash", 1000000)))
        if actuals and actuals.cash_ending:
            starting_cash = actuals.cash_ending
        
        # Working capital parameters
        dso_days = int(drivers.get("dso_days", 45))
        dpo_days = int(drivers.get("dpo_days", 30))
        
        # Calculate AR/AP changes
        ar_change_by_month = {}
        ap_change_by_month = {}
        
        prev_revenue = None
        prev_cogs = None
        
        for month in months:
            month_key = month.strftime("%Y-%m")
            revenue = pl.revenue_by_month.get(month_key, Decimal("0"))
            cogs = abs(pl.cogs_by_month.get(month_key, Decimal("0")))
            
            # AR change based on DSO
            # Simplified: AR = Revenue * (DSO/30)
            current_ar = revenue * Decimal(str(dso_days)) / 30
            if prev_revenue is not None:
                prev_ar = prev_revenue * Decimal(str(dso_days)) / 30
                ar_change = current_ar - prev_ar
            else:
                ar_change = Decimal("0")
            ar_change_by_month[month_key] = -ar_change  # Cash outflow when AR increases
            
            # AP change based on DPO
            current_ap = cogs * Decimal(str(dpo_days)) / 30
            if prev_cogs is not None:
                prev_ap = prev_cogs * Decimal(str(dpo_days)) / 30
                ap_change = current_ap - prev_ap
            else:
                ap_change = Decimal("0")
            ap_change_by_month[month_key] = ap_change  # Cash inflow when AP increases
            
            prev_revenue = revenue
            prev_cogs = cogs
        
        # Build items
        items.append(CashBridgeItem(
            category="operating",
            label="EBITDA",
            monthly_values=dict(pl.ebitda_by_month),
            total=pl.total_ebitda,
        ))
        
        items.append(CashBridgeItem(
            category="working_capital",
            label="Change in AR",
            monthly_values=ar_change_by_month,
            total=sum(ar_change_by_month.values()),
        ))
        
        items.append(CashBridgeItem(
            category="working_capital",
            label="Change in AP",
            monthly_values=ap_change_by_month,
            total=sum(ap_change_by_month.values()),
        ))
        
        # CapEx (if applicable)
        capex_monthly = Decimal(str(drivers.get("capex_monthly", 0)))
        if capex_monthly > 0:
            capex_values = {
                month.strftime("%Y-%m"): -capex_monthly
                for month in months
            }
            items.append(CashBridgeItem(
                category="investing",
                label="Capital Expenditures",
                monthly_values=capex_values,
                total=sum(capex_values.values()),
            ))
        
        # Calculate ending cash by month
        working_capital_change_by_month = {}
        operating_cash_flow_by_month = {}
        ending_cash_by_month = {}
        
        running_cash = starting_cash
        
        for month in months:
            month_key = month.strftime("%Y-%m")
            
            ebitda = pl.ebitda_by_month.get(month_key, Decimal("0"))
            wc_change = ar_change_by_month.get(month_key, Decimal("0")) + ap_change_by_month.get(month_key, Decimal("0"))
            capex = -capex_monthly if capex_monthly > 0 else Decimal("0")
            
            working_capital_change_by_month[month_key] = wc_change
            ocf = ebitda + wc_change
            operating_cash_flow_by_month[month_key] = ocf
            
            running_cash = running_cash + ocf + capex
            ending_cash_by_month[month_key] = running_cash.quantize(Decimal("0.01"))
        
        # Weekly overlay for first 13 weeks
        ending_cash_by_week = self._compute_weekly_cash_overlay(
            period_start, starting_cash, pl, drivers
        )
        
        return CashBridgeOutput(
            period_start=period_start,
            period_end=period_end,
            items=items,
            ebitda_by_month=dict(pl.ebitda_by_month),
            working_capital_change_by_month=working_capital_change_by_month,
            operating_cash_flow_by_month=operating_cash_flow_by_month,
            ending_cash_by_month=ending_cash_by_month,
            ending_cash_by_week=ending_cash_by_week,
            starting_cash=starting_cash,
            ending_cash=running_cash.quantize(Decimal("0.01")),
        )
    
    def _compute_weekly_cash_overlay(
        self,
        period_start: date,
        starting_cash: Decimal,
        pl: PLOutput,
        drivers: Dict[str, Any],
    ) -> Dict[str, Decimal]:
        """Compute weekly cash positions for first 13 weeks"""
        weekly_cash = {}
        running_cash = starting_cash
        
        # Get first month's values
        first_month_key = period_start.strftime("%Y-%m")
        monthly_ebitda = pl.ebitda_by_month.get(first_month_key, Decimal("0"))
        weekly_ebitda = monthly_ebitda / 4  # Simplified
        
        current_date = period_start
        for week in range(13):
            week_key = current_date.strftime("%Y-W%W")
            
            # Apply weekly cash flow
            running_cash = running_cash + weekly_ebitda
            weekly_cash[week_key] = running_cash.quantize(Decimal("0.01"))
            
            current_date = current_date + relativedelta(weeks=1)
        
        return weekly_cash
    
    def compute_runway(
        self,
        cash_bridge: CashBridgeOutput,
        drivers: Dict[str, Any],
    ) -> RunwayOutput:
        """
        Compute cash runway.
        
        Months until cash falls below minimum threshold.
        """
        min_cash = Decimal(str(drivers.get("min_cash_threshold", 100000)))
        
        # Get monthly cash positions
        months_sorted = sorted(cash_bridge.ending_cash_by_month.keys())
        
        if not months_sorted:
            return RunwayOutput(
                runway_months=0,
                runway_date=None,
                min_cash_threshold=min_cash,
                current_cash=cash_bridge.starting_cash,
                average_monthly_burn=Decimal("0"),
                burn_trend="unknown",
                confidence="low",
            )
        
        # Calculate average burn
        cash_values = [cash_bridge.ending_cash_by_month[m] for m in months_sorted]
        burns = []
        for i in range(1, len(cash_values)):
            burn = cash_values[i-1] - cash_values[i]
            if burn > 0:  # Only count when burning
                burns.append(burn)
        
        avg_burn = sum(burns) / len(burns) if burns else Decimal("0")
        
        # Find runway
        runway_months = len(months_sorted)
        runway_date = None
        
        for i, month_key in enumerate(months_sorted):
            if cash_bridge.ending_cash_by_month[month_key] < min_cash:
                runway_months = i
                runway_date = date.fromisoformat(f"{month_key}-01")
                break
        
        # Determine burn trend
        if len(burns) >= 3:
            recent_avg = sum(burns[-3:]) / 3
            older_avg = sum(burns[:3]) / 3 if len(burns) >= 6 else recent_avg
            
            if recent_avg > older_avg * Decimal("1.1"):
                burn_trend = "increasing"
            elif recent_avg < older_avg * Decimal("0.9"):
                burn_trend = "decreasing"
            else:
                burn_trend = "stable"
        else:
            burn_trend = "unknown"
        
        # Confidence based on data quality
        confidence = "high" if len(months_sorted) >= 12 else "medium" if len(months_sorted) >= 6 else "low"
        
        return RunwayOutput(
            runway_months=runway_months,
            runway_date=runway_date,
            min_cash_threshold=min_cash,
            current_cash=cash_bridge.starting_cash,
            average_monthly_burn=avg_burn.quantize(Decimal("0.01")),
            burn_trend=burn_trend,
            confidence=confidence,
            projected_cash_by_month=dict(cash_bridge.ending_cash_by_month),
        )
    
    def compute_kpis(
        self,
        pl: PLOutput,
        cash_bridge: CashBridgeOutput,
        drivers: Dict[str, Any],
    ) -> KPIOutput:
        """
        Compute key performance indicators.
        """
        kpi = KPIOutput()
        
        # Gross margin
        if pl.total_revenue != 0:
            kpi.gross_margin_pct = (pl.total_gross_profit / pl.total_revenue * 100).quantize(Decimal("0.1"))
        
        # EBITDA margin
        if pl.total_revenue != 0:
            kpi.ebitda_margin_pct = (pl.total_ebitda / pl.total_revenue * 100).quantize(Decimal("0.1"))
        
        # SaaS metrics (if applicable)
        is_saas = drivers.get("business_model") == "saas" or "churn_rate_pct" in drivers
        
        if is_saas:
            # MRR (last month's revenue)
            months_sorted = sorted(pl.revenue_by_month.keys())
            if months_sorted:
                kpi.mrr = pl.revenue_by_month[months_sorted[-1]]
                kpi.arr = kpi.mrr * 12
            
            # Growth rate
            if len(months_sorted) >= 2:
                first_rev = pl.revenue_by_month[months_sorted[0]]
                last_rev = pl.revenue_by_month[months_sorted[-1]]
                if first_rev != 0:
                    total_growth = (last_rev - first_rev) / first_rev
                    months_count = len(months_sorted)
                    kpi.arr_growth_pct = (total_growth / months_count * 12 * 100).quantize(Decimal("0.1"))
            
            # Churn
            kpi.churn_rate_pct = Decimal(str(drivers.get("churn_rate_pct", 0)))
            
            # CAC
            cac = drivers.get("cac")
            if cac:
                kpi.cac = Decimal(str(cac))
            
            # LTV
            if kpi.churn_rate_pct and kpi.churn_rate_pct > 0:
                arpu = kpi.mrr if kpi.mrr else Decimal("0")
                gm_pct = kpi.gross_margin_pct / 100
                kpi.ltv = (arpu * gm_pct / (kpi.churn_rate_pct / 100) * 12).quantize(Decimal("0.01"))
                
                if kpi.cac and kpi.cac > 0:
                    kpi.ltv_cac_ratio = (kpi.ltv / kpi.cac).quantize(Decimal("0.1"))
            
            # Payback months
            if kpi.cac and kpi.mrr and kpi.mrr > 0:
                monthly_contribution = kpi.mrr * (kpi.gross_margin_pct / 100)
                if monthly_contribution > 0:
                    kpi.payback_months = int((kpi.cac / monthly_contribution).quantize(Decimal("1")))
            
            # Burn multiple (net burn / net new ARR)
            # This requires more data than we have here
        
        # Rule of 40
        if kpi.arr_growth_pct is not None:
            kpi.rule_of_40 = kpi.arr_growth_pct + kpi.ebitda_margin_pct
        
        return kpi
    
    def _get_drivers_dict(self, assumption_set: AssumptionSet) -> Dict[str, Any]:
        """Convert drivers to a dictionary"""
        return {
            d.key: float(d.value) if d.unit != "text" else str(d.value)
            for d in assumption_set.drivers
        }
    
    def _get_months_in_range(self, start: date, end: date) -> List[date]:
        """Get list of first-of-month dates in range"""
        months = []
        current = start.replace(day=1)
        end_month = end.replace(day=1)
        
        while current <= end_month:
            months.append(current)
            current = current + relativedelta(months=1)
        
        return months
    
    def _compute_output_hash(self, output: ForecastOutput) -> str:
        """Compute SHA256 hash of output for integrity verification"""
        output_json = json.dumps(output.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(output_json.encode()).hexdigest()


def months_keys(months: List[date]) -> List[str]:
    """Convert month dates to YYYY-MM keys"""
    return [m.strftime("%Y-%m") for m in months]
