import asyncio
import logging
import ssl
import sys
import aiohttp

from aioscpy.http import TextResponse
from anti_header import Headers

logger = logging.getLogger(__name__)


class AioHttpDownloadHandler:
    session = None

    def __init__(self, settings):
        self.settings = settings
        self.aiohttp_client_session_args = settings.get('AIOHTTP_CLIENT_SESSION_ARGS', {})
        self.verify_ssl = self.settings.get("VERIFY_SSL")

    @classmethod
    def from_settings(cls, settings):
        return cls(settings)

    def get_session(self, *args, **kwargs):
        if self.session is None:
            self.session = aiohttp.ClientSession(*args, **kwargs)
        return self.session

    async def download_request(self, request, spider):
        kwargs = {
            'verify_ssl': request.meta.get('verify_ssl', self.verify_ssl),
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'data': request.body or None
        }

        headers = request.headers or self.settings.get('DEFAULT_REQUEST_HEADERS')
        if isinstance(headers, Headers):
            headers = headers.to_unicode_dict()
        kwargs['headers'] = headers

        ssl_ciphers = request.meta.get('TLS_CIPHERS')
        if ssl_ciphers:
            context = ssl.create_default_context()
            context.set_ciphers(ssl_ciphers)
            kwargs['ssl'] = context

        proxy = request.meta.get("proxy")
        if proxy:
            kwargs["proxy"] = proxy
            logger.debug(f"use {proxy} crawling: {request.url}")

        async with aiohttp.ClientSession(**self.aiohttp_client_session_args) as session:
            async with session.request(request.method, request.url, **kwargs) as response:
                content = await response.read()

        return TextResponse(str(response.url),
                            status=response.status,
                            headers=response.headers,
                            body=content,
                            cookies=response.cookies,
                            _response=response)

    async def close(self):
        if self.session is not None:
            await self.session.close()

        # Wait 250 ms for the underlying SSL connections to close
        # https://docs.aiohttp.org/en/latest/client_advanced.html#graceful-shutdown
        await asyncio.sleep(0.250)
