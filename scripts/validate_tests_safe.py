"""
Safe Test Validator
Checks test files for import errors and missing dependencies before running.
This prevents crashes by catching issues early.
"""

import sys
import os
import ast
import importlib.util

def check_imports_safe(file_path):
    """Check if a test file can be imported without crashing"""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST to check syntax
        try:
            ast.parse(content)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        # Try to import the module
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if spec is None:
            return False, "Could not create module spec"
        
        module = importlib.util.module_from_spec(spec)
        
        # Add parent directory to path
        parent_dir = os.path.dirname(os.path.dirname(file_path))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Try to load (but don't execute)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            return False, f"Import error: {type(e).__name__}: {e}"
        
        return True, "OK"
        
    except Exception as e:
        return False, f"Error: {type(e).__name__}: {e}"

def main():
    """Validate all test files"""
    test_files = [
        "backend/tests/test_cfo_trust_killers.py",
        "backend/tests/test_adversarial_fixtures.py",
        "backend/tests/test_golden_dataset.py",
        "backend/tests/test_tripwire_mutation.py",
    ]
    
    print("=" * 60)
    print("SAFE TEST VALIDATION")
    print("=" * 60)
    
    all_ok = True
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"❌ {test_file}: FILE NOT FOUND")
            all_ok = False
            continue
        
        ok, message = check_imports_safe(test_file)
        status = "✅" if ok else "❌"
        print(f"{status} {test_file}: {message}")
        if not ok:
            all_ok = False
    
    print("=" * 60)
    if all_ok:
        print("✅ All test files are safe to import")
        return 0
    else:
        print("❌ Some test files have issues - fix before running")
        return 1

if __name__ == "__main__":
    sys.exit(main())




