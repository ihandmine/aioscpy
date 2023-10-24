import asyncio

from aioscpy.spider import Spider
from anti_header import Header
from pprint import pprint, pformat


class Ja3Spider(Spider):
    name = 'ja3'
    custom_settings = {
        "SPIDER_IDLE": False,
        'TLS_CIPHERS': True,
        "DOWNLOAD_HANDLER": "aioscpy.core.downloader.handlers.requests.AiohttpDownloadHandler"
    }
    start_urls = [f'https://tls.browserleaks.com/json?a{i}' for i in range(10)]

    async def process_request(self, request):
        request.headers = Header(url=request.url, platform='windows', connection=True).random
        return request

    async def process_response(self, request, response):
        return response

    async def process_exception(self, request, exc):
        raise exc

    async def parse(self, response):
        _ja = await response.json
        item = {
            'ja3': _ja['ja3_hash'],
        }
        yield item

    async def process_item(self, item):
        pass
        # self.logger.info("{item}", **{'item': pformat(item)})


if __name__ == '__main__':
    ja3 = Ja3Spider()
    ja3.start()
