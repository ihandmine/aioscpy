import asyncio
import requests

from anti_header import Headers
from anti_useragent.utils.cipers import generate_cipher


class RequestsDownloadHandler(object):

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler

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
        requests_client_session = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'headers': headers,
            'allow_redirects': request.meta.get("allow_redirects", True),
            "data": request.body,
            "json": request.json,
        }

        if request.meta.get('TLS_CIPHERS') or self.settings.get('TLS_CIPHERS'):
            requests.adapters.DEFAULT_RETRIES = 10
            requests.packages.urllib3.disable_warnings()
            cipers_real = generate_cipher()
            self.logger.debug(cipers_real)
            requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = cipers_real

        if request.meta.get("proxy"):
            requests_client_session['proxies'] = {
                'http': request.meta["proxy"],
                'https': request.meta["proxy"]
            }
            self.logger.debug(f"use {request.meta['proxy']} crawling: {request.url}")


        
        response = await asyncio.to_thread(requests.request, request.method, request.url, **requests_client_session)

        return self.di.get("response")(
            str(response.url),
            status=response.status_code,
            headers=response.headers,
            body=response.content,
            cookies=response.cookies,
            _response=response)

    async def close(self):
        await asyncio.sleep(0.1)
