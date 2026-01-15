"""
Safe Single Test Runner
Runs one test at a time with timeout and error handling to prevent crashes.
"""

import sys
import os
import subprocess
import signal
import time

def run_test_safe(test_path, test_name=None, timeout=30):
    """Run a single test safely with timeout"""
    cmd = ["python", "-m", "pytest", test_path, "-v", "--tb=short", "--maxfail=1"]
    
    if test_name:
        cmd.append(f"::{test_name}")
    
    print(f"Running: {' '.join(cmd)}")
    print(f"Timeout: {timeout} seconds")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"❌ Test timed out after {timeout} seconds")
        return False
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

def main():
    """Run tests one at a time"""
    if len(sys.argv) < 2:
        print("Usage: python run_single_test_safe.py <test_file> [test_name]")
        print("\nExample:")
        print("  python run_single_test_safe.py backend/tests/test_cfo_trust_killers.py")
        print("  python run_single_test_safe.py backend/tests/test_cfo_trust_killers.py test_1_cell_sum_truth")
        sys.exit(1)
    
    test_path = sys.argv[1]
    test_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(test_path):
        print(f"❌ Test file not found: {test_path}")
        sys.exit(1)
    
    success = run_test_safe(test_path, test_name, timeout=60)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

