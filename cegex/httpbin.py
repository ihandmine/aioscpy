from aioscpy.spider import Spider


class HttpBinSpider(Spider):
    name = 'httpbin'
    custom_settings = {}
    start_urls = ['http://httpbin.org/get'] * 5

    async def parse(self, response):
        item = await response.json
        yield item

    async def process_item(self, item):
        print(item)
