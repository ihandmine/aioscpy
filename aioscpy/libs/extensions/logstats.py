import asyncio

from aioscpy.exceptions import NotConfigured
from aioscpy import signals


class LogStats:
    """Log basic scraping stats periodically"""

    def __init__(self, stats, interval=60.0):
        self.stats = stats
        self.interval = interval
        self.multiplier = 60.0 / self.interval
        self.task = None
        self._close_stats = 0

    @classmethod
    def from_crawler(cls, crawler):
        interval = crawler.settings.getfloat('LOGSTATS_INTERVAL')
        if not interval:
            raise NotConfigured
        o = cls(crawler.stats, interval)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        self.pagesprev = 0
        self.itemsprev = 0
        self.task = asyncio.create_task(self.log(spider))

    async def log(self, spider):
        await asyncio.sleep(self.interval)
        items = self.stats.get_value('item_scraped_count', 0)
        pages = self.stats.get_value('response_received_count', 0)
        irate = (items - self.itemsprev) * self.multiplier
        prate = (pages - self.pagesprev) * self.multiplier
        self.pagesprev, self.itemsprev = pages, items

        msg = ("<{spider_name}> Crawled {pages} pages (at {pagerate} pages/min), "
               "scraped {items} items (at {itemrate} items/min)")
        log_args = {'pages': pages, 'pagerate': prate, 'spider_name': spider.name,
                    'items': items, 'itemrate': irate}
        self.logger.info(msg, **log_args, extra={'spider': spider})
        self.task = asyncio.create_task(self.log(spider))

    def spider_closed(self, spider, reason):
        if self.task and not self.task.done():
            self.logger.warning(f'[{spider.name}] recevier logstats closed signed! reason: {reason}')
            self.task.cancel()
