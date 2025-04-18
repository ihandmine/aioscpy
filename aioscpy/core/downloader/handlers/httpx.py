import asyncio
import ssl
import httpx

from anti_header import Headers
from anti_useragent.utils.cipers import generate_cipher


class HttpxDownloadHandler(object):

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
        httpx_client_session = {}

        # Configure TLS settings if needed
        if request.meta.get('TLS_CIPHERS') or self.settings.get('TLS_CIPHERS'):
            try:
                self.context = ssl.create_default_context()
                self.context.set_ciphers(generate_cipher())
                httpx_client_session['verify'] = self.context
            except Exception as e:
                self.logger.warning(f"Error configuring TLS for {request.url}: {str(e)}")

        # Configure proxy if specified
        if request.meta.get("proxy"):
            httpx_client_session['proxies'] = request.meta["proxy"]
            self.logger.debug(f"Using proxy {request.meta['proxy']} for: {request.url}")

        # Prepare session arguments
        session_kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'headers': headers,
            'follow_redirects': True,
            "data": request.body,
            "json": request.json
        }

        try:
            async with httpx.AsyncClient(**httpx_client_session) as session:
                response = await session.request(request.method, request.url, **session_kwargs)
                content = response.read()

            return self.di.get("response")(
                str(response.url),
                status=response.status_code,
                headers=response.headers,
                body=content,
                cookies=response.cookies,
                _response=response)

        except httpx.TimeoutException as e:
            self.logger.warning(f"Request to {request.url} timed out: {str(e)}")
            raise self.di.get("exceptions").TimeoutError(f"Request to {request.url} timed out")

        except httpx.RequestError as e:
            self.logger.warning(f"Request to {request.url} failed: {str(e)}")
            raise self.di.get("exceptions").ConnectionError(f"Request to {request.url} failed: {str(e)}")

        except Exception as e:
            self.logger.error(f"Unexpected error when downloading {request.url}: {str(e)}")
            raise self.di.get("exceptions").DownloadError(f"Unexpected error: {str(e)}")

    async def close(self):
        await asyncio.sleep(0.1)
