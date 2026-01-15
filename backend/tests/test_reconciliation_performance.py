"""
Performance Tests for Reconciliation Service V2

Tests reconciliation performance with:
- 50,000 bank transactions
- 200,000 invoices
- Runtime threshold: < 60 seconds
"""

import pytest
import time
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import models
from reconciliation_service_v2 import ReconciliationServiceV2


@pytest.fixture
def large_dataset(db_session: Session):
    """Create large dataset: 50k transactions + 200k invoices."""
    entity = models.Entity(name="Test Entity", currency="EUR", payment_run_day=3)
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)
    
    bank_account = models.BankAccount(
        entity_id=entity.id,
        account_name="Test Account",
        account_number="ACC001",
        bank_name="Test Bank",
        currency="EUR",
        balance=0.0
    )
    db_session.add(bank_account)
    db_session.commit()
    db_session.refresh(bank_account)
    
    # Generate 200k invoices
    print("Generating 200,000 invoices...")
    invoices = []
    customers = [f"Customer-{i}" for i in range(100)]
    countries = ["US", "UK", "DE", "FR", "IT"]
    
    for i in range(200000):
        invoice = models.Invoice(
            entity_id=entity.id,
            document_number=f"INV-{i:06d}",
            customer=random.choice(customers),
            country=random.choice(countries),
            amount=random.uniform(100, 50000),
            currency="EUR",
            expected_due_date=datetime.now() + timedelta(days=random.randint(-30, 60)),
            payment_date=None,
            invoice_issue_date=datetime.now() - timedelta(days=random.randint(0, 90))
        )
        invoices.append(invoice)
    
    db_session.bulk_save_objects(invoices)
    db_session.commit()
    print(f"✓ Generated {len(invoices)} invoices")
    
    # Generate 50k transactions
    print("Generating 50,000 transactions...")
    transactions = []
    paid_invoices = random.sample(invoices, min(30000, len(invoices)))
    
    for i in range(50000):
        # 60% match to invoices, 40% random
        if i < 30000 and paid_invoices:
            inv = paid_invoices[i % len(paid_invoices)]
            amount = inv.amount
            reference = f"PAYMENT FOR {inv.document_number}"
            counterparty = inv.customer
        else:
            amount = random.uniform(100, 50000)
            reference = f"TXN-{i:06d}"
            counterparty = random.choice(customers)
        
        txn = models.BankTransaction(
            bank_account_id=bank_account.id,
            transaction_date=datetime.now() - timedelta(days=random.randint(0, 90)),
            amount=amount,
            currency="EUR",
            reference=reference,
            counterparty=counterparty,
            transaction_type="customer_receipt",
            is_reconciled=0
        )
        transactions.append(txn)
    
    db_session.bulk_save_objects(transactions)
    db_session.commit()
    print(f"✓ Generated {len(transactions)} transactions")
    
    return {
        "entity": entity,
        "bank_account": bank_account,
        "invoices": invoices,
        "transactions": transactions
    }


def test_reconciliation_performance(large_dataset, db_session: Session):
    """
    Test reconciliation performance with 50k transactions and 200k invoices.
    
    Threshold: Must complete in < 60 seconds
    """
    entity = large_dataset["entity"]
    
    # Clear any existing reconciliations
    db_session.query(models.ReconciliationTable).delete()
    db_session.query(models.BankTransaction).filter(
        models.BankTransaction.is_reconciled == 1
    ).update({"is_reconciled": 0})
    db_session.commit()
    
    # Run reconciliation
    service = ReconciliationServiceV2(db_session)
    
    start_time = time.time()
    results = service.reconcile_entity(entity.id)
    elapsed_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"Reconciliation Performance Test")
    print(f"{'='*60}")
    print(f"Transactions processed: {len(large_dataset['transactions'])}")
    print(f"Invoices indexed: {len(large_dataset['invoices'])}")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Throughput: {len(large_dataset['transactions']) / elapsed_time:.0f} txns/sec")
    print(f"\nResults:")
    print(f"  Deterministic: {results.get('deterministic', 0)}")
    print(f"  Rule-based: {results.get('rule_based', 0)}")
    print(f"  Suggested: {results.get('suggested', 0)}")
    print(f"  Manual: {results.get('manual', 0)}")
    print(f"  Many-to-many: {results.get('many_to_many', 0)}")
    print(f"{'='*60}\n")
    
    # Assert performance threshold
    assert elapsed_time < 60.0, f"Reconciliation took {elapsed_time:.2f}s, exceeds 60s threshold"
    
    # Assert some matches were found
    total_matches = (
        results.get('deterministic', 0) +
        results.get('rule_based', 0) +
        results.get('many_to_many', 0)
    )
    assert total_matches > 0, "No matches found - reconciliation may have failed"


def test_blocking_index_performance(large_dataset, db_session: Session):
    """Test blocking index build and query performance."""
    from reconciliation_service_v2 import BlockingIndex
    
    invoices = large_dataset["invoices"]
    transactions = large_dataset["transactions"]
    
    # Build index
    index = BlockingIndex()
    
    start_time = time.time()
    index.build(invoices, db_session)
    build_time = time.time() - start_time
    
    print(f"Blocking index build time: {build_time:.2f}s for {len(invoices)} invoices")
    assert build_time < 10.0, f"Index build took {build_time:.2f}s, exceeds 10s threshold"
    
    # Query performance
    query_times = []
    sample_txns = random.sample(transactions, min(1000, len(transactions)))
    
    for txn in sample_txns:
        start = time.time()
        candidates = index.query_candidates(txn, amount_tolerance=0.02, date_window_days=7)
        query_times.append(time.time() - start)
    
    avg_query_time = sum(query_times) / len(query_times)
    max_query_time = max(query_times)
    
    print(f"Average query time: {avg_query_time*1000:.2f}ms")
    print(f"Max query time: {max_query_time*1000:.2f}ms")
    
    assert avg_query_time < 0.01, f"Average query time {avg_query_time*1000:.2f}ms exceeds 10ms"
    assert max_query_time < 0.1, f"Max query time {max_query_time*1000:.2f}ms exceeds 100ms"


def test_constrained_solver_performance():
    """Test constrained solver performance with many candidates."""
    from reconciliation_service_v2 import ConstrainedAllocationSolver, MatchCandidate
    from datetime import datetime
    
    solver = ConstrainedAllocationSolver()
    
    # Create test scenario: transaction with 100 candidate invoices
    txn_amount = 10000.0
    candidates = []
    
    for i in range(100):
        cand = MatchCandidate(
            invoice_id=i,
            invoice_number=f"INV-{i}",
            customer_name=f"Customer-{i}",
            open_amount=random.uniform(100, 2000),
            due_date=datetime.now(),
            currency="EUR",
            confidence=random.uniform(0.5, 1.0)
        )
        candidates.append(cand)
    
    start_time = time.time()
    solution = solver.solve(txn_amount, candidates, fees=0.0, writeoffs=0.0)
    elapsed_time = time.time() - start_time
    
    print(f"Solver time: {elapsed_time*1000:.2f}ms for {len(candidates)} candidates")
    assert elapsed_time < 1.0, f"Solver took {elapsed_time:.2f}s, exceeds 1s threshold"
    assert solution.is_optimal or solution.solver_status == "greedy_fallback"
    
    # Validate solution
    total_allocated = sum(solution.allocations.values())
    assert abs(total_allocated + solution.fees + solution.writeoffs - txn_amount) < 0.01, \
        "Solution violates allocation constraint"


def test_many_to_many_allocation_constraints(large_dataset, db_session: Session):
    """Test that many-to-many allocations respect constraints."""
    from reconciliation_service_v2 import ReconciliationServiceV2, MatchCandidate, ConstrainedAllocationSolver
    
    entity = large_dataset["entity"]
    invoices = large_dataset["invoices"]
    
    # Create a transaction that should match multiple invoices
    txn = models.BankTransaction(
        bank_account_id=large_dataset["bank_account"].id,
        transaction_date=datetime.now(),
        amount=50000.0,
        currency="EUR",
        reference="BUNDLED PAYMENT",
        counterparty="Customer-1",
        transaction_type="customer_receipt",
        is_reconciled=0
    )
    db_session.add(txn)
    db_session.commit()
    db_session.refresh(txn)
    
    # Create candidates (multiple invoices from same customer)
    customer_invoices = [inv for inv in invoices if inv.customer == "Customer-1"][:10]
    
    candidates = []
    for inv in customer_invoices:
        existing_alloc = db_session.query(
            func.sum(models.ReconciliationTable.amount_allocated)
        ).filter(
            models.ReconciliationTable.invoice_id == inv.id
        ).scalar() or 0.0
        
        open_amount = float(inv.amount) - float(existing_alloc)
        
        cand = MatchCandidate(
            invoice_id=inv.id,
            invoice_number=inv.document_number,
            customer_name=inv.customer,
            open_amount=open_amount,
            due_date=inv.expected_due_date,
            currency=inv.currency,
            confidence=0.8,
            match_type="rule"
        )
        candidates.append(cand)
    
    # Solve allocation
    solver = ConstrainedAllocationSolver()
    solution = solver.solve(txn.amount, candidates, fees=0.0, writeoffs=0.0)
    
    # Validate constraints
    total_allocated = sum(solution.allocations.values())
    assert abs(total_allocated - abs(txn.amount)) < 0.01, \
        f"Allocations {total_allocated} don't sum to transaction amount {txn.amount}"
    
    # Validate no over-allocation
    for inv_id, alloc in solution.allocations.items():
        inv = next(inv for inv in customer_invoices if inv.id == inv_id)
        assert alloc <= inv.amount + 0.01, \
            f"Allocation {alloc} exceeds invoice amount {inv.amount}"


def test_embedding_similarity_suggestions(large_dataset, db_session: Session):
    """Test that embedding similarity only generates suggestions (never auto-applies)."""
    from reconciliation_service_v2 import ReconciliationServiceV2
    
    entity = large_dataset["entity"]
    
    # Create transaction with noisy reference (should use embedding similarity)
    txn = models.BankTransaction(
        bank_account_id=large_dataset["bank_account"].id,
        transaction_date=datetime.now(),
        amount=10000.0,
        currency="EUR",
        reference="Payment for services rendered invoice number 12345",
        counterparty="Customer-50",
        transaction_type="customer_receipt",
        is_reconciled=0
    )
    db_session.add(txn)
    db_session.commit()
    db_session.refresh(txn)
    
    service = ReconciliationServiceV2(db_session)
    
    # Build indexes
    invoices = large_dataset["invoices"]
    service.blocking_index.build(invoices, db_session)
    service.embedding_matcher.build(invoices)
    
    # Reconcile - should generate suggestions, not auto-apply
    from matching_policy_service import get_matching_policy
    policy = get_matching_policy(db_session, entity.id, "EUR")
    
    result = service._reconcile_transaction(txn, policy)
    
    # Should be suggested, not auto-applied
    assert result["type"] in ["suggested", "manual"], \
        f"Expected suggested or manual, got {result['type']}"
    
    # Transaction should not be reconciled
    db_session.refresh(txn)
    assert txn.is_reconciled == 0, "Suggested match was auto-applied (should require approval)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


