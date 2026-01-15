"""
Hard Conservation + No-Overmatch Tests

Hard check: Craft scenarios that must end correctly (no "create money", no over-allocation)
"""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime
from reconciliation_service_v2_enhanced import EnhancedConstrainedAllocationSolver, MatchCandidate


def test_conservation_txn_amount_exceeds_total_open():
    """
    Hard check: Transaction amount > total open invoices.
    Must end with remainder as fee/writeoff/unknown, not "create money".
    """
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 50000.0  # Large transaction
    
    # Small open amounts (total = 30000)
    candidates = [
        MatchCandidate(
            invoice_id=i,
            invoice_number=f"INV-{i:03d}",
            customer_name=f"Customer {i}",
            open_amount=10000.0,  # Each invoice has 10k open
            due_date=datetime.now(),
            currency="EUR",
            ref_match=(i % 2 == 0),
            confidence=0.8
        )
        for i in range(1, 4)  # 3 invoices = 30k total
    ]
    
    solution = solver.solve(txn_amount, candidates, fees=0.0, writeoffs=0.0)
    
    # Verify conservation
    proof = solver.verify_conservation(solution, txn_amount)
    
    assert proof["is_conserved"], f"Conservation failed: {proof['proof']}"
    
    # Total allocated should not exceed total open amounts
    total_open = sum(c.open_amount for c in candidates)
    total_allocated = sum(solution.allocations.values())
    
    assert total_allocated <= total_open + 0.01, \
        f"Allocated {total_allocated} exceeds total open {total_open}"
    
    # Remainder should be in unallocated (not "created money")
    expected_unallocated = txn_amount - total_allocated
    assert abs(solution.unallocated - expected_unallocated) < 0.01, \
        f"Unallocated {solution.unallocated} doesn't match expected {expected_unallocated}"


def test_no_overmatch_with_existing_partial_allocations():
    """
    Hard check: Invoice already has partial allocation.
    New allocation must not exceed remaining open amount.
    """
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 15000.0
    
    # Invoice with existing allocation
    existing_allocations = {
        1: 8000.0  # Already allocated 8k
    }
    
    candidates = [
        MatchCandidate(
            invoice_id=1,
            invoice_number="INV-001",
            customer_name="Customer A",
            open_amount=10000.0,  # Total open is 10k
            due_date=datetime.now(),
            currency="EUR",
            ref_match=True,
            confidence=0.95
        )
    ]
    
    solution = solver.solve(txn_amount, candidates, existing_allocations=existing_allocations)
    
    # Verify no-overmatch
    proof = solver.verify_no_overmatch(solution, candidates, existing_allocations)
    
    assert proof["no_overmatch"], f"Overmatch detected: {proof['violations']}"
    assert len(proof["violations"]) == 0
    
    # Allocation should be at most remaining open (10k - 8k = 2k)
    if solution.allocations:
        alloc = solution.allocations.get(1, 0.0)
        remaining_open = 10000.0 - 8000.0
        assert alloc <= remaining_open + 0.01, \
            f"Allocation {alloc} exceeds remaining open {remaining_open}"


def test_conservation_with_fees_and_writeoffs():
    """
    Hard check: Fees and writeoffs must be accounted for in conservation.
    """
    solver = EnhancedConstrainedAllocationSolver()
    
    txn_amount = 10000.0
    fees = 200.0
    writeoffs = 100.0
    
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
    
    # Verify conservation includes fees and writeoffs
    proof = solver.verify_conservation(solution, txn_amount)
    
    assert proof["is_conserved"], f"Conservation failed: {proof['proof']}"
    assert proof["fees"] == fees
    assert proof["writeoffs"] == writeoffs
    
    # Net amount should be allocated
    net_amount = abs(txn_amount) - fees - writeoffs
    total_allocated = sum(solution.allocations.values())
    
    # Either fully allocated or remainder in unallocated
    assert abs(total_allocated + solution.unallocated - net_amount) < 0.01, \
        f"Allocation + unallocated {total_allocated + solution.unallocated} doesn't equal net {net_amount}"


def test_no_overmatch_multiple_transactions_same_invoice():
    """
    Hard check: Multiple transactions allocating to same invoice.
    Total must not exceed open amount.
    """
    solver = EnhancedConstrainedAllocationSolver()
    
    invoice_open_amount = 20000.0
    
    # First transaction
    txn1_amount = 12000.0
    candidates1 = [
        MatchCandidate(
            invoice_id=1,
            invoice_number="INV-001",
            customer_name="Customer A",
            open_amount=invoice_open_amount,
            due_date=datetime.now(),
            currency="EUR",
            ref_match=True,
            confidence=0.95
        )
    ]
    
    solution1 = solver.solve(txn1_amount, candidates1)
    
    # Second transaction (after first allocation)
    existing_allocations = {1: solution1.allocations.get(1, 0.0)}
    
    txn2_amount = 15000.0
    candidates2 = [
        MatchCandidate(
            invoice_id=1,
            invoice_number="INV-001",
            customer_name="Customer A",
            open_amount=invoice_open_amount,  # Still shows full open amount
            due_date=datetime.now(),
            currency="EUR",
            ref_match=True,
            confidence=0.95
        )
    ]
    
    solution2 = solver.solve(txn2_amount, candidates2, existing_allocations=existing_allocations)
    
    # Verify no-overmatch
    proof2 = solver.verify_no_overmatch(solution2, candidates2, existing_allocations)
    
    assert proof2["no_overmatch"], f"Overmatch detected: {proof2['violations']}"
    
    # Total allocations should not exceed open amount
    total_allocated = existing_allocations[1] + solution2.allocations.get(1, 0.0)
    assert total_allocated <= invoice_open_amount + 0.01, \
        f"Total allocated {total_allocated} exceeds open amount {invoice_open_amount}"


def test_conservation_proof_human_readable():
    """Hard check: Conservation proof must be human-readable for audit."""
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
    proof = solver.verify_conservation(solution, txn_amount)
    
    # Proof string must be human-readable
    assert "proof" in proof
    assert isinstance(proof["proof"], str)
    assert len(proof["proof"]) > 20, "Proof string too short"
    
    # Must contain calculation
    assert "+" in proof["proof"] or "=" in proof["proof"], "Proof should show calculation"
    
    # Must show expected vs actual
    assert "expected" in proof["proof"].lower() or str(proof["expected_total"]) in proof["proof"]


