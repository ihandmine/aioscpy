import asyncio
import random

from curl_cffi.requests import AsyncSession

from anti_header import Headers


class CurlCffiDownloadHandler(object):

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler
        self.context = None
        self.browsers = [
            "chrome99",
            "chrome100",
            "chrome101",
            "chrome104",
            "chrome107",
            "chrome110",
            # "chrome116",
            "chrome99_android",
            "edge99",
            "edge101",
            # "ff91esr",
            # "ff95",
            # "ff98",
            # "ff100",
            # "ff102",
            # "ff109",
            # "ff117",
            "safari15_3",
            "safari15_5",
        ]

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
        session_kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'headers': headers,
            'allow_redirects': True,
            "data": request.body,
            "json": request.json
        }

        if request.meta.get('TLS_CIPHERS') or self.settings.get('TLS_CIPHERS'):
            session_kwargs['impersonate'] = random.choice(self.browsers)

        if request.meta.get("proxy"):
            session_kwargs['proxies'] = {
                'http': request.meta["proxy"],
                'https': request.meta["proxy"]
            }
            self.logger.debug(f"use {request.meta['proxy']} crawling: {request.url}")
        
        async with AsyncSession() as session:
            response = await session.request(request.method, request.url, **session_kwargs)
            content = response.content

        return self.di.get("response")(
            str(response.url),
            status=response.status_code,
            headers=response.headers,
            body=content,
            cookies=response.cookies,
            _response=response)

    async def close(self):
        await asyncio.sleep(0.1)
