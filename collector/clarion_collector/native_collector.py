"""
Native NetFlow Collector - Receives NetFlow/IPFIX/sFlow from switches.
"""

import asyncio
import socket
import logging
from typing import Dict, List, Optional
from datetime import datetime
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from .config import CollectorConfig
from .netflow_parser import parse_netflow_packet, NetFlowRecord
from .retry import retry_with_backoff

logger = logging.getLogger(__name__)


class NativeNetFlowCollector:
    """
    Collects NetFlow/IPFIX/sFlow from network switches.
    
    Listens on UDP ports:
    - 2055: NetFlow v5/v9
    - 4739: IPFIX
    - 6343: sFlow (future)
    """
    
    def __init__(self, config: CollectorConfig):
        self.config = config
        self.backend_client: Optional[httpx.AsyncClient] = None
        self.batch: List[NetFlowRecord] = []
        self.batch_lock = asyncio.Lock()
        self.total_received = 0
        self.total_sent = 0
        self.total_errors = 0
        self._shutdown = False
        self.app: Optional[FastAPI] = None
        self._setup_http_routes()
    
    def _setup_http_routes(self):
        """Set up HTTP routes for health checks and metrics."""
        self.app = FastAPI(title="Clarion Native NetFlow Collector")
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "native-netflow-collector",
                "backend_url": self.config.backend_url,
            }
        
        @self.app.get("/metrics")
        async def metrics():
            """Collector metrics."""
            metrics_data = self.get_metrics()
            return {
                **metrics_data,
                "errors": self.total_errors,
                "batch_size": self.config.batch_size,
                "batch_interval_seconds": self.config.batch_interval_seconds,
            }
        
    async def start(self, http_port: int = 8081):
        """Start the collector."""
        logger.info(f"Starting Native NetFlow Collector")
        logger.info(f"  Backend URL: {self.config.backend_url}")
        logger.info(f"  NetFlow port: {self.config.netflow_port}")
        logger.info(f"  IPFIX port: {self.config.ipfix_port}")
        logger.info(f"  Batch size: {self.config.batch_size}")
        logger.info(f"  Batch interval: {self.config.batch_interval_seconds}s")
        
        # Create HTTP client for backend
        self.backend_client = httpx.AsyncClient(
            base_url=self.config.backend_url,
            timeout=30.0,
        )
        
        # Create UDP sockets
        loop = asyncio.get_event_loop()
        
        # NetFlow socket
        netflow_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        netflow_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Enable SO_REUSEPORT for horizontal scaling (Linux 3.9+)
        # Allows multiple instances to bind to same port - OS load balances UDP packets
        try:
            netflow_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            logger.info("SO_REUSEPORT enabled - collector can be scaled horizontally")
        except (AttributeError, OSError):
            # SO_REUSEPORT not available (Windows, older Linux)
            logger.warning("SO_REUSEPORT not available - single instance only")
        
        # Set UDP receive buffer size if configured (requires privileges)
        if self.config.udp_rcvbuf_size:
            try:
                netflow_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.config.udp_rcvbuf_size)
                logger.info(f"UDP receive buffer set to {self.config.udp_rcvbuf_size} bytes")
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not set UDP receive buffer size: {e} (may require root/privileges)")
        
        netflow_sock.bind((self.config.bind_host, self.config.netflow_port))
        netflow_sock.setblocking(False)
        
        # IPFIX socket
        ipfix_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ipfix_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            ipfix_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass  # Already logged for NetFlow socket
        
        # Set UDP receive buffer size if configured
        if self.config.udp_rcvbuf_size:
            try:
                ipfix_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.config.udp_rcvbuf_size)
            except (OSError, PermissionError):
                pass  # Already logged for NetFlow socket
        
        ipfix_sock.bind((self.config.bind_host, self.config.ipfix_port))
        ipfix_sock.setblocking(False)
        
        # Start UDP listeners
        netflow_task = asyncio.create_task(
            self._udp_listener(netflow_sock, self._handle_netflow_packet)
        )
        ipfix_task = asyncio.create_task(
            self._udp_listener(ipfix_sock, self._handle_ipfix_packet)
        )
        
        # Start batch processing task
        batch_task = asyncio.create_task(self._batch_processor())
        
        # Start HTTP server for health/metrics
        http_task = None
        if self.app:
            http_config = uvicorn.Config(
                self.app,
                host=self.config.bind_host,
                port=http_port,
                log_level=self.config.log_level.lower(),
            )
            http_server = uvicorn.Server(http_config)
            http_task = asyncio.create_task(http_server.serve())
            logger.info(f"HTTP server started on {self.config.bind_host}:{http_port}")
        
        try:
            # Wait for tasks
            tasks = [netflow_task, ipfix_task, batch_task]
            if http_task:
                tasks.append(http_task)
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Shutting down Native NetFlow Collector...")
            self._shutdown = True
            netflow_sock.close()
            ipfix_sock.close()
            netflow_task.cancel()
            ipfix_task.cancel()
            batch_task.cancel()
            if http_task:
                http_task.cancel()
            if self.backend_client:
                await self.backend_client.aclose()
    
    async def _udp_listener(self, sock: socket.socket, handler):
        """Generic UDP listener."""
        loop = asyncio.get_event_loop()
        while not self._shutdown:
            try:
                data, addr = await loop.sock_recvfrom(sock, 65535)
                if data:
                    await handler(data, addr[0])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in UDP listener: {e}", exc_info=True)
    
    async def _handle_netflow_packet(self, data: bytes, source_ip: str):
        """Handle NetFlow v5/v9 packets."""
        try:
            # Parse packet (auto-detect version)
            records = parse_netflow_packet(data, source_ip)
            
            if records:
                # Set switch_id from source IP if configured
                if self.config.switch_id_from_source_ip:
                    for record in records:
                        if not record.switch_id:
                            record.switch_id = source_ip
                
                # Add to batch
                async with self.batch_lock:
                    self.batch.extend(records)
                    self.total_received += len(records)
                    
        except Exception as e:
            logger.error(f"Error handling NetFlow packet from {source_ip}: {e}", exc_info=True)
    
    async def _handle_ipfix_packet(self, data: bytes, source_ip: str):
        """Handle IPFIX packets."""
        try:
            # Parse packet (IPFIX is version 10)
            records = parse_netflow_packet(data, source_ip, version=10)
            
            if records:
                # Set switch_id from source IP if configured
                if self.config.switch_id_from_source_ip:
                    for record in records:
                        if not record.switch_id:
                            record.switch_id = source_ip
                
                # Add to batch
                async with self.batch_lock:
                    self.batch.extend(records)
                    self.total_received += len(records)
                    
        except Exception as e:
            logger.error(f"Error handling IPFIX packet from {source_ip}: {e}", exc_info=True)
    
    async def _batch_processor(self):
        """Process batches and send to backend."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.config.batch_interval_seconds)
                
                async with self.batch_lock:
                    if not self.batch:
                        continue
                    
                    # Get batch
                    batch_to_send = self.batch[:self.config.batch_size]
                    self.batch = self.batch[self.config.batch_size:]
                
                # Send to backend
                if batch_to_send and self.backend_client:
                    await self._send_batch(batch_to_send)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}", exc_info=True)
        
        # Send remaining batch on shutdown
        async with self.batch_lock:
            if self.batch and self.backend_client:
                await self._send_batch(self.batch)
                self.batch = []
    
    async def _send_batch(self, records: List[NetFlowRecord]):
        """Send a batch of records to the backend."""
        if not records:
            return
        
        try:
            # Convert to API format
            records_dict = [r.to_dict() for r in records]
            
            # Group by switch_id for batching
            switch_batches: Dict[str, List[Dict]] = {}
            for record in records_dict:
                switch_id = record.get("switch_id") or "unknown"
                if switch_id not in switch_batches:
                    switch_batches[switch_id] = []
                switch_batches[switch_id].append(record)
            
            # Send each switch's batch with retry logic
            for switch_id, switch_records in switch_batches.items():
                payload = {
                    "records": switch_records,
                    "switch_id": switch_id,
                }
                
                async def send_request():
                    response = await self.backend_client.post(
                        "/api/netflow/netflow",
                        json=payload,
                    )
                    response.raise_for_status()
                    return response
                
                try:
                    await retry_with_backoff(
                        send_request,
                        max_attempts=self.config.retry_max_attempts,
                        backoff_factor=self.config.retry_backoff_factor,
                    )
                    
                    self.total_sent += len(switch_records)
                    logger.info(
                        f"Sent {len(switch_records)} NetFlow records from {switch_id} "
                        f"(total sent: {self.total_sent})"
                    )
                except Exception as e:
                    self.total_errors += 1
                    logger.error(
                        f"Failed to send batch from {switch_id} after retries: {e}",
                        exc_info=True
                    )
                    # Note: Records are lost here - consider adding persistence layer
                
        except Exception as e:
            self.total_errors += 1
            logger.error(f"Error preparing batch for backend: {e}", exc_info=True)
    
    def get_metrics(self) -> Dict:
        """Get collector metrics (synchronous, safe to call from HTTP handlers)."""
        # Get pending count - this is safe because list length is atomic in Python
        # We don't need the lock for just reading the length
        pending = len(self.batch)
        
        return {
            "total_received": self.total_received,
            "total_sent": self.total_sent,
            "pending": pending,
            "errors": self.total_errors,
        }

