"""
Shared Database Configuration

Centralized database connection management with environment variable support.
This ensures a single database engine instance across the application.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
from typing import Generator

# Get database URL from environment variable, fallback to SQLite for development
SQLALCHEMY_DATABASE_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL",
    "sqlite:///./sql_app.db"
)

# Determine if we're using SQLite or PostgreSQL/other
is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

# Configure engine with appropriate settings
if is_sqlite:
    # SQLite configuration (development only)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL query logging
    )
else:
    # PostgreSQL/Production configuration with connection pooling
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL query logging in production
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database session.
    Ensures session is properly closed after request.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables. Call this on application startup."""
    import models
    models.Base.metadata.create_all(bind=engine)
    
    # Initialize lineage models (separate Base)
    import lineage_models
    lineage_models.Base.metadata.create_all(bind=engine)
    
    # Initialize health report models (separate Base)
    import health_report_models
    health_report_models.Base.metadata.create_all(bind=engine)
    
    # Initialize invariant models (separate Base)
    import invariant_models
    invariant_models.Base.metadata.create_all(bind=engine)
    
    # Initialize trust report models (separate Base)
    import trust_report_models
    trust_report_models.Base.metadata.create_all(bind=engine)
    
    # External certification models use models.Base, so they're created with models above
    # Just import to ensure they're registered
    import external_certification_models
    
    # Cash-to-Plan Bridge models also use models.Base
    import cash_plan_bridge_models
    
    # Create database constraints for immutable snapshots
    from db_constraints import create_snapshot_immutability_constraints
    try:
        create_snapshot_immutability_constraints(engine)
    except Exception as e:
        # Constraints might already exist, which is fine
        pass
