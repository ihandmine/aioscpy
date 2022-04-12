from aioscpy.spider import Spider


class HttpBinSpider(Spider):
    name = 'httpbin'
    permanent = False
    custom_settings = {}
    start_urls = ['http://httpbin.org/get'] * 5

    async def parse(self, response):
        # item = {
        #     'hot': '\n'.join(response.xpath('//span[@class="title-content-title"]/text()').extract()),
        # }
        item = response.json()
        yield item

    async def process_item(self, item):
        print(item)

    def spider_idle(self):
        """跑完关闭爬虫"""
        pass
