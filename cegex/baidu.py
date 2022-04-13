from aioscpy.spider import Spider
from anti_header import Header


class BaiduSpider(Spider):
    name = 'baidu'
    custom_settings = {}
    start_urls = ['http://www.baidu.com/'] * 5

    async def process_request(self, request):
        request.headers = Header(url=request.url, platform='windows', connection=True).random
        return request

    async def process_response(self, request, response):
        print(request.headers)
        print(response.headers)
        return response

    async def parse(self, response):
        item = {
            'hot': '\n'.join(response.xpath('//span[@class="title-content-title"]/text()').extract()),
        }
        yield item

    async def process_item(self, item):
        print(item)
