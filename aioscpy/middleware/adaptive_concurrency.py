import time
from collections import deque

from aioscpy.middleware.manager import MiddlewareManager


class AdaptiveConcurrencyMiddleware:
    """
    Middleware that adjusts concurrency based on response times.
    
    This middleware monitors response times and adjusts the concurrency
    settings dynamically to maintain optimal performance.
    """
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.enabled = self.settings.getbool('ADAPTIVE_CONCURRENCY_ENABLED', False)
        
        if not self.enabled:
            return
            
        # Configuration
        self.target_response_time = self.settings.getfloat('ADAPTIVE_CONCURRENCY_TARGET_RESPONSE_TIME', 1.0)
        self.min_concurrency = self.settings.getint('ADAPTIVE_CONCURRENCY_MIN_REQUESTS', 8)
        self.max_concurrency = self.settings.getint('ADAPTIVE_CONCURRENCY_MAX_REQUESTS', 32)
        self.window_size = self.settings.getint('ADAPTIVE_CONCURRENCY_WINDOW_SIZE', 20)
        self.adjustment_interval = self.settings.getint('ADAPTIVE_CONCURRENCY_ADJUSTMENT_INTERVAL', 10)
        
        # State
        self.response_times = deque(maxlen=self.window_size)
        self.last_adjustment_time = time.time()
        self.current_concurrency = self.settings.getint('CONCURRENT_REQUESTS', 16)
        
        # Set initial concurrency
        self.crawler.settings.set('CONCURRENT_REQUESTS', self.current_concurrency)
        self.logger.info(f"Adaptive concurrency enabled. Initial concurrency: {self.current_concurrency}")
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    async def process_request(self, request, spider):
        if not self.enabled:
            return None
            
        # Store request start time
        request.meta['request_start_time'] = time.time()
        return None
    
    async def process_response(self, request, response, spider):
        if not self.enabled or 'request_start_time' not in request.meta:
            return response
            
        # Calculate response time
        response_time = time.time() - request.meta['request_start_time']
        self.response_times.append(response_time)
        
        # Adjust concurrency if needed
        current_time = time.time()
        if (current_time - self.last_adjustment_time) >= self.adjustment_interval and len(self.response_times) >= self.window_size:
            self._adjust_concurrency()
            self.last_adjustment_time = current_time
            
        return response
    
    def _adjust_concurrency(self):
        """Adjust concurrency based on average response time"""
        avg_response_time = sum(self.response_times) / len(self.response_times)
        
        # Calculate adjustment factor
        adjustment_factor = self.target_response_time / avg_response_time
        
        # Apply adjustment with limits
        new_concurrency = int(self.current_concurrency * adjustment_factor)
        new_concurrency = max(self.min_concurrency, min(self.max_concurrency, new_concurrency))
        
        # Only update if there's a significant change
        if new_concurrency != self.current_concurrency:
            self.current_concurrency = new_concurrency
            self.crawler.settings.set('CONCURRENT_REQUESTS', new_concurrency)
            self.logger.info(
                f"Adjusted concurrency to {new_concurrency} (avg response time: {avg_response_time:.2f}s, "
                f"target: {self.target_response_time:.2f}s)"
            )
