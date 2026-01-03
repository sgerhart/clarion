"""
Policy Service

Manages policies, recommendations, and SGT lifecycle.
"""
import sys
from pathlib import Path

# Add src to path for shared code
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from clarion.storage import init_database, get_database
from clarion.api.routes import policy, policy_recommendations, sgt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db_path = os.environ.get("CLARION_DB_PATH", "/app/data/clarion.db")
init_database(db_path)
logger.info(f"Policy Service: Database initialized at {db_path}")

app = FastAPI(
    title="Clarion Policy Service",
    description="Policy management and recommendations service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(policy.router, prefix="/api", tags=["Policy"])
app.include_router(policy_recommendations.router, prefix="/api", tags=["Policy Recommendations"])
app.include_router(sgt.router, prefix="/api", tags=["SGT"])


@app.get("/health")
async def health():
    """Service health check."""
    try:
        db = get_database()
        return {"status": "healthy", "service": "policy-service"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

