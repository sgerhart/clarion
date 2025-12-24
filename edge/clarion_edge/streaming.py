"""
Backend Streaming - Stream sketches to the central backend.

Supports multiple transport options:
1. HTTP/JSON - Simple, works everywhere
2. HTTP/Binary - More efficient, uses sketch serialization
3. gRPC - Most efficient (optional, requires grpcio)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from clarion_edge.sketch import EdgeSketch, EdgeSketchStore

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for backend streaming."""
    backend_url: str
    switch_id: str
    
    # Transport
    transport: str = "http"  # "http", "http_binary", "grpc"
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    
    # Batching
    batch_size: int = 100  # Max sketches per batch
    
    # Compression
    compress: bool = True


class StreamTransport(ABC):
    """Abstract base class for stream transports."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to backend."""
        pass
    
    @abstractmethod
    async def send_sketches(
        self,
        sketches: List[EdgeSketch],
        switch_id: str,
    ) -> bool:
        """Send sketches to backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass


class HTTPTransport(StreamTransport):
    """
    HTTP/JSON transport for streaming.
    
    Simple and reliable, works with any backend.
    """
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self._connected = False
        self._client = None
    
    async def connect(self) -> bool:
        """Verify backend is reachable."""
        try:
            import httpx
            
            self._client = httpx.AsyncClient(timeout=30.0)
            
            # Health check
            response = await self._client.get(
                f"{self.config.backend_url}/health"
            )
            
            if response.status_code == 200:
                self._connected = True
                logger.info(f"Connected to backend: {self.config.backend_url}")
                return True
            else:
                logger.warning(f"Backend health check failed: {response.status_code}")
                return False
                
        except ImportError:
            logger.error("httpx not installed, cannot use HTTP transport")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to backend: {e}")
            return False
    
    async def send_sketches(
        self,
        sketches: List[EdgeSketch],
        switch_id: str,
    ) -> bool:
        """Send sketches via HTTP POST."""
        if not self._client:
            logger.error("Not connected")
            return False
        
        try:
            payload = {
                "switch_id": switch_id,
                "timestamp": int(time.time()),
                "sketch_count": len(sketches),
                "sketches": [s.to_dict() for s in sketches],
            }
            
            response = await self._client.post(
                f"{self.config.backend_url}/api/edge/sketches",
                json=payload,
            )
            
            if response.status_code in (200, 201, 202):
                logger.debug(f"Sent {len(sketches)} sketches successfully")
                return True
            else:
                logger.warning(f"Backend returned {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send sketches: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
    
    def is_connected(self) -> bool:
        return self._connected


class BinaryHTTPTransport(StreamTransport):
    """
    HTTP transport with binary sketch serialization.
    
    More efficient than JSON for large numbers of sketches.
    """
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self._connected = False
        self._client = None
    
    async def connect(self) -> bool:
        """Verify backend is reachable."""
        try:
            import httpx
            
            self._client = httpx.AsyncClient(timeout=30.0)
            
            response = await self._client.get(
                f"{self.config.backend_url}/health"
            )
            
            self._connected = response.status_code == 200
            return self._connected
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def send_sketches(
        self,
        sketches: List[EdgeSketch],
        switch_id: str,
    ) -> bool:
        """Send serialized sketches."""
        if not self._client:
            return False
        
        try:
            # Serialize sketches
            parts = [len(sketches).to_bytes(4, 'little')]
            for s in sketches:
                sketch_bytes = s.to_bytes()
                parts.append(len(sketch_bytes).to_bytes(4, 'little'))
                parts.append(sketch_bytes)
            
            data = b''.join(parts)
            
            # Compress if enabled
            if self.config.compress:
                import gzip
                data = gzip.compress(data)
            
            headers = {
                "Content-Type": "application/octet-stream",
                "X-Switch-ID": switch_id,
                "X-Sketch-Count": str(len(sketches)),
            }
            
            if self.config.compress:
                headers["Content-Encoding"] = "gzip"
            
            response = await self._client.post(
                f"{self.config.backend_url}/api/edge/sketches/binary",
                content=data,
                headers=headers,
            )
            
            return response.status_code in (200, 201, 202)
            
        except Exception as e:
            logger.error(f"Failed to send binary sketches: {e}")
            return False
    
    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
    
    def is_connected(self) -> bool:
        return self._connected


class SketchStreamer:
    """
    High-level interface for streaming sketches to backend.
    
    Handles:
    - Transport selection
    - Batching
    - Retries
    - Connection management
    
    Example:
        >>> config = StreamConfig(
        ...     backend_url="http://backend:8000",
        ...     switch_id="switch-1",
        ... )
        >>> streamer = SketchStreamer(config)
        >>> await streamer.start()
        >>> await streamer.send(store.get_all_sketches())
        >>> await streamer.stop()
    """
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self._transport: Optional[StreamTransport] = None
        self._running = False
        
        # Metrics
        self._sketches_sent = 0
        self._batches_sent = 0
        self._errors = 0
    
    async def start(self) -> bool:
        """Start the streamer and connect to backend."""
        # Select transport
        if self.config.transport == "http":
            self._transport = HTTPTransport(self.config)
        elif self.config.transport == "http_binary":
            self._transport = BinaryHTTPTransport(self.config)
        else:
            logger.error(f"Unknown transport: {self.config.transport}")
            return False
        
        # Connect with retries
        for attempt in range(self.config.max_retries):
            if await self._transport.connect():
                self._running = True
                return True
            
            logger.warning(
                f"Connection attempt {attempt + 1} failed, "
                f"retrying in {self.config.retry_delay_seconds}s"
            )
            await asyncio.sleep(self.config.retry_delay_seconds)
        
        logger.error("Failed to connect after all retries")
        return False
    
    async def send(self, sketches: List[EdgeSketch]) -> bool:
        """
        Send sketches to backend.
        
        Automatically batches if there are many sketches.
        """
        if not self._transport or not self._running:
            logger.warning("Streamer not running")
            return False
        
        success = True
        
        # Batch if needed
        for i in range(0, len(sketches), self.config.batch_size):
            batch = sketches[i:i + self.config.batch_size]
            
            # Send with retries
            batch_success = False
            for attempt in range(self.config.max_retries):
                if await self._transport.send_sketches(batch, self.config.switch_id):
                    batch_success = True
                    self._sketches_sent += len(batch)
                    self._batches_sent += 1
                    break
                
                self._errors += 1
                await asyncio.sleep(self.config.retry_delay_seconds)
            
            if not batch_success:
                success = False
        
        return success
    
    async def stop(self) -> None:
        """Stop the streamer."""
        self._running = False
        if self._transport:
            await self._transport.disconnect()
            self._transport = None
    
    def get_metrics(self) -> Dict:
        """Get streamer metrics."""
        return {
            "transport": self.config.transport,
            "backend_url": self.config.backend_url,
            "connected": self._transport.is_connected() if self._transport else False,
            "sketches_sent": self._sketches_sent,
            "batches_sent": self._batches_sent,
            "errors": self._errors,
        }


async def test_streaming(backend_url: str, switch_id: str = "test-switch") -> Dict:
    """
    Test streaming to a backend.
    
    Creates some test sketches and tries to send them.
    
    Returns:
        Dict with test results
    """
    from clarion_edge.sketch import EdgeSketch, EdgeSketchStore
    
    # Create test data
    store = EdgeSketchStore(switch_id=switch_id)
    
    for i in range(10):
        mac = f"00:11:22:33:44:{i:02x}"
        sketch = store.get_or_create(mac)
        
        for j in range(50):
            sketch.record_flow(
                dst_ip=f"10.0.1.{j % 10}",
                dst_port=443,
                proto="tcp",
                bytes_count=1000,
                is_outbound=True,
            )
    
    # Try to stream
    config = StreamConfig(
        backend_url=backend_url,
        switch_id=switch_id,
    )
    
    streamer = SketchStreamer(config)
    
    results = {
        "connected": False,
        "sent": False,
        "sketches": len(store),
    }
    
    try:
        results["connected"] = await streamer.start()
        
        if results["connected"]:
            results["sent"] = await streamer.send(store.get_all_sketches())
        
        results["metrics"] = streamer.get_metrics()
        
    finally:
        await streamer.stop()
    
    return results

