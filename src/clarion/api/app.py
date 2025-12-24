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
    clustering,
    policy,
    visualization,
    export,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Clarion TrustSec Policy Copilot API",
        description="Scale-first network segmentation using edge processing and unsupervised learning",
        version="0.5.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(sketches.router, prefix="/api/edge", tags=["Edge"])
    app.include_router(clustering.router, prefix="/api/clustering", tags=["Clustering"])
    app.include_router(policy.router, prefix="/api/policy", tags=["Policy"])
    app.include_router(visualization.router, prefix="/api/viz", tags=["Visualization"])
    app.include_router(export.router, prefix="/api/export", tags=["Export"])
    
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

