# Aioscpy Tests

This directory contains unit tests for the Aioscpy framework.

## Running the Tests

To run all tests, use the following command from the project root:

```bash
python -m tests.run_tests
```

To run a specific test file:

```bash
python -m tests.test_engine_memory_management
```

## Test Files

- `test_engine_memory_management.py`: Tests for the memory management optimizations in the ExecutionEngine.
- `test_engine_task_beat.py`: Tests for the task beat optimizations in the ExecutionEngine.
- `test_httpx_handler.py`: Tests for the improved error handling in the HttpxDownloadHandler.
- `test_adaptive_concurrency.py`: Tests for the AdaptiveConcurrencyMiddleware.

## Writing New Tests

When writing new tests, follow these guidelines:

1. Create a new test file with a name that clearly indicates what is being tested.
2. Use the `unittest` framework.
3. Use mocks to isolate the code being tested.
4. Test both success and failure cases.
5. Add the new test to `run_tests.py`.

## Test Coverage

To generate a test coverage report, install the `coverage` package:

```bash
pip install coverage
```

Then run the tests with coverage:

```bash
coverage run -m tests.run_tests
```

And generate a report:

```bash
coverage report
```

Or an HTML report:

```bash
coverage html
```
