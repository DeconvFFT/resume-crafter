"""Shared dependencies for the application.

This module provides shared dependencies that can be reused across multiple routes,
avoiding code duplication and ensuring consistent behavior.
"""

import logging
from typing import AsyncGenerator

from arq import ArqRedis, create_pool

logger = logging.getLogger(__name__)

# Module-level connection pool for reuse
_arq_pool: ArqRedis | None = None


async def get_arq_redis() -> ArqRedis:
    """Get ARQ Redis connection with connection pooling.
    
    This function reuses an existing connection pool if available,
    avoiding the overhead of creating new connections for each request.
    
    Returns:
        ArqRedis: The ARQ Redis connection pool.
    """
    global _arq_pool
    
    if _arq_pool is None:
        from src.tasks.worker import get_redis_settings
        _arq_pool = await create_pool(get_redis_settings())
        logger.info("Created new ARQ Redis connection pool")
    
    return _arq_pool


async def close_arq_redis() -> None:
    """Close the ARQ Redis connection pool.
    
    Should be called during application shutdown.
    """
    global _arq_pool
    
    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
        logger.info("Closed ARQ Redis connection pool")
