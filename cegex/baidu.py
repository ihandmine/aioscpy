from aioscpy.spider import Spider


class BaiduSpider(Spider):
    name = 'baidu'
    permanent = False
    custom_settings = {}
    start_urls = ['http://www.baidu.com/'] * 5

    async def parse(self, response):
        item = {
            'hot': '\n'.join(response.xpath('//span[@class="title-content-title"]/text()').extract()),
        }
        yield item

    async def process_item(self, item):
        print(item)

    def spider_idle(self):
        """跑完关闭爬虫"""
        pass
