"""
Request throttling and rate limiting
"""
import asyncio
import time
import random
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class RequestThrottler:
    """Throttle requests to respect rate limits"""
    
    def __init__(self, concurrency: int = 3, delay_range: Tuple[float, float] = (1.0, 3.0)):
        """
        Initialize throttler
        
        Args:
            concurrency: Maximum concurrent requests
            delay_range: Random delay range between requests (min, max) in seconds
        """
        self.concurrency = concurrency
        self.delay_range = delay_range
        self.semaphore = asyncio.Semaphore(concurrency)
        self.last_request_time = 0
        self._lock = asyncio.Lock()
    
    async def wait(self):
        """Wait before making a request"""
        async with self._lock:
            # Calculate time since last request
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            # Calculate random delay
            min_delay, max_delay = self.delay_range
            required_delay = random.uniform(min_delay, max_delay)
            
            # Wait if needed
            if time_since_last < required_delay:
                sleep_time = required_delay - time_since_last
                logger.debug(f"Throttling request, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
            
            # Update last request time
            self.last_request_time = time.time()
    
    async def acquire(self):
        """Acquire semaphore for concurrent request control"""
        await self.semaphore.acquire()
    
    def release(self):
        """Release semaphore"""
        self.semaphore.release()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.acquire()
        await self.wait()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.release()