# Performance Benchmarking Setup

## Overview

Performance benchmarks ensure the categorization engine meets performance requirements:
- Sketch building: <10 seconds for 380 endpoints
- Clustering: <5 seconds for 380 endpoints
- Incremental assignment: <100ms per endpoint
- Full pipeline: <30 seconds for enterprise dataset

## Running Benchmarks Locally

```bash
# Install benchmark tool
pip install pytest-benchmark

# Run all benchmarks
pytest tests/benchmark/ -v --benchmark-only

# Run with comparison (vs previous run)
pytest tests/benchmark/ -v --benchmark-only --benchmark-compare

# Run specific benchmark
pytest tests/benchmark/test_clustering_performance.py::test_clustering_performance_small -v --benchmark-only
```

## Benchmark Results

Benchmark results are stored in `benchmark_results.json` and uploaded as GitHub Actions artifacts.

## Adding New Benchmarks

Add new benchmark tests in `tests/benchmark/` with the `@pytest.mark.benchmark` marker:

```python
@pytest.mark.benchmark
def test_my_feature_performance(benchmark):
    def my_function():
        # Code to benchmark
        pass
    
    result = benchmark(my_function)
    assert benchmark.stats['mean'] < TARGET_TIME
```

