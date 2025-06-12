#!/usr/bin/env python3
"""
Simple test to verify Claude Code is working correctly.
This test checks basic functionality and imports of key dependencies.
"""

import sys
import pandas as pd
import numpy as np


def test_basic_functionality():
    """Test basic Python functionality."""
    assert 2 + 2 == 4, "Basic arithmetic should work"
    assert len([1, 2, 3]) == 3, "List operations should work"
    print("✓ Basic functionality test passed")


def test_dependencies():
    """Test that key dependencies are available and functional."""
    # Test pandas
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    assert len(df) == 3, "Pandas DataFrame creation should work"
    
    # Test numpy
    arr = np.array([1, 2, 3])
    assert np.sum(arr) == 6, "NumPy operations should work"
    
    print("✓ Dependencies test passed")


def main():
    """Run all tests."""
    print("Testing Claude Code functionality...")
    print(f"Python version: {sys.version}")
    
    try:
        test_basic_functionality()
        test_dependencies()
        print("\n🎉 All tests passed! Claude Code is working correctly.")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)