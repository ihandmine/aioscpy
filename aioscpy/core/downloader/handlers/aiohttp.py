import asyncio
import ssl
import aiohttp
import ujson
import json

from anti_header import Headers
from anti_useragent.utils.cipers import generate_cipher


class AioHttpDownloadHandler(object):

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler
        self.aiohttp_client_session = {
            'timeout': aiohttp.ClientTimeout(total=20),
            'trust_env': True,
            'json_serialize': ujson.dumps,
            "connector": aiohttp.TCPConnector(
                verify_ssl=False,
                limit=1000,
                force_close=True,
                use_dns_cache=False,
                limit_per_host=200,
                enable_cleanup_closed=True
            )
        }
        self.session_stats = self.settings.getbool("REQUESTS_SESSION_STATS", False)
        self.session = None
        self.context = None

    @classmethod
    def from_settings(cls, settings, crawler):
        return cls(settings, crawler)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings, crawler)

    async def download_request(self, request, spider):
        session_kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            "data": request.body,
            "json": request.json
        }
        headers = request.headers
        if isinstance(headers, Headers):
            headers = headers.to_unicode_dict()
        session_kwargs['headers'] = headers

        if request.meta.get('TLS_CIPHERS') or self.settings.get('TLS_CIPHERS'):
            self.context = ssl.create_default_context()
            self.context.set_ciphers(generate_cipher())
            session_kwargs['ssl'] = self.context

        if request.meta.get("proxy"):
            session_kwargs["proxy"] = request.meta['proxy']
            self.logger.debug(f"use {request.meta['proxy']} crawling: {request.url}")

        if self.session_stats:
            if self.session is None:
                self.session = aiohttp.ClientSession(**self.aiohttp_client_session)
            response = await self.session.request(request.method, request.url, **session_kwargs)
            content = await response.read()
        else:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20),
                trust_env=True,
                connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                async with session.request(request.method, request.url, **session_kwargs) as response:
                    content = await response.read()

        return self.di.get("response")(
            str(response.url),
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
