from aioscpy.spider import Spider


class BaiduSpider(Spider):
    name = 'baidu'
    permanent = False
    custom_settings = {}
    start_urls = ['http://www.baidu.com/']

    def parse(self, response):
        item = {
            'hot': '\n'.join(response.xpath('//span[@class="title-content-title"]/text()').extract()),
        }
        self.logger.info(item)
        yield item
