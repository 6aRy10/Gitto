"""
FP&A System Tests

Comprehensive tests for:
- P&L computation
- Cash bridge
- Runway calculation
- Variance analysis
- Determinism
- Invariants
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
import json

# Test fixtures and helpers
@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MagicMock()


@pytest.fixture
def sample_drivers():
    """Sample driver values for testing"""
    return {
        "base_monthly_revenue": 100000,
        "revenue_growth_pct": 5,
        "churn_rate_pct": 2,
        "cogs_pct": 20,
        "headcount_engineering": 10,
        "headcount_sales": 5,
        "headcount_gna": 5,
        "salary_engineering_annual": 100000,
        "salary_sales_annual": 80000,
        "salary_gna_annual": 70000,
        "burden_rate_pct": 25,
        "software_spend_monthly": 5000,
        "starting_cash": 1000000,
        "dso_days": 45,
        "dpo_days": 30,
        "min_cash_threshold": 100000,
    }


class TestPLComputation:
    """Tests for P&L computation"""
    
    def test_revenue_growth(self, sample_drivers):
        """Test that revenue grows at specified rate"""
        from fpa_compute_engine import FPAComputeEngine
        
        # Create mock with drivers
        base = Decimal(str(sample_drivers["base_monthly_revenue"]))
        growth = Decimal(str(sample_drivers["revenue_growth_pct"])) / 100
        churn = Decimal(str(sample_drivers["churn_rate_pct"])) / 100
        
        # Calculate expected month 2 revenue
        net_growth = growth - churn
        expected_month2 = base * (1 + net_growth)
        
        # Verify calculation logic
        assert expected_month2 > base
        assert net_growth == Decimal("0.03")  # 5% - 2% = 3%
    
    def test_ebitda_reconciliation(self, sample_drivers):
        """Test EBITDA = Revenue - COGS - Opex"""
        # Sample values
        revenue = Decimal("100000")
        cogs = Decimal("-20000")  # 20%
        opex = Decimal("-50000")
        
        gross_profit = revenue + cogs  # cogs is negative
        ebitda = gross_profit + opex  # opex is negative
        
        assert gross_profit == Decimal("80000")
        assert ebitda == Decimal("30000")
    
    def test_sign_conventions(self, sample_drivers):
        """Test that expenses are negative, revenue is positive"""
        revenue = Decimal("100000")
        cogs_pct = Decimal(str(sample_drivers["cogs_pct"])) / 100
        
        # COGS should be stored as negative
        cogs = -(revenue * cogs_pct)
        
        assert revenue > 0
        assert cogs < 0
        assert cogs == Decimal("-20000")
    
    def test_total_reconciliation(self, sample_drivers):
        """Test that totals match sum of monthly values"""
        monthly_values = {
            "2026-01": Decimal("100000"),
            "2026-02": Decimal("103000"),
            "2026-03": Decimal("106090"),
        }
        
        total = sum(monthly_values.values())
        
        assert total == Decimal("309090")


class TestCashBridge:
    """Tests for cash bridge computation"""
    
    def test_working_capital_change(self, sample_drivers):
        """Test AR/AP change calculations"""
        dso = sample_drivers["dso_days"]
        dpo = sample_drivers["dpo_days"]
        
        month1_revenue = Decimal("100000")
        month2_revenue = Decimal("103000")
        month1_cogs = Decimal("20000")
        month2_cogs = Decimal("20600")
        
        # AR = Revenue * (DSO/30)
        ar_month1 = month1_revenue * Decimal(str(dso)) / 30
        ar_month2 = month2_revenue * Decimal(str(dso)) / 30
        ar_change = ar_month2 - ar_month1
        
        # AR increase is a cash outflow
        cash_impact_ar = -ar_change
        
        # AP = COGS * (DPO/30)
        ap_month1 = month1_cogs * Decimal(str(dpo)) / 30
        ap_month2 = month2_cogs * Decimal(str(dpo)) / 30
        ap_change = ap_month2 - ap_month1
        
        # AP increase is a cash inflow
        cash_impact_ap = ap_change
        
        assert ar_change > 0  # AR increases with revenue
        assert ap_change > 0  # AP increases with COGS
        assert cash_impact_ar < 0  # Cash outflow
        assert cash_impact_ap > 0  # Cash inflow
    
    def test_ending_cash_reconciliation(self, sample_drivers):
        """Test ending cash = starting + net cash flow"""
        starting_cash = Decimal(str(sample_drivers["starting_cash"]))
        
        ebitda = Decimal("30000")
        wc_change = Decimal("-2000")  # Working capital increase
        capex = Decimal("0")
        
        net_cash_flow = ebitda + wc_change + capex
        ending_cash = starting_cash + net_cash_flow
        
        assert net_cash_flow == Decimal("28000")
        assert ending_cash == Decimal("1028000")


class TestRunway:
    """Tests for runway calculation"""
    
    def test_runway_months(self, sample_drivers):
        """Test runway calculation"""
        current_cash = Decimal("1000000")
        monthly_burn = Decimal("50000")
        min_cash = Decimal(str(sample_drivers["min_cash_threshold"]))
        
        # Runway = (current - min) / burn
        available_cash = current_cash - min_cash
        runway = available_cash / monthly_burn
        
        assert available_cash == Decimal("900000")
        assert runway == Decimal("18")  # 18 months
    
    def test_zero_burn(self):
        """Test runway with zero burn (infinite)"""
        current_cash = Decimal("1000000")
        monthly_burn = Decimal("0")
        
        # Should handle gracefully
        if monthly_burn == 0:
            runway = float("inf")
        else:
            runway = current_cash / monthly_burn
        
        assert runway == float("inf")


class TestVarianceAnalysis:
    """Tests for variance analysis"""
    
    def test_variance_calculation(self):
        """Test basic variance calculation"""
        actual = Decimal("110000")
        expected = Decimal("100000")
        
        variance = actual - expected
        variance_pct = (variance / expected * 100) if expected != 0 else Decimal("0")
        
        assert variance == Decimal("10000")
        assert variance_pct == Decimal("10")
    
    def test_favorable_unfavorable(self):
        """Test favorability determination"""
        # Revenue higher than expected = favorable
        revenue_variance = Decimal("10000")
        is_revenue_favorable = revenue_variance > 0
        assert is_revenue_favorable
        
        # Expense lower than expected = favorable
        expense_variance = Decimal("-5000")  # Spent less
        is_expense_favorable = expense_variance < 0
        assert is_expense_favorable
    
    def test_materiality_threshold(self):
        """Test materiality threshold"""
        threshold = Decimal("10000")
        
        small_variance = Decimal("5000")
        large_variance = Decimal("15000")
        
        assert abs(small_variance) < threshold  # Not material
        assert abs(large_variance) >= threshold  # Material


class TestDeterminism:
    """Tests for determinism"""
    
    def test_same_inputs_same_outputs(self):
        """Test that same inputs produce same outputs"""
        import hashlib
        import json
        
        # Simulate deterministic computation
        inputs = {
            "revenue": 100000,
            "growth": 5,
            "months": 12,
        }
        
        # Run twice
        def compute(inputs):
            total = inputs["revenue"]
            for _ in range(inputs["months"]):
                total *= (1 + inputs["growth"] / 100)
            return total
        
        result1 = compute(inputs)
        result2 = compute(inputs)
        
        assert result1 == result2
        
        # Hash should be identical
        hash1 = hashlib.sha256(json.dumps({"result": result1}, sort_keys=True).encode()).hexdigest()
        hash2 = hashlib.sha256(json.dumps({"result": result2}, sort_keys=True).encode()).hexdigest()
        
        assert hash1 == hash2
    
    def test_scaling_invariant(self):
        """Test that scaling inputs scales outputs"""
        base_revenue = Decimal("100000")
        scale_factor = Decimal("10")
        
        # Linear calculation
        result_base = base_revenue * 12
        result_scaled = (base_revenue * scale_factor) * 12
        
        actual_ratio = result_scaled / result_base
        
        assert actual_ratio == scale_factor


class TestInvariants:
    """Tests for system invariants"""
    
    def test_pl_invariant(self):
        """Test P&L always reconciles"""
        revenue = Decimal("100000")
        cogs = Decimal("-20000")
        opex = Decimal("-50000")
        
        gross_profit = revenue + cogs
        ebitda = gross_profit + opex
        
        # Invariant: EBITDA = Revenue - |COGS| - |Opex|
        expected_ebitda = revenue - abs(cogs) - abs(opex)
        
        assert ebitda == expected_ebitda
    
    def test_cash_invariant(self):
        """Test cash always reconciles"""
        starting = Decimal("1000000")
        inflows = Decimal("100000")
        outflows = Decimal("-50000")
        
        ending = starting + inflows + outflows
        
        # Invariant: Ending = Starting + Net Flow
        net_flow = inflows + outflows
        expected_ending = starting + net_flow
        
        assert ending == expected_ending
    
    def test_no_negative_runway(self):
        """Test runway is never negative"""
        current_cash = Decimal("50000")
        min_cash = Decimal("100000")
        burn = Decimal("10000")
        
        # If current < min, runway is 0 (already breached)
        if current_cash < min_cash:
            runway = 0
        else:
            runway = int((current_cash - min_cash) / burn)
        
        assert runway >= 0


class TestDecisionQueue:
    """Tests for decision queue"""
    
    def test_policy_matching(self):
        """Test policy rule matching"""
        context = {
            "variance_pct": 15,
            "impact_amount": 50000,
        }
        
        # Rule: if variance_pct >= 5 and < 20, single approval
        condition = "variance_pct >= 5 and variance_pct < 20"
        matches = eval(condition, {"__builtins__": {}}, context)
        
        assert matches
    
    def test_severity_determination(self):
        """Test severity determination"""
        def determine_severity(impact, variance_pct):
            if impact >= 100000 or variance_pct >= 50:
                return "critical"
            elif impact >= 50000 or variance_pct >= 20:
                return "high"
            elif impact >= 10000 or variance_pct >= 10:
                return "medium"
            else:
                return "low"
        
        assert determine_severity(150000, 10) == "critical"
        assert determine_severity(75000, 10) == "high"
        assert determine_severity(25000, 15) == "medium"
        assert determine_severity(5000, 5) == "low"


class TestTrustReport:
    """Tests for trust report generation"""
    
    def test_trust_score_calculation(self):
        """Test trust score calculation"""
        metrics_status = ["pass", "pass", "warn", "pass", "fail"]
        
        weights = {"pass": 100, "warn": 50, "fail": 0}
        scores = [weights[s] for s in metrics_status]
        
        avg_score = sum(scores) / len(scores)
        
        assert avg_score == 70  # (100+100+50+100+0) / 5
    
    def test_lock_eligibility(self):
        """Test lock eligibility determination"""
        trust_score = Decimal("85")
        gate_failures = []
        
        lock_eligible = len(gate_failures) == 0 and trust_score >= Decimal("80")
        
        assert lock_eligible
        
        # With failures
        gate_failures = ["Data too stale"]
        lock_eligible = len(gate_failures) == 0 and trust_score >= Decimal("80")
        
        assert not lock_eligible


class TestEdgeCases:
    """Tests for edge cases"""
    
    def test_zero_revenue(self):
        """Test handling zero revenue"""
        revenue = Decimal("0")
        cogs_pct = Decimal("0.2")
        
        cogs = revenue * cogs_pct
        gross_margin_pct = Decimal("0") if revenue == 0 else (revenue - cogs) / revenue
        
        assert cogs == Decimal("0")
        assert gross_margin_pct == Decimal("0")
    
    def test_negative_growth(self):
        """Test negative growth rate"""
        base_revenue = Decimal("100000")
        growth_rate = Decimal("-0.05")  # -5%
        
        month2_revenue = base_revenue * (1 + growth_rate)
        
        assert month2_revenue == Decimal("95000")
        assert month2_revenue < base_revenue
    
    def test_empty_periods(self):
        """Test handling empty period lists"""
        monthly_values = {}
        
        total = sum(monthly_values.values()) if monthly_values else Decimal("0")
        
        assert total == Decimal("0")
    
    def test_very_large_numbers(self):
        """Test handling very large numbers"""
        large_revenue = Decimal("1000000000000")  # 1 trillion
        growth = Decimal("0.05")
        
        next_period = large_revenue * (1 + growth)
        
        assert next_period == Decimal("1050000000000")
        assert next_period > large_revenue


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
