"""
FP&A Evaluation Harness

Testing framework for FP&A system correctness:
- Determinism tests
- Invariant checks
- Trust report generation
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
import hashlib
import json
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from fpa_models import (
    Plan, AssumptionSet, Driver, ActualsSnapshot, ForecastRun,
    FPAArtifact, FPADecision, VarianceReport
)
from fpa_compute_engine import FPAComputeEngine

logger = logging.getLogger(__name__)


# =============================================================================
# TRUST REPORT STRUCTURES
# =============================================================================

@dataclass
class TrustMetric:
    """A single trust metric"""
    key: str
    name: str
    value: Any
    unit: str
    status: str  # "pass", "warn", "fail"
    threshold: Optional[Any] = None
    evidence_refs: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "name": self.name,
            "value": str(self.value) if isinstance(self.value, Decimal) else self.value,
            "unit": self.unit,
            "status": self.status,
            "threshold": str(self.threshold) if isinstance(self.threshold, Decimal) else self.threshold,
            "evidence_refs": self.evidence_refs,
        }


@dataclass
class InvariantResult:
    """Result of an invariant check"""
    name: str
    passed: bool
    severity: str  # "critical", "high", "medium", "low"
    message: str
    details: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class FPATrustReport:
    """Complete trust report for FP&A system state"""
    entity_id: int
    generated_at: datetime
    
    # Overall score
    trust_score: Decimal  # 0-100
    lock_eligible: bool
    
    # Metrics
    metrics: List[TrustMetric]
    
    # Invariant checks
    invariant_results: List[InvariantResult]
    
    # Gate failures
    gate_failures: List[str]
    
    # Evidence
    evidence_summary: Dict
    
    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "generated_at": self.generated_at.isoformat(),
            "trust_score": str(self.trust_score),
            "lock_eligible": self.lock_eligible,
            "metrics": [m.to_dict() for m in self.metrics],
            "invariant_results": [i.to_dict() for i in self.invariant_results],
            "gate_failures": self.gate_failures,
            "evidence_summary": self.evidence_summary,
        }


# =============================================================================
# EVALUATION HARNESS
# =============================================================================

class FPAEvaluationHarness:
    """
    Evaluation framework for FP&A system.
    
    Provides:
    - Determinism testing
    - Invariant checking
    - Trust report generation
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.compute_engine = FPAComputeEngine(db)
    
    # =========================================================================
    # DETERMINISM TESTS
    # =========================================================================
    
    def test_forecast_determinism(
        self,
        forecast_run_id: int,
        num_runs: int = 3,
    ) -> Tuple[bool, Dict]:
        """
        Test that forecast produces identical outputs.
        
        Re-runs the forecast multiple times and compares hashes.
        """
        forecast_run = self.db.query(ForecastRun).filter(
            ForecastRun.id == forecast_run_id
        ).first()
        
        if not forecast_run:
            return False, {"error": "Forecast run not found"}
        
        original_hash = forecast_run.outputs_hash
        hashes = [original_hash]
        
        for i in range(num_runs):
            # Re-compute
            output = self.compute_engine.run_forecast(forecast_run_id)
            hashes.append(output.output_hash)
        
        all_match = len(set(hashes)) == 1
        
        return all_match, {
            "num_runs": num_runs + 1,
            "hashes": hashes,
            "all_match": all_match,
        }
    
    def test_scaling_invariant(
        self,
        plan_id: int,
        scale_factor: Decimal = Decimal("10"),
    ) -> Tuple[bool, Dict]:
        """
        Test that scaling inputs scales outputs proportionally.
        
        For linear relationships: 2x inputs = 2x outputs.
        """
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            return False, {"error": "Plan not found"}
        
        # Get latest assumption set
        assumption_set = self.db.query(AssumptionSet).filter(
            AssumptionSet.plan_id == plan_id
        ).order_by(AssumptionSet.version.desc()).first()
        
        if not assumption_set:
            return False, {"error": "No assumptions found"}
        
        # Run original forecast
        original_run = ForecastRun(
            plan_id=plan_id,
            assumption_set_id=assumption_set.id,
            run_label="Scaling test - original",
        )
        self.db.add(original_run)
        self.db.commit()
        
        original_output = self.compute_engine.run_forecast(original_run.id)
        
        # Create scaled assumption set
        scaled_set = AssumptionSet(
            plan_id=plan_id,
            version=assumption_set.version + 1,
            version_label="Scaling test - scaled",
        )
        self.db.add(scaled_set)
        self.db.flush()
        
        # Scale revenue drivers
        for driver in assumption_set.drivers:
            if driver.category == "revenue" or driver.key.startswith("base_"):
                scaled_value = driver.value * scale_factor
            else:
                scaled_value = driver.value
            
            new_driver = Driver(
                assumption_set_id=scaled_set.id,
                key=driver.key,
                value=scaled_value,
                category=driver.category,
                subcategory=driver.subcategory,
                unit=driver.unit,
                source=driver.source,
            )
            self.db.add(new_driver)
        
        self.db.commit()
        
        # Run scaled forecast
        scaled_run = ForecastRun(
            plan_id=plan_id,
            assumption_set_id=scaled_set.id,
            run_label="Scaling test - scaled",
        )
        self.db.add(scaled_run)
        self.db.commit()
        
        scaled_output = self.compute_engine.run_forecast(scaled_run.id)
        
        # Check scaling
        original_revenue = original_output.pl.total_revenue
        scaled_revenue = scaled_output.pl.total_revenue
        
        expected_ratio = scale_factor
        actual_ratio = scaled_revenue / original_revenue if original_revenue != 0 else Decimal("0")
        
        tolerance = Decimal("0.01")
        passed = abs(actual_ratio - expected_ratio) < tolerance
        
        return passed, {
            "scale_factor": str(scale_factor),
            "original_revenue": str(original_revenue),
            "scaled_revenue": str(scaled_revenue),
            "expected_ratio": str(expected_ratio),
            "actual_ratio": str(actual_ratio),
            "passed": passed,
        }
    
    # =========================================================================
    # INVARIANT CHECKS
    # =========================================================================
    
    def check_all_invariants(
        self,
        entity_id: int,
        plan_id: Optional[int] = None,
    ) -> List[InvariantResult]:
        """Run all invariant checks"""
        results = []
        
        # P&L invariants
        results.append(self._check_pl_reconciliation(entity_id, plan_id))
        
        # Cash invariants
        results.append(self._check_cash_bridge_reconciliation(entity_id, plan_id))
        
        # Sign convention invariants
        results.append(self._check_sign_conventions(entity_id, plan_id))
        
        # Data freshness invariants
        results.append(self._check_data_freshness(entity_id))
        
        # Decision queue invariants
        results.append(self._check_decision_queue(entity_id))
        
        return results
    
    def _check_pl_reconciliation(
        self,
        entity_id: int,
        plan_id: Optional[int],
    ) -> InvariantResult:
        """
        Check P&L reconciliation: EBITDA = Revenue - COGS - Opex
        """
        # Get latest forecast
        query = self.db.query(ForecastRun).join(Plan).filter(
            Plan.entity_id == entity_id
        )
        if plan_id:
            query = query.filter(ForecastRun.plan_id == plan_id)
        
        forecast = query.order_by(ForecastRun.created_at.desc()).first()
        
        if not forecast or not forecast.outputs_json:
            return InvariantResult(
                name="P&L Reconciliation",
                passed=True,  # No data to check
                severity="low",
                message="No forecast data available to check",
            )
        
        pl = forecast.outputs_json.get("pl", {})
        
        revenue = Decimal(str(pl.get("total_revenue", 0)))
        cogs = abs(Decimal(str(pl.get("total_cogs", 0))))
        opex = abs(Decimal(str(pl.get("total_opex", 0))))
        ebitda = Decimal(str(pl.get("total_ebitda", 0)))
        
        expected_ebitda = revenue - cogs - opex
        diff = abs(ebitda - expected_ebitda)
        
        tolerance = Decimal("0.01")
        passed = diff <= tolerance
        
        return InvariantResult(
            name="P&L Reconciliation",
            passed=passed,
            severity="critical" if not passed else "low",
            message=f"EBITDA reconciliation: expected €{expected_ebitda:,.2f}, got €{ebitda:,.2f}",
            details={
                "revenue": str(revenue),
                "cogs": str(cogs),
                "opex": str(opex),
                "ebitda": str(ebitda),
                "expected_ebitda": str(expected_ebitda),
                "difference": str(diff),
            },
        )
    
    def _check_cash_bridge_reconciliation(
        self,
        entity_id: int,
        plan_id: Optional[int],
    ) -> InvariantResult:
        """
        Check cash bridge: Ending = Starting + Net Cash Flow
        """
        query = self.db.query(ForecastRun).join(Plan).filter(
            Plan.entity_id == entity_id
        )
        if plan_id:
            query = query.filter(ForecastRun.plan_id == plan_id)
        
        forecast = query.order_by(ForecastRun.created_at.desc()).first()
        
        if not forecast or not forecast.outputs_json:
            return InvariantResult(
                name="Cash Bridge Reconciliation",
                passed=True,
                severity="low",
                message="No forecast data available to check",
            )
        
        cash = forecast.outputs_json.get("cash_bridge", {})
        
        starting = Decimal(str(cash.get("starting_cash", 0)))
        ending = Decimal(str(cash.get("ending_cash", 0)))
        
        # Sum all cash flow items
        items = cash.get("items", [])
        net_flow = sum(
            Decimal(str(item.get("total", 0)))
            for item in items
        )
        
        expected_ending = starting + net_flow
        diff = abs(ending - expected_ending)
        
        tolerance = Decimal("0.01")
        passed = diff <= tolerance
        
        return InvariantResult(
            name="Cash Bridge Reconciliation",
            passed=passed,
            severity="critical" if not passed else "low",
            message=f"Cash reconciliation: expected €{expected_ending:,.2f}, got €{ending:,.2f}",
            details={
                "starting": str(starting),
                "net_flow": str(net_flow),
                "ending": str(ending),
                "expected_ending": str(expected_ending),
            },
        )
    
    def _check_sign_conventions(
        self,
        entity_id: int,
        plan_id: Optional[int],
    ) -> InvariantResult:
        """
        Check sign conventions: expenses negative, revenue positive
        """
        query = self.db.query(ForecastRun).join(Plan).filter(
            Plan.entity_id == entity_id
        )
        if plan_id:
            query = query.filter(ForecastRun.plan_id == plan_id)
        
        forecast = query.order_by(ForecastRun.created_at.desc()).first()
        
        if not forecast or not forecast.outputs_json:
            return InvariantResult(
                name="Sign Conventions",
                passed=True,
                severity="low",
                message="No forecast data available to check",
            )
        
        pl = forecast.outputs_json.get("pl", {})
        
        violations = []
        
        # Revenue should be positive
        revenue = Decimal(str(pl.get("total_revenue", 0)))
        if revenue < 0:
            violations.append(f"Revenue is negative: {revenue}")
        
        # COGS and Opex should be negative (expenses)
        cogs = Decimal(str(pl.get("total_cogs", 0)))
        if cogs > 0:
            violations.append(f"COGS is positive: {cogs}")
        
        opex = Decimal(str(pl.get("total_opex", 0)))
        if opex > 0:
            violations.append(f"Opex is positive: {opex}")
        
        passed = len(violations) == 0
        
        return InvariantResult(
            name="Sign Conventions",
            passed=passed,
            severity="high" if not passed else "low",
            message="Sign conventions valid" if passed else f"Violations: {', '.join(violations)}",
            details={"violations": violations},
        )
    
    def _check_data_freshness(self, entity_id: int) -> InvariantResult:
        """
        Check data freshness requirements
        """
        # Get latest actuals
        latest_actuals = self.db.query(ActualsSnapshot).filter(
            ActualsSnapshot.entity_id == entity_id
        ).order_by(ActualsSnapshot.created_at.desc()).first()
        
        if not latest_actuals:
            return InvariantResult(
                name="Data Freshness",
                passed=False,
                severity="medium",
                message="No actuals data available",
            )
        
        age_hours = (datetime.utcnow() - latest_actuals.created_at).total_seconds() / 3600
        
        # Warn if data is more than 24 hours old
        passed = age_hours < 24
        
        return InvariantResult(
            name="Data Freshness",
            passed=passed,
            severity="medium" if not passed else "low",
            message=f"Latest actuals are {age_hours:.1f} hours old",
            details={
                "last_update": latest_actuals.created_at.isoformat(),
                "age_hours": age_hours,
            },
        )
    
    def _check_decision_queue(self, entity_id: int) -> InvariantResult:
        """
        Check decision queue health
        """
        # Count pending decisions
        pending_count = self.db.query(FPADecision).filter(
            FPADecision.entity_id == entity_id,
            FPADecision.status == "pending",
        ).count()
        
        # Count overdue
        overdue_count = self.db.query(FPADecision).filter(
            FPADecision.entity_id == entity_id,
            FPADecision.status == "pending",
            FPADecision.expires_at < datetime.utcnow(),
        ).count()
        
        passed = overdue_count == 0
        
        return InvariantResult(
            name="Decision Queue",
            passed=passed,
            severity="high" if overdue_count > 0 else "low",
            message=f"{pending_count} pending, {overdue_count} overdue",
            details={
                "pending": pending_count,
                "overdue": overdue_count,
            },
        )
    
    # =========================================================================
    # TRUST REPORT
    # =========================================================================
    
    def generate_trust_report(
        self,
        entity_id: int,
        plan_id: Optional[int] = None,
    ) -> FPATrustReport:
        """
        Generate comprehensive trust report.
        """
        metrics = []
        gate_failures = []
        
        # === METRICS ===
        
        # Forecast coverage
        forecast_count = self.db.query(ForecastRun).join(Plan).filter(
            Plan.entity_id == entity_id
        ).count()
        
        metrics.append(TrustMetric(
            key="forecast_coverage",
            name="Forecast Coverage",
            value=forecast_count,
            unit="runs",
            status="pass" if forecast_count > 0 else "fail",
        ))
        
        # Actuals availability
        actuals_count = self.db.query(ActualsSnapshot).filter(
            ActualsSnapshot.entity_id == entity_id,
            ActualsSnapshot.locked == True,
        ).count()
        
        metrics.append(TrustMetric(
            key="locked_actuals",
            name="Locked Actuals",
            value=actuals_count,
            unit="periods",
            status="pass" if actuals_count > 0 else "warn",
        ))
        
        # Pending decisions
        pending_decisions = self.db.query(FPADecision).filter(
            FPADecision.entity_id == entity_id,
            FPADecision.status == "pending",
        ).count()
        
        decision_status = "pass" if pending_decisions == 0 else "warn" if pending_decisions < 5 else "fail"
        metrics.append(TrustMetric(
            key="pending_decisions",
            name="Pending Decisions",
            value=pending_decisions,
            unit="decisions",
            status=decision_status,
            threshold=5,
        ))
        
        if pending_decisions >= 5:
            gate_failures.append("Too many pending decisions")
        
        # Data freshness
        latest_actuals = self.db.query(ActualsSnapshot).filter(
            ActualsSnapshot.entity_id == entity_id
        ).order_by(ActualsSnapshot.created_at.desc()).first()
        
        if latest_actuals:
            age_hours = (datetime.utcnow() - latest_actuals.created_at).total_seconds() / 3600
            freshness_status = "pass" if age_hours < 24 else "warn" if age_hours < 72 else "fail"
            
            metrics.append(TrustMetric(
                key="data_freshness",
                name="Data Freshness",
                value=round(age_hours, 1),
                unit="hours",
                status=freshness_status,
                threshold=24,
            ))
            
            if age_hours >= 72:
                gate_failures.append("Data too stale")
        else:
            metrics.append(TrustMetric(
                key="data_freshness",
                name="Data Freshness",
                value="N/A",
                unit="",
                status="fail",
            ))
            gate_failures.append("No actuals data")
        
        # === INVARIANTS ===
        invariant_results = self.check_all_invariants(entity_id, plan_id)
        
        # Check for critical failures
        for result in invariant_results:
            if not result.passed and result.severity == "critical":
                gate_failures.append(f"Invariant failed: {result.name}")
        
        # === TRUST SCORE ===
        # Calculate weighted score
        weights = {
            "pass": 100,
            "warn": 50,
            "fail": 0,
        }
        
        metric_scores = [weights.get(m.status, 0) for m in metrics]
        invariant_scores = [100 if r.passed else 0 for r in invariant_results]
        
        all_scores = metric_scores + invariant_scores
        trust_score = Decimal(str(sum(all_scores) / len(all_scores))) if all_scores else Decimal("0")
        
        # Lock eligibility
        lock_eligible = len(gate_failures) == 0 and trust_score >= Decimal("80")
        
        return FPATrustReport(
            entity_id=entity_id,
            generated_at=datetime.utcnow(),
            trust_score=trust_score.quantize(Decimal("0.1")),
            lock_eligible=lock_eligible,
            metrics=metrics,
            invariant_results=invariant_results,
            gate_failures=gate_failures,
            evidence_summary={
                "forecast_count": forecast_count,
                "actuals_count": actuals_count,
                "pending_decisions": pending_decisions,
            },
        )


# =============================================================================
# TEST UTILITIES
# =============================================================================

def run_golden_test(
    db: Session,
    entity_id: int,
    expected_totals: Dict[str, Decimal],
    tolerance: Decimal = Decimal("0.01"),
) -> Tuple[bool, Dict]:
    """
    Run golden test comparing outputs to expected values.
    """
    harness = FPAEvaluationHarness(db)
    
    # Get latest forecast
    forecast = db.query(ForecastRun).join(Plan).filter(
        Plan.entity_id == entity_id
    ).order_by(ForecastRun.created_at.desc()).first()
    
    if not forecast or not forecast.outputs_json:
        return False, {"error": "No forecast to test"}
    
    results = {}
    all_passed = True
    
    for key, expected in expected_totals.items():
        actual = None
        
        # Navigate to value based on key
        if key.startswith("pl."):
            actual = Decimal(str(forecast.outputs_json.get("pl", {}).get(key[3:], 0)))
        elif key.startswith("cash."):
            actual = Decimal(str(forecast.outputs_json.get("cash_bridge", {}).get(key[5:], 0)))
        elif key.startswith("runway."):
            actual = Decimal(str(forecast.outputs_json.get("runway", {}).get(key[7:], 0)))
        
        if actual is not None:
            diff = abs(actual - expected)
            passed = diff <= tolerance
            
            results[key] = {
                "expected": str(expected),
                "actual": str(actual),
                "diff": str(diff),
                "passed": passed,
            }
            
            if not passed:
                all_passed = False
        else:
            results[key] = {
                "expected": str(expected),
                "actual": None,
                "error": "Key not found",
                "passed": False,
            }
            all_passed = False
    
    return all_passed, results
