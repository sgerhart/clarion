"""
FastAPI Application Factory

Main application setup and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from clarion.api.routes import (
    health,
    sketches,
    netflow,
    clustering,
    policy,
    visualization,
    export,
    devices,
    groups,
    topology,
    collectors,
    sgt,
    policy_recommendations,
)
from clarion.storage import init_database

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    # Initialize database on startup
    init_database()
    logger.info("Database initialized")
    
    app = FastAPI(
        title="Clarion TrustSec Policy Copilot API",
        description="Scale-first network segmentation using edge processing and unsupervised learning",
        version="0.5.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # CORS middleware - Allow React frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "*",  # Allow all for development
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(sketches.router, prefix="/api/edge", tags=["Edge"])
    app.include_router(netflow.router, prefix="/api/netflow", tags=["NetFlow"])
    app.include_router(clustering.router, prefix="/api/clustering", tags=["Clustering"])
    app.include_router(policy.router, prefix="/api/policy", tags=["Policy"])
    app.include_router(visualization.router, prefix="/api/viz", tags=["Visualization"])
    app.include_router(export.router, prefix="/api/export", tags=["Export"])
    app.include_router(devices.router, prefix="/api", tags=["Devices"])
    app.include_router(groups.router, prefix="/api", tags=["Groups"])
    app.include_router(topology.router, prefix="/api", tags=["Topology"])
    app.include_router(collectors.router, prefix="/api", tags=["Collectors"])
    app.include_router(sgt.router, prefix="/api", tags=["SGT"])
    app.include_router(policy_recommendations.router, prefix="/api", tags=["Policy Recommendations"])
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )
    
    return app


# Create the app instance
app = create_app()

