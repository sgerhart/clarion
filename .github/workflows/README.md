# GitHub Actions Workflows

This directory contains CI/CD workflows for the Clarion project.

## Workflows

### `ci.yml` - Continuous Integration

Runs on every push and pull request to main branches.

**Jobs:**
1. **Test** - Runs unit and integration tests on Python 3.11 and 3.12
2. **Validate Ground Truth** - Generates and validates ground truth datasets, runs clustering accuracy tests
3. **Lint** - Checks code formatting (Black), linting (Ruff), and type checking (mypy)
4. **Frontend Test** - Runs frontend tests and builds the React app
5. **Collector Test** - Runs NetFlow collector unit tests

### `validation-report.yml` - Weekly Validation Report

Runs weekly (Monday 9 AM UTC) and on manual trigger.

**Purpose:**
- Generates comprehensive validation reports for clustering accuracy
- Tracks accuracy metrics over time
- Helps identify regressions in categorization engine

## Test Coverage

- **Unit Tests**: `tests/unit/` - Test individual components
- **Integration Tests**: `tests/integration/` - Test end-to-end workflows
- **Clustering Accuracy Tests**: `tests/integration/test_clustering_accuracy.py` - Validate against ground truth datasets

## Running Tests Locally

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run clustering accuracy tests
pytest tests/integration/test_clustering_accuracy.py -v

# Run with coverage
pytest --cov=src/clarion --cov-report=html
```

## Ground Truth Datasets

Ground truth datasets are generated automatically in CI, but can be generated locally:

```bash
# Generate all datasets
python tests/data/ground_truth/generator.py enterprise
python tests/data/ground_truth/generator.py healthcare
python tests/data/ground_truth/generator.py manufacturing
python tests/data/ground_truth/generator.py education
python tests/data/ground_truth/generator.py retail
```

## Code Quality

The lint job checks:
- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **mypy**: Static type checking

To fix formatting locally:
```bash
black src/ tests/
ruff check --fix src/ tests/
```
