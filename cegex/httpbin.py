import asyncio

from aioscpy.spider import Spider


class HttpBinSpider(Spider):
    name = 'httpbin'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10
    }
    start_urls = [f'http://httpbin.org/get?a{i}' for i in range(20)]

    async def parse(self, response):
        item = await response.json
        await asyncio.sleep(2)
        yield item

    async def process_item(self, item):
        pass
        # self.logger.info(item)


if __name__ == '__main__':
    q = HttpBinSpider()
    q.start()
