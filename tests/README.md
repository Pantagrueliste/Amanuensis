# Amanuensis 2.0 Test Suite

This directory contains comprehensive tests for the Amanuensis 2.0 project, covering all core modules and functionality.

## Test Structure

The test suite is organized as follows:

- `conftest.py` - Shared pytest fixtures and configuration
- `test_tei_processor.py` - Tests for the TEI XML processor
- `test_config.py` - Tests for the configuration manager
- `test_dataset_builder.py` - Tests for the dataset builder
- `test_suggestion_generator.py` - Tests for the suggestion generator

## Running Tests

### Install Test Dependencies

First, make sure you have all the required test dependencies:

```bash
pip install pytest pytest-cov
```

### Run All Tests

To run the complete test suite with coverage reporting:

```bash
# From the project root directory
pytest
```

### Run Specific Test Files

To run a specific test file:

```bash
pytest tests/test_tei_processor.py
```

### Run Specific Test Classes

To run all tests in a specific test class:

```bash
pytest tests/test_tei_processor.py::TestTEIProcessor
```

### Run Specific Test Methods

To run a specific test method:

```bash
pytest tests/test_tei_processor.py::TestTEIProcessor::test_parse_document
```

## Code Coverage

To generate a detailed HTML coverage report:

```bash
pytest --cov=modules --cov-report=html
```

This will create a `htmlcov` directory with an interactive HTML report.

## Configuration

The test suite uses the following configuration:

- Tests are parameterized where appropriate to test multiple scenarios
- Mock objects are used to isolate tests from external dependencies
- Temporary directories are created for file I/O tests
- Common fixtures are shared through conftest.py

## CI Integration

The test suite is configured to run in Continuous Integration environments through the pytest configuration in `pytest.ini`.