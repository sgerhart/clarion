"""
API Gateway / Orchestrator Service

Single entry point for all client requests. Routes requests to appropriate microservices.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import logging
import os
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Clarion API Gateway",
    description="API Gateway for Clarion microservices",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs (from environment variables or service discovery)
SERVICE_URLS = {
    "user": os.getenv("USER_SERVICE_URL", "http://user-service:8001"),
    "policy": os.getenv("POLICY_SERVICE_URL", "http://policy-service:8002"),
    "clustering": os.getenv("CLUSTERING_SERVICE_URL", "http://clustering-service:8003"),
    "connector": os.getenv("CONNECTOR_SERVICE_URL", "http://connector-service:8004"),
    "data": os.getenv("DATA_SERVICE_URL", "http://data-service:8005"),
    "pxgrid": os.getenv("PXGRID_SERVICE_URL", "http://pxgrid-service:9000"),
}

# Route prefixes
ROUTE_PREFIXES = {
    "/api/users": "user",
    "/api/user": "user",
    "/api/policies": "policy",
    "/api/policy": "policy",
    "/api/sgt": "policy",
    "/api/clustering": "clustering",
    "/api/cluster": "clustering",
    "/api/connectors": "connector",
    "/api/connector": "connector",
    "/api/ise": "connector",
    "/api/data": "data",
    "/api/netflow": "data",
    "/api/flows": "data",
    "/api/pxgrid": "pxgrid",
}


async def forward_request(service_name: str, path: str, method: str, request: Request) -> Dict[str, Any]:
    """Forward request to appropriate microservice."""
    service_url = SERVICE_URLS.get(service_name)
    if not service_url:
        raise HTTPException(status_code=503, detail=f"Service {service_name} not available")
    
    # Get request body if present
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
        except Exception:
            pass
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Forward request
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{service_url}{path}"
        headers = dict(request.headers)
        # Remove host header (let service set it)
        headers.pop("host", None)
        
        try:
            response = await client.request(
                method=method,
                url=url,
                content=body,
                params=query_params,
                headers=headers,
            )
            return {
                "status_code": response.status_code,
                "content": response.content,
                "headers": dict(response.headers),
            }
        except httpx.RequestError as e:
            logger.error(f"Error forwarding request to {service_name}: {e}")
            raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")


@app.get("/health")
async def health():
    """Gateway health check."""
    return {"status": "healthy", "service": "gateway"}


@app.get("/api/health")
async def api_health():
    """Aggregated health check for all services."""
    health_status = {
        "gateway": {"status": "healthy"},
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICE_URLS.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=2.0)
                health_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                }
            except Exception as e:
                health_status[service_name] = {
                    "status": "unavailable",
                    "error": str(e),
                }
    
    return health_status


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(path: str, request: Request):
    """Proxy requests to appropriate microservice."""
    full_path = f"/api/{path}"
    
    # Determine which service to route to
    service_name = None
    for prefix, service in ROUTE_PREFIXES.items():
        if full_path.startswith(prefix):
            service_name = service
            # Remove prefix from path
            service_path = full_path[len(prefix):] if len(prefix) < len(full_path) else "/"
            break
    
    if not service_name:
        # Default routing or 404
        raise HTTPException(status_code=404, detail=f"No service found for path: {full_path}")
    
    # Forward request
    result = await forward_request(service_name, service_path, request.method, request)
    
    # Return response
    return JSONResponse(
        content=result["content"],
        status_code=result["status_code"],
        headers=result["headers"],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

