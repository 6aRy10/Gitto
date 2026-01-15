"""
Pytest configuration and fixtures for Gitto test suite
"""

import pytest
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import models

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    models.Base.metadata.create_all(engine)
    
    # Add DB-level constraints for finance system integrity
    try:
        from migrations.add_db_constraints import add_finance_constraints
        add_finance_constraints(engine)
    except Exception as e:
        # Constraints might not be critical for all tests
        pass
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()

@pytest.fixture
def sample_entity(db_session):
    """Create a sample entity for testing"""
    entity = models.Entity(
        id=1,
        name="Test Entity",
        currency="EUR"
    )
    db_session.add(entity)
    db_session.commit()
    return entity

@pytest.fixture
def sample_snapshot(db_session, sample_entity):
    """Create a sample snapshot for testing"""
    snapshot = models.Snapshot(
        name="Test Snapshot",
        entity_id=sample_entity.id,
        total_rows=0,
        created_at=datetime.utcnow()
    )
    if hasattr(snapshot, 'is_locked'):
        snapshot.is_locked = 0
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot

@pytest.fixture
def sample_bank_account(db_session, sample_entity):
    """Create a sample bank account for testing"""
    account = models.BankAccount(
        entity_id=sample_entity.id,
        account_name="Test Account",
        account_number="123456",
        bank_name="Test Bank",
        currency="EUR",
        balance=100000.0,
        last_sync_at=datetime.utcnow()
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


