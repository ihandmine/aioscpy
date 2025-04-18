import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from aioscpy.core.engine import ExecutionEngine


class TestEngineMemoryManagement(unittest.TestCase):
    """Test the memory management optimizations in the ExecutionEngine."""

    def setUp(self):
        # Create mocks
        self.crawler = MagicMock()
        self.crawler.settings = {
            'GC_ENABLED': True,
            'GC_FREQUENCY': 3,  # Set to a small value for testing
        }
        self.crawler.settings.getint = lambda key, default: self.crawler.settings.get(key, default)
        self.crawler.settings.getbool = lambda key, default: self.crawler.settings.get(key, default)
        self.crawler.settings.getfloat = lambda key, default: self.crawler.settings.get(key, default)
        
        self.spider = MagicMock()
        self.spider.name = 'test_spider'
        
        self.slot = MagicMock()
        self.slot.close_if_idle = True
        
        # Create engine
        self.engine = ExecutionEngine(self.crawler, lambda: None)
        self.engine.logger = MagicMock()
        self.engine.spider_is_idle = AsyncMock(return_value=False)
        
        # Patch asyncio.sleep to avoid actual sleeping
        self.sleep_patch = patch('asyncio.sleep', new=AsyncMock())
        self.mock_sleep = self.sleep_patch.start()
        
        # Patch gc.collect
        self.gc_patch = patch('gc.collect')
        self.mock_gc = self.gc_patch.start()

    def tearDown(self):
        self.sleep_patch.stop()
        self.gc_patch.stop()

    async def _run_heart_beat(self, iterations):
        """Helper to run the heart_beat method for a specific number of iterations."""
        # Create a task for heart_beat
        task = asyncio.create_task(self.engine.heart_beat(0.1, self.spider, self.slot))
        
        # Let it run for a few iterations
        for _ in range(iterations):
            await asyncio.sleep(0)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def test_gc_enabled(self):
        """Test that garbage collection runs when enabled."""
        asyncio.run(self._run_heart_beat(10))
        
        # With GC_FREQUENCY=3, we should have called gc.collect about 3 times in 10 iterations
        # (not exactly 3 because of the counter initialization and async nature)
        self.assertGreaterEqual(self.mock_gc.call_count, 2)
        self.assertLessEqual(self.mock_gc.call_count, 4)

    def test_gc_disabled(self):
        """Test that garbage collection doesn't run when disabled."""
        self.crawler.settings['GC_ENABLED'] = False
        
        asyncio.run(self._run_heart_beat(10))
        
        # With GC_ENABLED=False, gc.collect should never be called
        self.mock_gc.assert_not_called()

    def test_gc_frequency(self):
        """Test that garbage collection respects the frequency setting."""
        # Set frequency to 5
        self.crawler.settings['GC_FREQUENCY'] = 5
        
        asyncio.run(self._run_heart_beat(15))
        
        # With GC_FREQUENCY=5, we should have called gc.collect about 3 times in 15 iterations
        self.assertGreaterEqual(self.mock_gc.call_count, 2)
        self.assertLessEqual(self.mock_gc.call_count, 4)

    def test_gc_exception_handling(self):
        """Test that exceptions in garbage collection are handled properly."""
        # Make gc.collect raise an exception
        self.mock_gc.side_effect = Exception("Test exception")
        
        asyncio.run(self._run_heart_beat(5))
        
        # The exception should be caught and logged
        self.engine.logger.warning.assert_called()
        
        # The heart_beat should continue running despite the exception
        self.assertGreater(self.mock_sleep.call_count, 3)


if __name__ == '__main__':
    unittest.main()
