"""
Agent Collector - Receives and forwards edge agent sketches.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from .config import CollectorConfig

logger = logging.getLogger(__name__)


class AgentCollector:
    """
    Collects sketches from edge agents and forwards to backend.
    
    Provides an HTTP endpoint that agents can connect to instead of
    connecting directly to the backend. Useful for:
    - Load balancing multiple agents
    - Aggregating data from multiple agents
    - Adding middleware processing
    - Network isolation
    """
    
    def __init__(self, config: CollectorConfig):
        self.config = config
        self.backend_client: Optional[httpx.AsyncClient] = None
        self.app = FastAPI(title="Clarion Agent Collector")
        self.total_received = 0
        self.total_forwarded = 0
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up FastAPI routes."""
        
        @self.app.post("/api/edge/sketches")
        async def receive_sketches(request: Request):
            """Receive sketches from edge agents."""
            try:
                payload = await request.json()
                
                switch_id = payload.get("switch_id")
                sketches = payload.get("sketches", [])
                timestamp = payload.get("timestamp", int(datetime.now().timestamp()))
                sketch_count = payload.get("sketch_count", len(sketches))
                
                if not switch_id:
                    raise HTTPException(status_code=400, detail="switch_id is required")
                
                if not sketches:
                    raise HTTPException(status_code=400, detail="sketches list is required")
                
                # Forward to backend
                forwarded = await self._forward_to_backend(
                    switch_id=switch_id,
                    sketches=sketches,
                    timestamp=timestamp,
                    sketch_count=sketch_count,
                )
                
                if forwarded:
                    self.total_received += len(sketches)
                    self.total_forwarded += len(sketches)
                    return {
                        "status": "received",
                        "switch_id": switch_id,
                        "sketches_received": len(sketches),
                        "forwarded": True,
                    }
                else:
                    raise HTTPException(
                        status_code=502,
                        detail="Failed to forward to backend"
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error receiving sketches: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/edge/sketches/binary")
        async def receive_sketches_binary(request: Request):
            """Receive binary-encoded sketches from edge agents."""
            try:
                content = await request.body()
                switch_id = request.headers.get("X-Switch-ID")
                sketch_count = request.headers.get("X-Sketch-Count")
                
                if not switch_id:
                    raise HTTPException(status_code=400, detail="X-Switch-ID header is required")
                
                # For binary format, we could either:
                # 1. Forward as-is (passthrough)
                # 2. Parse and forward as JSON
                # For now, forward as binary passthrough
                forwarded = await self._forward_binary_to_backend(
                    content=content,
                    switch_id=switch_id,
                    sketch_count=sketch_count,
                )
                
                if forwarded:
                    count = int(sketch_count) if sketch_count else 0
                    self.total_received += count
                    self.total_forwarded += count
                    return {
                        "status": "received",
                        "format": "binary",
                        "forwarded": True,
                    }
                else:
                    raise HTTPException(
                        status_code=502,
                        detail="Failed to forward to backend"
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error receiving binary sketches: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "agent-collector",
                "backend_url": self.config.backend_url,
            }
        
        @self.app.get("/metrics")
        async def metrics():
            """Collector metrics."""
            return {
                "total_received": self.total_received,
                "total_forwarded": self.total_forwarded,
                "pending": 0,  # Agent collector forwards immediately
            }
    
    async def _forward_to_backend(
        self,
        switch_id: str,
        sketches: List[Dict],
        timestamp: int,
        sketch_count: int,
    ) -> bool:
        """Forward sketches to backend API."""
        if not self.backend_client:
            return False
        
        try:
            payload = {
                "switch_id": switch_id,
                "timestamp": timestamp,
                "sketch_count": sketch_count,
                "sketches": sketches,
            }
            
            response = await self.backend_client.post(
                "/api/edge/sketches",
                json=payload,
            )
            response.raise_for_status()
            
            logger.debug(
                f"Forwarded {len(sketches)} sketches from {switch_id} to backend"
            )
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Backend returned error {e.response.status_code}: {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Error forwarding to backend: {e}", exc_info=True)
            return False
    
    async def _forward_binary_to_backend(
        self,
        content: bytes,
        switch_id: str,
        sketch_count: Optional[str],
    ) -> bool:
        """Forward binary sketches to backend API."""
        if not self.backend_client:
            return False
        
        try:
            headers = {
                "Content-Type": "application/octet-stream",
                "X-Switch-ID": switch_id,
            }
            if sketch_count:
                headers["X-Sketch-Count"] = sketch_count
            
            response = await self.backend_client.post(
                "/api/edge/sketches/binary",
                content=content,
                headers=headers,
            )
            response.raise_for_status()
            
            logger.debug(
                f"Forwarded binary sketches from {switch_id} to backend"
            )
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Backend returned error {e.response.status_code}: {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Error forwarding binary to backend: {e}", exc_info=True)
            return False
    
    async def start(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the agent collector HTTP server."""
        logger.info(f"Starting Agent Collector")
        logger.info(f"  Backend URL: {self.config.backend_url}")
        logger.info(f"  Listening on: {host}:{port}")
        
        # Create HTTP client for backend
        self.backend_client = httpx.AsyncClient(
            base_url=self.config.backend_url,
            timeout=30.0,
        )
        
        # Start FastAPI server
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level=self.config.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()

