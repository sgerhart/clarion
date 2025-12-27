"""
Clarion Sketches Module

Probabilistic data structures for bounded-memory behavioral fingerprinting.
These sketches run on edge devices (switches) with constrained resources.

Key structures:
- EndpointSketch: Complete behavioral fingerprint per endpoint (~10KB)
- HyperLogLog: Cardinality estimation (unique peers, services)
- CountMinSketch: Frequency distribution (port usage, service access)
"""

from clarion.sketches.endpoint_sketch import EndpointSketch
from clarion.sketches.hyperloglog import HyperLogLogSketch
from clarion.sketches.countmin import CountMinSketch

__all__ = [
    "EndpointSketch",
    "HyperLogLogSketch",
    "CountMinSketch",
]


