import asyncio

from aioscpy.spider import Spider
from aioscpy import call_grace_instance


class QuotesSpider(Spider):
    name = 'quotes'
    custom_settings = {
        "SPIDER_IDLE": False
    }
    start_urls = [
        'https://quotes.toscrape.com/',
    ]

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


if __name__ == '__main__':
    q = QuotesSpider()
    q.start()
