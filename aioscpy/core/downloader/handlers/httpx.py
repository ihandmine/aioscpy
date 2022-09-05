import asyncio
import ssl
import httpx

from anti_header import Headers
from anti_useragent.utils.cipers import generate_cipher


class HttpxDownloadHandler(object):

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler
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
        httpx_client_session = {}

        if request.meta.get('TLS_CIPHERS') or self.settings.get('TLS_CIPHERS'):
            self.context.set_ciphers(generate_cipher())
            httpx_client_session['verify'] = self.context

        if request.meta.get("proxy"):
            httpx_client_session['proxies'] = request.meta["proxy"]
            self.logger.debug(f"use {request.meta['proxy']} crawling: {request.url}")

        async with httpx.AsyncClient(**httpx_client_session) as session:
            response = await session.request(request.method, request.url, **{
                'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
                'cookies': dict(request.cookies),
                'data': request.body or None,
                'headers': headers
            })
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
