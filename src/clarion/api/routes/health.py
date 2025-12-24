"""
Health Check Endpoints
"""

from fastapi import APIRouter
from datetime import datetime
import os

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.5.0",
    }


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with system metrics."""
    if HAS_PSUTIL:
        process = psutil.Process(os.getpid())
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "0.5.0",
            "system": {
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "memory_percent": process.memory_percent(),
            },
        }
    else:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "0.5.0",
            "system": {
                "note": "psutil not available",
            },
        }

