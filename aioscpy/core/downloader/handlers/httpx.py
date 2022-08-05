import asyncio
import ssl
import httpx

from anti_header import Headers
from anti_useragent.utils.cipers import generate_cipher


class HttpxDownloadHandler(object):

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler
        self.verify_ssl = self.settings.get("VERIFY_SSL")
        self.context = ssl.create_default_context()

    @classmethod
    def from_settings(cls, settings, crawler):
        return cls(settings, crawler)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings, crawler)

    async def download_request(self, request, spider):
        headers = request.headers
        if isinstance(headers, Headers):
            headers = headers.to_unicode_dict()
        kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'data': request.body or None,
            'headers': headers
        }
        httpx_client_session = {}

        ssl_ciphers = request.meta.get('TLS_CIPHERS') or self.settings.get('TLS_CIPHERS')
        if ssl_ciphers:
            self.context.set_ciphers(generate_cipher())
            httpx_client_session['verify'] = self.context

        proxy = request.meta.get("proxy")
        if proxy:
            httpx_client_session['proxies'] = proxy
            self.logger.debug(f"use {proxy} crawling: {request.url}")

        async with httpx.AsyncClient(**httpx_client_session) as session:
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
        await asyncio.sleep(0.1)