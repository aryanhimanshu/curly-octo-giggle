import asyncio
from datetime import datetime, timedelta
from typing import Optional

class RateLimiter:
    def __init__(self, delay: float):
        """
        Initialize rate limiter with specified delay between requests.
        
        Args:
            delay (float): Minimum time (in seconds) between requests
        """
        self.delay = delay
        self.last_request_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to make a request, waiting if necessary to respect the rate limit.
        """
        async with self._lock:
            if self.last_request_time is not None:
                # Calculate time to wait
                time_since_last = datetime.now() - self.last_request_time
                wait_time = self.delay - time_since_last.total_seconds()
                
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            self.last_request_time = datetime.now() 