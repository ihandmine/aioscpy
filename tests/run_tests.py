import unittest
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the test modules
from test_engine_memory_management import TestEngineMemoryManagement
from test_engine_task_beat import TestEngineTaskBeat
from test_httpx_handler import TestHttpxHandler
from test_adaptive_concurrency import TestAdaptiveConcurrencyMiddleware


def run_tests():
    """Run all the tests."""
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add the test cases
    test_suite.addTest(unittest.makeSuite(TestEngineMemoryManagement))
    test_suite.addTest(unittest.makeSuite(TestEngineTaskBeat))
    test_suite.addTest(unittest.makeSuite(TestHttpxHandler))
    test_suite.addTest(unittest.makeSuite(TestAdaptiveConcurrencyMiddleware))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return the result
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
