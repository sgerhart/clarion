"""
Retry logic with exponential backoff for backend communication.
"""

import asyncio
import logging
from typing import Callable, Any, Optional
import httpx

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
    initial_delay: float = 1.0,
    exceptions: tuple = (httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError),
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts
        backoff_factor: Multiplier for delay between retries
        initial_delay: Initial delay in seconds
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Result of function call
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"All {max_attempts} attempts failed")
                raise
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception

