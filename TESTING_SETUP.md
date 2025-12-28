# Automated Testing Setup

## Overview

We use **GitHub Actions** for continuous integration and automated testing. This provides:
- Automated testing on every push/PR
- Multi-version Python testing (3.11, 3.12)
- Ground truth dataset validation
- Clustering accuracy metrics
- Code quality checks
- Weekly validation reports

## Why GitHub Actions?

✅ **Free for public repos** - No cost for open source projects  
✅ **Integrated with GitHub** - Automatic status checks on PRs  
✅ **Easy to configure** - YAML-based workflow definitions  
✅ **Good ecosystem** - Many pre-built actions available  
✅ **Matrix builds** - Test multiple Python versions easily  
✅ **Artifact storage** - Store test reports and validation results  

## Alternative Options (Not Recommended)

- **Jenkins**: More complex setup, requires self-hosting
- **GitLab CI**: Good alternative if using GitLab
- **CircleCI/Travis CI**: Similar to GitHub Actions but less integrated
- **Azure Pipelines**: Good but more complex for simple projects

## Workflow Structure

### 1. CI Pipeline (`ci.yml`)
Runs on every push/PR:
- Unit tests (Python 3.11, 3.12)
- Integration tests
- Ground truth dataset validation
- Code linting
- Frontend tests
- Collector tests

### 2. Validation Report (`validation-report.yml`)
Runs weekly:
- Generates comprehensive clustering accuracy reports
- Tracks metrics over time
- Helps identify regressions

## Test Structure

```
tests/
├── unit/              # Unit tests for individual components
├── integration/       # End-to-end integration tests
│   ├── test_categorization_mvp.py
│   └── test_clustering_accuracy.py  # Ground truth validation
└── data/
    └── ground_truth/  # Test datasets
```

## Running Tests Locally

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-xdist

# Run all tests
pytest

# Run with coverage
pytest --cov=src/clarion --cov-report=html

# Run specific test file
pytest tests/integration/test_clustering_accuracy.py -v

# Run tests in parallel (faster)
pytest -n auto
```

## Next Steps

1. ✅ GitHub Actions workflows created
2. ✅ Test structure set up
3. ⏳ Add more unit tests as components are built
4. ⏳ Set up code coverage reporting (Codecov)
5. ⏳ Add performance benchmarks
6. ⏳ Set up test result notifications
