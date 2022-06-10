import asyncio
import ssl
import httpx

from anti_header import Headers
from anti_useragent.utils.cipers import generate_cipher


class HttpxDownloadHandler(object):
    session = None

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler
        self.httpx_client_session_args = settings.get(
            'HTTPX_CLIENT_SESSION_ARGS', {})
        self.verify_ssl = self.settings.get("VERIFY_SSL")

    @classmethod
    def from_settings(cls, settings, crawler):
        return cls(settings, crawler)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings, crawler)

    def get_session(self, *args, **kwargs):
        if self.session is None:
            self.session = httpx.AsyncClient()
        return self.session

    async def download_request(self, request, spider):
        kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'data': request.body or None
        }

        headers = request.headers or self.settings.get(
            'DEFAULT_REQUEST_HEADERS')
        if isinstance(headers, Headers):
            headers = headers.to_unicode_dict()
        kwargs['headers'] = headers

        ssl_ciphers = request.meta.get(
            'TLS_CIPHERS') or self.settings.get('TLS_CIPHERS')
        if ssl_ciphers:
            context = ssl.create_default_context()
            context.set_ciphers(generate_cipher())
            kwargs['verify'] = context

        proxy = request.meta.get("proxy")
        if proxy:
            kwargs["proxies"] = proxy
            self.logger.debug(f"use {proxy} crawling: {request.url}")

        async with httpx.AsyncClient(**self.httpx_client_session_args) as session:
            response = await session.request(request.method, request.url, **kwargs)
            content = response.read()

        return self.di.get("response")(
            str(response.url),
            status=response.status_code,
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
