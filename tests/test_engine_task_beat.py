import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from aioscpy.core.engine import ExecutionEngine


class TestEngineTaskBeat(unittest.TestCase):
    """Test the task beat optimizations in the ExecutionEngine."""

    def setUp(self):
        # Create mocks
        self.crawler = MagicMock()
        self.crawler.settings = {
            'TASK_BEAT_ACTIVE_SLEEP': 0.1,
            'TASK_BEAT_IDLE_SLEEP': 0.5,
            'TASK_BEAT_BATCH_SIZE': 10,
        }
        self.crawler.settings.getint = lambda key, default: self.crawler.settings.get(key, default)
        self.crawler.settings.getbool = lambda key, default: self.crawler.settings.get(key, default)
        self.crawler.settings.getfloat = lambda key, default: self.crawler.settings.get(key, default)
        
        self.slot = MagicMock()
        self.slot.scheduler = MagicMock()
        self.slot.scheduler.async_next_request = AsyncMock()
        self.slot.add_request = MagicMock()
        
        # Create engine
        self.engine = ExecutionEngine(self.crawler, lambda: None)
        self.engine.logger = MagicMock()
        self.engine._needs_backout = MagicMock(return_value=False)
        self.engine.slot = self.slot
        self.engine.downloader = MagicMock()
        self.engine.downloader.fetch = AsyncMock()
        
        # Patch asyncio.sleep to avoid actual sleeping
        self.sleep_patch = patch('asyncio.sleep', new=AsyncMock())
        self.mock_sleep = self.sleep_patch.start()

    def tearDown(self):
        self.sleep_patch.stop()

    async def _run_task_beat(self, iterations):
        """Helper to run the task_beat method for a specific number of iterations."""
        # Create a task for task_beat
        task = asyncio.create_task(self.engine.task_beat())
        
        # Let it run for a few iterations
        for _ in range(iterations):
            await asyncio.sleep(0)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def test_task_beat_with_requests(self):
        """Test that task_beat processes requests when available."""
        # Set up mock to return some requests
        mock_requests = [MagicMock() for _ in range(3)]
        self.slot.scheduler.async_next_request.return_value = mock_requests
        
        asyncio.run(self._run_task_beat(2))
        
        # Verify that scheduler.async_next_request was called with the batch size
        self.slot.scheduler.async_next_request.assert_called_with(count=10)
        
        # Verify that add_request and fetch were called for each request
        self.assertEqual(self.slot.add_request.call_count, 3)
        self.assertEqual(self.engine.downloader.fetch.call_count, 3)
        
        # Verify that we used the active sleep time
        self.mock_sleep.assert_called_with(0.1)

    def test_task_beat_no_requests(self):
        """Test that task_beat handles the case when no requests are available."""
        # Set up mock to return no requests
        self.slot.scheduler.async_next_request.return_value = []
        
        asyncio.run(self._run_task_beat(2))
        
        # Verify that scheduler.async_next_request was called
        self.slot.scheduler.async_next_request.assert_called()
        
        # Verify that add_request and fetch were not called
        self.slot.add_request.assert_not_called()
        self.engine.downloader.fetch.assert_not_called()
        
        # Verify that we used the idle sleep time
        self.mock_sleep.assert_called_with(0.5)

    def test_task_beat_with_backout(self):
        """Test that task_beat respects the backout condition."""
        # Set up mock to indicate backout is needed
        self.engine._needs_backout.return_value = True
        
        asyncio.run(self._run_task_beat(2))
        
        # Verify that scheduler.async_next_request was not called
        self.slot.scheduler.async_next_request.assert_not_called()
        
        # Verify that we used the idle sleep time
        self.mock_sleep.assert_called_with(0.5)


if __name__ == '__main__':
    unittest.main()
