"""
Count-Min Sketch wrapper for frequency estimation.

Count-Min Sketch estimates the frequency of items in a stream using
fixed memory. Perfect for tracking port usage distribution or
service access patterns.

Memory: width × depth × 4 bytes (32-bit counters)
Default: 1000 × 5 = ~20KB
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Union

from datasketch import MinHash
import numpy as np


@dataclass
class CountMinSketch:
    """
    Count-Min Sketch for frequency estimation.
    
    Use cases:
    - Track port usage frequency (which ports does this endpoint use?)
    - Track service access frequency (which services are accessed most?)
    - Track destination IP frequency (who does this endpoint talk to most?)
    
    Memory: ~20KB per instance (default parameters)
    
    Example:
        >>> cms = CountMinSketch(name="port_frequency")
        >>> cms.add("tcp/443", count=100)
        >>> cms.add("tcp/22", count=10)
        >>> cms.add("tcp/443", count=50)
        >>> cms.get("tcp/443")  # Returns ~150
    """
    
    name: str
    width: int = 1000   # Number of counters per row
    depth: int = 5      # Number of hash functions
    _counters: np.ndarray = field(default=None, repr=False)
    _total_count: int = field(default=0, repr=False)
    
    def __post_init__(self):
        """Initialize the counter array."""
        if self._counters is None:
            self._counters = np.zeros((self.depth, self.width), dtype=np.int64)
    
    def _hash(self, item: str, seed: int) -> int:
        """
        Hash function for Count-Min Sketch.
        
        Uses simple polynomial hashing with different seeds.
        """
        h = seed
        for char in item:
            h = (h * 31 + ord(char)) & 0xFFFFFFFF
        return h % self.width
    
    def add(self, item: Union[str, int], count: int = 1) -> None:
        """
        Add an item with optional count.
        
        Args:
            item: Item to add (will be converted to string)
            count: Number of occurrences to add (default 1)
        """
        item_str = str(item)
        for i in range(self.depth):
            idx = self._hash(item_str, seed=i * 1000003)
            self._counters[i, idx] += count
        self._total_count += count
    
    def get(self, item: Union[str, int]) -> int:
        """
        Get estimated frequency for an item.
        
        Returns the minimum count across all hash positions
        (Count-Min Sketch only overestimates, never underestimates).
        
        Args:
            item: Item to query
            
        Returns:
            Estimated frequency (may overestimate due to collisions)
        """
        item_str = str(item)
        counts = []
        for i in range(self.depth):
            idx = self._hash(item_str, seed=i * 1000003)
            counts.append(self._counters[i, idx])
        return int(min(counts))
    
    def total(self) -> int:
        """
        Get total count of all items added.
        
        Returns:
            Total count
        """
        return self._total_count
    
    def top_k(self, candidates: List[str], k: int = 10) -> List[Tuple[str, int]]:
        """
        Get top-k items from a list of candidates.
        
        Note: Count-Min Sketch doesn't track keys, so you must
        provide candidate items to check.
        
        Args:
            candidates: List of candidate items to check
            k: Number of top items to return
            
        Returns:
            List of (item, count) tuples sorted by count descending
        """
        counts = [(item, self.get(item)) for item in candidates]
        counts.sort(key=lambda x: -x[1])
        return counts[:k]
    
    def merge(self, other: CountMinSketch) -> CountMinSketch:
        """
        Merge another Count-Min Sketch into this one.
        
        Args:
            other: Another CountMinSketch to merge
            
        Returns:
            Self (for chaining)
        """
        if self.width != other.width or self.depth != other.depth:
            raise ValueError(
                f"Cannot merge CMS with different dimensions: "
                f"({self.width}, {self.depth}) vs ({other.width}, {other.depth})"
            )
        self._counters += other._counters
        self._total_count += other._total_count
        return self
    
    def to_bytes(self) -> bytes:
        """
        Serialize to bytes for storage/transmission.
        
        Returns:
            Serialized Count-Min Sketch as bytes
        """
        return self._counters.tobytes()
    
    @classmethod
    def from_bytes(
        cls, 
        name: str, 
        data: bytes, 
        width: int = 1000, 
        depth: int = 5,
        total_count: int = 0
    ) -> CountMinSketch:
        """
        Deserialize from bytes.
        
        Args:
            name: Name for the sketch
            data: Serialized counter array bytes
            width: Width parameter (must match serialized)
            depth: Depth parameter (must match serialized)
            total_count: Total count value
            
        Returns:
            Reconstructed CountMinSketch
        """
        counters = np.frombuffer(data, dtype=np.int64).reshape((depth, width))
        sketch = cls(name=name, width=width, depth=depth)
        sketch._counters = counters.copy()
        sketch._total_count = total_count
        return sketch
    
    def clear(self) -> None:
        """Reset the sketch to empty state."""
        self._counters = np.zeros((self.depth, self.width), dtype=np.int64)
        self._total_count = 0
    
    def memory_bytes(self) -> int:
        """
        Approximate memory usage in bytes.
        
        Returns:
            Estimated memory usage
        """
        # depth × width × 8 bytes (int64) + overhead
        return self.depth * self.width * 8 + 100
    
    def __repr__(self) -> str:
        return f"CountMinSketch(name='{self.name}', total={self._total_count})"


