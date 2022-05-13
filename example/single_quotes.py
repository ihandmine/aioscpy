from aioscpy.spider import Spider
from anti_header import Header
from pprint import pprint, pformat


class SingleQuotesSpider(Spider):
    name = 'single_quotes'
    custom_settings = {
        "SPIDER_IDLE": False
    }
    start_urls = [
        'https://quotes.toscrape.com/',
    ]

    async def process_request(self, request):
        request.headers = Header(url=request.url, platform='windows', connection=True).random
        return request

    async def process_response(self, request, response):
        if response.status in [404, 503]:
            return request
        return response

    async def process_exception(self, request, exc):
        raise exc

    async def parse(self, response):

        for quote in response.css('div.quote'):
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            # first next_page method:
            yield response.follow(next_page, callback=self.parse)

            # second next_page method:
            # next_page_url = 'https://quotes.toscrape.com' + next_page
            # yield call_grace_instance(self.di.get("request"), next_page_url, callback=self.parse)

    async def process_item(self, item):
        pass
        # self.logger.info("{item}", **{'item': pformat(item)})


if __name__ == '__main__':
    q = SingleQuotesSpider()
    q.start()
