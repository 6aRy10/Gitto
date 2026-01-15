"""
Test Reconciliation Conservation Proofs

Verifies that sum(allocations) + fees + writeoffs == txn_amount
"""

import pytest
from sqlalchemy.orm import Session
from decimal import Decimal
import models
from reconciliation_service_v2_enhanced import EnhancedConstrainedAllocationSolver, MatchCandidate
from datetime import datetime


def test_conservation_proof_single_allocation(db_session: Session):
    """Test conservation for single invoice allocation."""
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 10000.0
    candidates = [
        MatchCandidate(
            invoice_id=1,
            invoice_number="INV-001",
            customer_name="Customer A",
            open_amount=12000.0,
            due_date=datetime.now(),
            currency="EUR",
            ref_match=True,
            amount_match=True,
            confidence=0.95
        )
    ]
    
    solution = solver.solve(txn_amount, candidates, fees=0.0, writeoffs=0.0)
    
    # Verify conservation
    proof = solver.verify_conservation(solution, txn_amount)
    
    assert proof["is_conserved"], f"Conservation failed: {proof['proof']}"
    assert abs(proof["difference"]) < 0.01, f"Difference too large: {proof['difference']}"


def test_conservation_proof_many_to_many(db_session: Session):
    """Test conservation for many-to-many allocation."""
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 50000.0
    candidates = [
        MatchCandidate(
            invoice_id=i,
            invoice_number=f"INV-{i:03d}",
            customer_name=f"Customer {i}",
            open_amount=15000.0,
            due_date=datetime.now(),
            currency="EUR",
            ref_match=(i % 2 == 0),
            amount_match=True,
            confidence=0.8 + (i * 0.01)
        )
        for i in range(1, 6)  # 5 invoices
    ]
    
    solution = solver.solve(txn_amount, candidates, fees=500.0, writeoffs=200.0)
    
    # Verify conservation
    proof = solver.verify_conservation(solution, txn_amount)
    
    assert proof["is_conserved"], f"Conservation failed: {proof['proof']}"
    assert proof["fees"] == 500.0
    assert proof["writeoffs"] == 200.0
    assert abs(proof["difference"]) < 0.01


def test_no_overmatch_invariant(db_session: Session):
    """Test no-overmatch: allocation[i] <= open_amount[i]."""
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 20000.0
    candidates = [
        MatchCandidate(
            invoice_id=1,
            invoice_number="INV-001",
            customer_name="Customer A",
            open_amount=15000.0,  # Less than txn_amount
            due_date=datetime.now(),
            currency="EUR",
            ref_match=True,
            confidence=0.95
        )
    ]
    
    solution = solver.solve(txn_amount, candidates)
    
    # Verify no-overmatch
    proof = solver.verify_no_overmatch(solution, candidates)
    
    assert proof["no_overmatch"], f"Overmatch detected: {proof['violations']}"
    assert len(proof["violations"]) == 0
    
    # Verify allocation doesn't exceed open_amount
    if solution.allocations:
        alloc = solution.allocations.get(1, 0.0)
        assert alloc <= 15000.0 + 0.01, f"Allocation {alloc} exceeds open_amount 15000.0"


def test_no_overmatch_with_existing_allocations(db_session: Session):
    """Test no-overmatch when invoice already has partial allocation."""
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 10000.0
    existing_allocations = {1: 5000.0}  # Invoice 1 already has 5000 allocated
    
    candidates = [
        MatchCandidate(
            invoice_id=1,
            invoice_number="INV-001",
            customer_name="Customer A",
            open_amount=10000.0,  # Total open amount
            due_date=datetime.now(),
            currency="EUR",
            ref_match=True,
            confidence=0.95
        )
    ]
    
    solution = solver.solve(txn_amount, candidates, existing_allocations=existing_allocations)
    
    # Verify no-overmatch (should only allocate remaining 5000, not full 10000)
    proof = solver.verify_no_overmatch(solution, candidates, existing_allocations)
    
    assert proof["no_overmatch"], f"Overmatch detected: {proof['violations']}"
    
    # Verify allocation respects existing
    if solution.allocations:
        alloc = solution.allocations.get(1, 0.0)
        assert alloc <= 5000.0 + 0.01, f"Allocation {alloc} exceeds remaining open_amount 5000.0"


def test_conservation_with_fees_and_writeoffs(db_session: Session):
    """Test conservation when fees and writeoffs are present."""
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 10000.0
    fees = 150.0
    writeoffs = 50.0
    
    candidates = [
        MatchCandidate(
            invoice_id=1,
            invoice_number="INV-001",
            customer_name="Customer A",
            open_amount=15000.0,
            due_date=datetime.now(),
            currency="EUR",
            ref_match=True,
            confidence=0.95
        )
    ]
    
    solution = solver.solve(txn_amount, candidates, fees=fees, writeoffs=writeoffs)
    
    # Verify conservation
    proof = solver.verify_conservation(solution, txn_amount)
    
    assert proof["is_conserved"], f"Conservation failed: {proof['proof']}"
    assert proof["fees"] == fees
    assert proof["writeoffs"] == writeoffs
    
    # Net amount should be allocated
    expected_net = abs(txn_amount) - fees - writeoffs
    assert abs(proof["allocations_sum"] - expected_net) < 0.01 or abs(proof["unallocated"]) < 0.01


def test_conservation_proof_output_format(db_session: Session):
    """Test that conservation proof has required format."""
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 10000.0
    candidates = [
        MatchCandidate(
            invoice_id=1,
            invoice_number="INV-001",
            customer_name="Customer A",
            open_amount=12000.0,
            due_date=datetime.now(),
            currency="EUR",
            ref_match=True,
            confidence=0.95
        )
    ]
    
    solution = solver.solve(txn_amount, candidates)
    proof = solver.verify_conservation(solution, txn_amount)
    
    # Verify proof has all required fields
    required_fields = [
        "is_conserved", "expected_total", "actual_total", "difference",
        "allocations_sum", "fees", "writeoffs", "unallocated", "proof"
    ]
    
    for field in required_fields:
        assert field in proof, f"Missing field: {field}"
    
    # Verify proof string is human-readable
    assert "=" in proof["proof"] or "+" in proof["proof"], "Proof string should show calculation"


