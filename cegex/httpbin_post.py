from aioscpy.spider import Spider
from aioscpy import call_grace_instance


class HttpBinPostSpider(Spider):
    name = 'httpbin_post'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10
    }

    start_urls = ['http://httpbin.org/post' for _ in range(20)]

    async def start_requests(self):
        for url in self.start_urls:
            yield call_grace_instance(
                self.di.get('form_request'), 
                url, 
                method='POST',
                formdata={"b": '11'}
            )

    async def parse(self, response):
        item = await response.json
        yield item

    async def process_item(self, item):
        self.logger.info(item)


if __name__ == '__main__':
    q = HttpBinPostSpider()
    q.start()
