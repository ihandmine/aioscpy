import asyncio
import pyhttpx

from anti_header import Headers


class PyHttpxDownloadHandler(object):

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler
        self.context = None

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
        pyhttpx_client_session = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'headers': headers,
            'allow_redirects': True,
            "data": request.body,
            "json": request.json
        }

        if request.meta.get("proxy"):
            pyhttpx_client_session['proxies'] = {'https': request.meta["proxy"]}
            self.logger.debug(f"use {request.meta['proxy']} crawling: {request.url}")
        
        session_args = {'http2': True}
        with pyhttpx.HttpSession(**session_args) as session:
            response = await asyncio.to_thread(session.request, request.method, request.url, **pyhttpx_client_session)

        return self.di.get("response")(
            str(request.url),
            status=response.status_code,
            headers=response.headers,
            body=response.content,
            cookies=response.cookies,
            _response=response)

    async def close(self):
        await asyncio.sleep(0.1)
