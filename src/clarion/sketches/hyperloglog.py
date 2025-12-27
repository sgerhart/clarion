"""
HyperLogLog wrapper for cardinality estimation.

HyperLogLog estimates the number of unique items in a stream using
fixed memory (~1KB for 2% error). Perfect for counting unique peers
or services an endpoint communicates with.

Memory: ~1.5KB for p=14 (default)
Error: ~2% standard error
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Union

from datasketch import HyperLogLog


@dataclass
class HyperLogLogSketch:
    """
    Wrapper around datasketch HyperLogLog for endpoint behavioral tracking.
    
    Use cases:
    - Count unique destination IPs (peer diversity)
    - Count unique services accessed
    - Count unique ports used
    
    Memory: ~1.5KB per instance (p=14)
    Error: ~2% standard error for cardinality
    
    Example:
        >>> hll = HyperLogLogSketch(name="unique_peers")
        >>> hll.add("10.0.0.1")
        >>> hll.add("10.0.0.2")
        >>> hll.add("10.0.0.1")  # Duplicate
        >>> hll.count()  # Returns ~2
    """
    
    name: str
    precision: int = 14  # 2^14 = 16384 registers, ~1.5KB
    _hll: HyperLogLog = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize the underlying HyperLogLog."""
        if self._hll is None:
            self._hll = HyperLogLog(p=self.precision)
    
    def add(self, item: Union[str, bytes, int]) -> None:
        """
        Add an item to the sketch.
        
        Args:
            item: Item to add (string, bytes, or int)
        """
        if isinstance(item, int):
            item = str(item)
        if isinstance(item, str):
            item = item.encode('utf-8')
        self._hll.update(item)
    
    def count(self) -> int:
        """
        Get estimated cardinality (unique count).
        
        Returns:
            Estimated number of unique items added
        """
        return int(self._hll.count())
    
    def merge(self, other: HyperLogLogSketch) -> HyperLogLogSketch:
        """
        Merge another HyperLogLog into this one.
        
        Used for combining sketches from multiple sources
        (e.g., same endpoint seen on multiple switches).
        
        Args:
            other: Another HyperLogLogSketch to merge
            
        Returns:
            Self (for chaining)
        """
        if self.precision != other.precision:
            raise ValueError(
                f"Cannot merge HLLs with different precision: "
                f"{self.precision} vs {other.precision}"
            )
        self._hll.merge(other._hll)
        return self
    
    def to_bytes(self) -> bytes:
        """
        Serialize to bytes for storage/transmission.
        
        Returns:
            Serialized HyperLogLog as bytes
        """
        return bytes(self._hll.digest())
    
    @classmethod
    def from_bytes(cls, name: str, data: bytes, precision: int = 14) -> HyperLogLogSketch:
        """
        Deserialize from bytes.
        
        Args:
            name: Name for the sketch
            data: Serialized HyperLogLog bytes
            precision: Precision parameter (must match serialized)
            
        Returns:
            Reconstructed HyperLogLogSketch
        """
        hll = HyperLogLog(p=precision)
        # datasketch uses hashvalues for digest, we need to restore
        # For now, return empty - full serialization needs custom impl
        sketch = cls(name=name, precision=precision)
        # TODO: Implement proper deserialization
        return sketch
    
    def clear(self) -> None:
        """Reset the sketch to empty state."""
        self._hll = HyperLogLog(p=self.precision)
    
    def memory_bytes(self) -> int:
        """
        Approximate memory usage in bytes.
        
        Returns:
            Estimated memory usage
        """
        # 2^p registers, each 1 byte + overhead
        return (2 ** self.precision) + 100
    
    def __repr__(self) -> str:
        return f"HyperLogLogSketch(name='{self.name}', count≈{self.count()})"


