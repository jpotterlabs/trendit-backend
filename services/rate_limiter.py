"""
Rate Limiting Service with Redis-based Sliding Window Counter

Provides accurate burst limiting for dashboard endpoints while preserving
existing DB sampling for monthly usage accounting.
"""

import os
import time
import json
import asyncio
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone, timedelta
from threading import Lock
from collections import defaultdict, deque

# Optional Redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter with sliding window counter implementation.
    
    Uses Redis if available, falls back to in-memory storage.
    Maintains separate counters for burst detection vs monthly usage.
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_store: Dict[str, deque] = defaultdict(deque)
        self.memory_lock = Lock()
        
        # Initialize Redis connection if available
        if REDIS_AVAILABLE:
            self._init_redis()
    
    def _init_redis(self) -> None:
        """Initialize Redis connection with fallback to memory"""
        try:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis connection established for rate limiting")
            else:
                # Local Redis fallback
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    db=int(os.getenv("REDIS_DB", "0")),
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Local Redis connection established for rate limiting")
                
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
            self.redis_client = None
    
    async def check_burst_limit(
        self, 
        user_id: int, 
        endpoint: str, 
        window_minutes: int = 5, 
        max_requests: int = 20
    ) -> Tuple[bool, int]:
        """
        Check burst limit using sliding window counter.
        
        Args:
            user_id: User identifier
            endpoint: Endpoint identifier
            window_minutes: Time window in minutes
            max_requests: Maximum requests allowed in window
            
        Returns:
            Tuple of (is_allowed, current_count)
        """
        key = f"burst:{user_id}:{endpoint}"
        now = int(time.time())
        window_start = now - (window_minutes * 60)
        
        if self.redis_client:
            return await self._check_redis_burst_limit(
                key, now, window_start, max_requests
            )
        else:
            return await self._check_memory_burst_limit(
                key, now, window_start, max_requests
            )
    
    async def increment_burst_counter(
        self, 
        user_id: int, 
        endpoint: str,
        window_minutes: int = 5
    ) -> int:
        """
        Increment burst counter and return current count.
        
        Args:
            user_id: User identifier
            endpoint: Endpoint identifier  
            window_minutes: Time window in minutes
            
        Returns:
            Current count in window
        """
        key = f"burst:{user_id}:{endpoint}"
        now = int(time.time())
        expire_seconds = window_minutes * 60
        
        if self.redis_client:
            return await self._increment_redis_counter(key, now, expire_seconds)
        else:
            return await self._increment_memory_counter(key, now, expire_seconds)
    
    async def _check_redis_burst_limit(
        self, 
        key: str, 
        now: int, 
        window_start: int, 
        max_requests: int
    ) -> Tuple[bool, int]:
        """Check burst limit using Redis sliding window"""
        try:
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries in window
            pipe.zcard(key)
            
            results = pipe.execute()
            current_count = results[1]
            
            is_allowed = current_count < max_requests
            return is_allowed, current_count
            
        except Exception as e:
            logger.error(f"Redis burst limit check failed: {e}")
            # Fallback to allowing request
            return True, 0
    
    async def _increment_redis_counter(
        self, 
        key: str, 
        now: int, 
        expire_seconds: int
    ) -> int:
        """Increment Redis counter atomically"""
        try:
            pipe = self.redis_client.pipeline()
            
            # Add current timestamp to sorted set
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, expire_seconds)
            
            # Remove old entries and count current
            window_start = now - expire_seconds
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            
            results = pipe.execute()
            return results[3]  # Count after cleanup
            
        except Exception as e:
            logger.error(f"Redis counter increment failed: {e}")
            return 0
    
    async def _check_memory_burst_limit(
        self, 
        key: str, 
        now: int, 
        window_start: int, 
        max_requests: int
    ) -> Tuple[bool, int]:
        """Check burst limit using in-memory sliding window"""
        with self.memory_lock:
            requests = self.memory_store[key]
            
            # Remove expired entries
            while requests and requests[0] < window_start:
                requests.popleft()
            
            current_count = len(requests)
            is_allowed = current_count < max_requests
            
            return is_allowed, current_count
    
    async def _increment_memory_counter(
        self, 
        key: str, 
        now: int, 
        expire_seconds: int
    ) -> int:
        """Increment in-memory counter"""
        window_start = now - expire_seconds
        
        with self.memory_lock:
            requests = self.memory_store[key]
            
            # Remove expired entries
            while requests and requests[0] < window_start:
                requests.popleft()
            
            # Add current request
            requests.append(now)
            
            return len(requests)
    
    async def cleanup_memory_store(self) -> None:
        """Periodic cleanup of expired in-memory entries"""
        if self.redis_client:
            return  # Redis handles expiration automatically
        
        now = int(time.time())
        five_minutes_ago = now - 300  # 5 minutes
        
        with self.memory_lock:
            keys_to_clean = []
            for key, requests in self.memory_store.items():
                # Remove expired entries
                while requests and requests[0] < five_minutes_ago:
                    requests.popleft()
                
                # Mark empty queues for deletion
                if not requests:
                    keys_to_clean.append(key)
            
            # Clean up empty entries
            for key in keys_to_clean:
                del self.memory_store[key]
        
        logger.debug(f"Cleaned up {len(keys_to_clean)} empty rate limit entries")

# Global rate limiter instance
rate_limiter = RateLimiter()

async def check_dashboard_burst_limit(user_id: int, endpoint: str) -> Tuple[bool, int]:
    """
    Check dashboard burst limit for user endpoint.
    
    Args:
        user_id: User ID
        endpoint: Endpoint identifier
        
    Returns:
        Tuple of (is_allowed, current_count)
    """
    return await rate_limiter.check_burst_limit(
        user_id=user_id,
        endpoint=endpoint,
        window_minutes=5,
        max_requests=20
    )

async def record_dashboard_request(user_id: int, endpoint: str) -> int:
    """
    Record dashboard request and return current count.
    
    Args:
        user_id: User ID
        endpoint: Endpoint identifier
        
    Returns:
        Current request count in 5-minute window
    """
    return await rate_limiter.increment_burst_counter(
        user_id=user_id,
        endpoint=endpoint,
        window_minutes=5
    )

# Background cleanup task for in-memory store
async def periodic_cleanup():
    """Background task to clean up expired in-memory entries"""
    while True:
        await asyncio.sleep(300)  # Clean every 5 minutes
        await rate_limiter.cleanup_memory_store()

# Start cleanup task when module is imported
def start_cleanup_task():
    """Start the periodic cleanup task"""
    try:
        asyncio.create_task(periodic_cleanup())
    except RuntimeError:
        # No event loop running, will start when needed
        pass

# Initialize cleanup
start_cleanup_task()