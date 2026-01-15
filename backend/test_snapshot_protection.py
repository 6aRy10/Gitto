"""
Test Snapshot Immutability Protection
"""

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import models
from snapshot_protection import check_snapshot_not_locked, SnapshotLockedError

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

DATABASE_URL = "sqlite:///sql_app.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)

def test_snapshot_protection():
    """Test that locked snapshots cannot be modified"""
    db = SessionLocal()
    
    try:
        # Create test snapshot
        snapshot = models.Snapshot(
            name=f"Protection Test {datetime.now().isoformat()}",
            entity_id=1,
            total_rows=0
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Test 1: Unlocked snapshot should pass
        try:
            check_snapshot_not_locked(db, snapshot.id, "modify")
            print("[PASS] Test 1: Unlocked snapshot allows modification")
        except SnapshotLockedError:
            print("[FAIL] Test 1: Unlocked snapshot incorrectly blocked")
            return False
        
        # Lock the snapshot
        snapshot.is_locked = 1
        snapshot.lock_type = "Meeting"
        db.commit()
        
        # Test 2: Locked snapshot should raise error
        try:
            check_snapshot_not_locked(db, snapshot.id, "modify")
            print("[FAIL] Test 2: Locked snapshot incorrectly allowed modification")
            return False
        except SnapshotLockedError as e:
            if "locked" in str(e).lower() and "Meeting" in str(e):
                print("[PASS] Test 2: Locked snapshot correctly blocked")
            else:
                print(f"[FAIL] Test 2: Error message incorrect: {e}")
                return False
        
        print("\n[SUCCESS] All snapshot protection tests passed!")
        return True
        
    except Exception as e:
        print(f"[FAIL] Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_snapshot_protection()
    sys.exit(0 if success else 1)


