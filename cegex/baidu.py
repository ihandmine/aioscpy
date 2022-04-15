import asyncio

from aioscpy.spider import Spider
from anti_header import Header
from pprint import pprint, pformat


class BaiduSpider(Spider):
    name = 'baidu'
    custom_settings = {}
    start_urls = ['http://www.baidu.com/'] * 10

    async def process_request(self, request):
        request.headers = Header(url=request.url, platform='windows', connection=True).random
        return request

    async def process_response(self, request, response):
        return response

    async def parse(self, response):
        item = {
            'hot': '\n'.join(response.xpath('//span[@class="title-content-title"]/text()').extract()),
        }
        yield item

    async def process_item(self, item):
        pass
        # self.logger.info("%(item)s", {'item': pformat(item)})
