import asyncio
import ssl
import aiohttp

from anti_header import Headers
from anti_useragent.utils.cipers import generate_cipher


class AioHttpDownloadHandler(object):
    session = None

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler
        self.context = ssl.create_default_context()
        self.aiohttp_client_session = {
            'timeout': aiohttp.ClientTimeout(total=20),
            'trust_env': True,
            "connector": aiohttp.TCPConnector(
                verify_ssl=False,
                limit=1000,
                force_close=True,
                use_dns_cache=False,
                limit_per_host=200,
                enable_cleanup_closed=True
            )
        }
        self.session = None

    @classmethod
    def from_settings(cls, settings, crawler):
        return cls(settings, crawler)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings, crawler)

    def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(**self.aiohttp_client_session)
        return self.session

    async def download_request(self, request, spider):
        kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'data': request.body or None
        }
        self.session = self.get_session()
        headers = request.headers
        if isinstance(headers, Headers):
            headers = headers.to_unicode_dict()
        kwargs['headers'] = headers

        ssl_ciphers = request.meta.get('TLS_CIPHERS') or self.settings.get('TLS_CIPHERS')
        if ssl_ciphers:
            self.context.set_ciphers(generate_cipher())
            kwargs['ssl'] = self.context

        proxy = request.meta.get("proxy")
        if proxy:
            kwargs["proxy"] = proxy
            self.logger.debug(f"use {proxy} crawling: {request.url}")

        # async with aiohttp.ClientSession(**aiohttp_client_session) as session:
        # async with session.request(request.method, request.url, **kwargs) as response:
        response = await self.session.request(request.method, request.url, **kwargs)
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
