import asyncio

from aioscpy.spider import Spider
from anti_header import Header
from pprint import pprint, pformat


class BaiduSpider(Spider):
    name = 'baidu'
    custom_settings = {
        "SPIDER_IDLE": False,
        'TLS_CIPHERS': True,
        "DOWNLOAD_HANDLER": "aioscpy.core.downloader.handlers.requests.RequestsDownloadHandler"
    }
    start_urls = [f'https://www.baidu.com/?a{i}' for i in range(10)]

    async def process_request(self, request):
        request.headers = Header(url=request.url, platform='windows', connection=True).random
        return request

    async def process_response(self, request, response):
        return response

    async def process_exception(self, request, exc):
        raise exc

    async def parse(self, response):
        item = {
            'hot': '\n'.join(response.xpath('//span[@class="title-content-title"]/text()').extract()),
        }
        yield item

    async def process_item(self, item):
        pass
        # self.logger.info("{item}", **{'item': pformat(item)})


if __name__ == '__main__':
    baidu = BaiduSpider()
    baidu.start()
