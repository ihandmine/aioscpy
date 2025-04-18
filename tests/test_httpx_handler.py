import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

import httpx

from aioscpy.core.downloader.handlers.httpx import HttpxDownloadHandler


class TestHttpxHandler(unittest.TestCase):
    """Test the improved error handling in the HttpxDownloadHandler."""

    def setUp(self):
        # Create mocks
        self.settings = {
            'DOWNLOAD_TIMEOUT': 10,
        }
        self.settings.get = lambda key, default=None: self.settings.get(key, default)
        
        self.crawler = MagicMock()
        self.crawler.settings = self.settings
        
        self.spider = MagicMock()
        self.spider.name = 'test_spider'
        
        # Create request mock
        self.request = MagicMock()
        self.request.url = 'https://example.com'
        self.request.method = 'GET'
        self.request.headers = {}
        self.request.cookies = {}
        self.request.body = None
        self.request.json = None
        self.request.meta = {}
        
        # Create handler
        self.handler = HttpxDownloadHandler(self.settings, self.crawler)
        self.handler.logger = MagicMock()
        
        # Mock the dependency injection
        self.mock_response_cls = MagicMock()
        self.handler.di = MagicMock()
        self.handler.di.get.return_value = self.mock_response_cls
        
        # Patch httpx.AsyncClient
        self.client_patch = patch('httpx.AsyncClient')
        self.mock_client_cls = self.client_patch.start()
        self.mock_client = AsyncMock()
        self.mock_client_cls.return_value.__aenter__.return_value = self.mock_client
        
        # Create a mock response
        self.mock_http_response = MagicMock()
        self.mock_http_response.url = 'https://example.com'
        self.mock_http_response.status_code = 200
        self.mock_http_response.headers = {}
        self.mock_http_response.cookies = {}
        self.mock_http_response.read.return_value = b'response content'
        
        # Set up the client to return the mock response
        self.mock_client.request.return_value = self.mock_http_response

    def tearDown(self):
        self.client_patch.stop()

    async def test_successful_request(self):
        """Test that a successful request returns a response object."""
        response = await self.handler.download_request(self.request, self.spider)
        
        # Verify that the client was called with the correct arguments
        self.mock_client.request.assert_called_once()
        args, kwargs = self.mock_client.request.call_args
        self.assertEqual(args[0], 'GET')
        self.assertEqual(args[1], 'https://example.com')
        
        # Verify that the response was created correctly
        self.mock_response_cls.assert_called_once()
        self.assertEqual(response, self.mock_response_cls.return_value)

    async def test_timeout_exception(self):
        """Test that a timeout exception is handled properly."""
        # Make the client raise a timeout exception
        self.mock_client.request.side_effect = httpx.TimeoutException('Timeout')
        
        # Mock the exceptions
        mock_timeout_error = MagicMock()
        self.handler.di.get.side_effect = lambda x: mock_timeout_error if x == 'exceptions' else self.mock_response_cls
        
        with self.assertRaises(Exception):
            await self.handler.download_request(self.request, self.spider)
        
        # Verify that the error was logged
        self.handler.logger.warning.assert_called_once()
        
        # Verify that the correct exception was raised
        mock_timeout_error.TimeoutError.assert_called_once()

    async def test_request_error(self):
        """Test that a request error is handled properly."""
        # Make the client raise a request error
        self.mock_client.request.side_effect = httpx.RequestError('Connection error')
        
        # Mock the exceptions
        mock_connection_error = MagicMock()
        self.handler.di.get.side_effect = lambda x: mock_connection_error if x == 'exceptions' else self.mock_response_cls
        
        with self.assertRaises(Exception):
            await self.handler.download_request(self.request, self.spider)
        
        # Verify that the error was logged
        self.handler.logger.warning.assert_called_once()
        
        # Verify that the correct exception was raised
        mock_connection_error.ConnectionError.assert_called_once()

    async def test_unexpected_error(self):
        """Test that an unexpected error is handled properly."""
        # Make the client raise an unexpected error
        self.mock_client.request.side_effect = ValueError('Unexpected error')
        
        # Mock the exceptions
        mock_download_error = MagicMock()
        self.handler.di.get.side_effect = lambda x: mock_download_error if x == 'exceptions' else self.mock_response_cls
        
        with self.assertRaises(Exception):
            await self.handler.download_request(self.request, self.spider)
        
        # Verify that the error was logged
        self.handler.logger.error.assert_called_once()
        
        # Verify that the correct exception was raised
        mock_download_error.DownloadError.assert_called_once()

    async def test_proxy_configuration(self):
        """Test that proxy configuration is handled properly."""
        # Set up a request with a proxy
        self.request.meta['proxy'] = 'http://proxy.example.com:8080'
        
        await self.handler.download_request(self.request, self.spider)
        
        # Verify that the client was created with the proxy
        args, kwargs = self.mock_client_cls.call_args
        self.assertEqual(kwargs['proxies'], 'http://proxy.example.com:8080')
        
        # Verify that the proxy usage was logged
        self.handler.logger.debug.assert_called_once()


if __name__ == '__main__':
    unittest.main()
