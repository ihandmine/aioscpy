import unittest
import time
from unittest.mock import MagicMock, patch

from aioscpy.middleware.adaptive_concurrency import AdaptiveConcurrencyMiddleware


class TestAdaptiveConcurrencyMiddleware(unittest.TestCase):
    """Test the AdaptiveConcurrencyMiddleware."""

    def setUp(self):
        # Create mocks
        self.crawler = MagicMock()
        self.crawler.settings = {
            'ADAPTIVE_CONCURRENCY_ENABLED': True,
            'ADAPTIVE_CONCURRENCY_TARGET_RESPONSE_TIME': 0.5,
            'ADAPTIVE_CONCURRENCY_MIN_REQUESTS': 5,
            'ADAPTIVE_CONCURRENCY_MAX_REQUESTS': 20,
            'ADAPTIVE_CONCURRENCY_WINDOW_SIZE': 10,
            'ADAPTIVE_CONCURRENCY_ADJUSTMENT_INTERVAL': 1,
            'CONCURRENT_REQUESTS': 10,
        }
        self.crawler.settings.getbool = lambda key, default: self.crawler.settings.get(key, default)
        self.crawler.settings.getfloat = lambda key, default: self.crawler.settings.get(key, default)
        self.crawler.settings.getint = lambda key, default: self.crawler.settings.get(key, default)
        
        self.spider = MagicMock()
        self.spider.name = 'test_spider'
        
        # Create middleware
        self.middleware = AdaptiveConcurrencyMiddleware(self.crawler)
        self.middleware.logger = MagicMock()
        
        # Create request and response mocks
        self.request = MagicMock()
        self.request.meta = {}
        self.response = MagicMock()

    async def test_process_request_adds_start_time(self):
        """Test that process_request adds a start time to the request meta."""
        result = await self.middleware.process_request(self.request, self.spider)
        
        # Verify that the result is None (middleware continues)
        self.assertIsNone(result)
        
        # Verify that a start time was added to the request meta
        self.assertIn('request_start_time', self.request.meta)
        self.assertIsInstance(self.request.meta['request_start_time'], float)

    async def test_process_response_calculates_time(self):
        """Test that process_response calculates the response time."""
        # Set up a request with a start time
        start_time = time.time() - 0.3  # 300ms ago
        self.request.meta['request_start_time'] = start_time
        
        result = await self.middleware.process_response(self.request, self.response, self.spider)
        
        # Verify that the result is the response
        self.assertEqual(result, self.response)
        
        # Verify that a response time was added to the deque
        self.assertEqual(len(self.middleware.response_times), 1)
        self.assertGreaterEqual(self.middleware.response_times[0], 0.3)

    async def test_adjust_concurrency_faster_responses(self):
        """Test that concurrency is increased when responses are faster than target."""
        # Fill the response times deque with fast responses (0.2s)
        self.middleware.response_times.extend([0.2] * self.middleware.window_size)
        self.middleware.current_concurrency = 10
        
        # Adjust concurrency
        self.middleware._adjust_concurrency()
        
        # Verify that concurrency was increased
        self.assertGreater(self.middleware.current_concurrency, 10)
        
        # Verify that the setting was updated
        self.crawler.settings.set.assert_called_with('CONCURRENT_REQUESTS', self.middleware.current_concurrency)
        
        # Verify that the change was logged
        self.middleware.logger.info.assert_called_once()

    async def test_adjust_concurrency_slower_responses(self):
        """Test that concurrency is decreased when responses are slower than target."""
        # Fill the response times deque with slow responses (1.0s)
        self.middleware.response_times.extend([1.0] * self.middleware.window_size)
        self.middleware.current_concurrency = 10
        
        # Adjust concurrency
        self.middleware._adjust_concurrency()
        
        # Verify that concurrency was decreased
        self.assertLess(self.middleware.current_concurrency, 10)
        
        # Verify that the setting was updated
        self.crawler.settings.set.assert_called_with('CONCURRENT_REQUESTS', self.middleware.current_concurrency)
        
        # Verify that the change was logged
        self.middleware.logger.info.assert_called_once()

    async def test_adjust_concurrency_respects_min_max(self):
        """Test that concurrency adjustments respect the min and max limits."""
        # Test minimum limit
        self.middleware.response_times.extend([2.0] * self.middleware.window_size)  # Very slow responses
        self.middleware.current_concurrency = 6
        
        self.middleware._adjust_concurrency()
        
        # Verify that concurrency was not decreased below the minimum
        self.assertEqual(self.middleware.current_concurrency, 5)
        
        # Test maximum limit
        self.middleware.response_times.clear()
        self.middleware.response_times.extend([0.1] * self.middleware.window_size)  # Very fast responses
        self.middleware.current_concurrency = 19
        
        self.middleware._adjust_concurrency()
        
        # Verify that concurrency was not increased above the maximum
        self.assertEqual(self.middleware.current_concurrency, 20)

    async def test_disabled_middleware(self):
        """Test that the middleware does nothing when disabled."""
        # Disable the middleware
        self.middleware.enabled = False
        
        # Process a request
        result = await self.middleware.process_request(self.request, self.spider)
        
        # Verify that the result is None
        self.assertIsNone(result)
        
        # Verify that no start time was added
        self.assertNotIn('request_start_time', self.request.meta)
        
        # Process a response
        result = await self.middleware.process_response(self.request, self.response, self.spider)
        
        # Verify that the result is the response
        self.assertEqual(result, self.response)
        
        # Verify that no response times were recorded
        self.assertEqual(len(self.middleware.response_times), 0)


if __name__ == '__main__':
    unittest.main()
