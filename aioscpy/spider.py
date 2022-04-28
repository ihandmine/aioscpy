from aioscpy import signals
from aioscpy import call_grace_instance


class Spider(object):
    name = None
    custom_settings = None

    def __init__(self, name=None, **kwargs):
        if name is not None:
            self.name = name
        self.__dict__.update(kwargs)
        if not hasattr(self, 'start_urls'):
            self.start_urls = []

    def log(self, message, level='DEBUG', **kw):
        self.logger.log(level, message, **kw)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def _set_crawler(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        crawler.signals.connect(self.close, signals.spider_closed)
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)

    async def start_requests(self):
        for url in self.start_urls:
            yield self.di.get('request')(url, dont_filter=True)

    async def _parse(self, response, **kwargs):
        return self.parse(response)

    async def parse(self, response):
        raise NotImplementedError(f'{self.__class__.__name__}.parse callback is not defined')

    @classmethod
    def update_settings(cls, settings):
        settings.setdict(cls.custom_settings or {}, priority='spider')

    @staticmethod
    def close(spider, reason):
        closed = getattr(spider, 'closed', None)
        if callable(closed):
            return closed(reason)

    @classmethod
    def start(cls):
        from aioscpy.crawler import CrawlerProcess
        process = call_grace_instance(CrawlerProcess)
        process.crawl(cls)
        process.start()

    def spider_idle(self):
        if self.settings.get("SPIDER_IDLE", True):
            raise self.di.get('exceptions').DontCloseSpider

    def __str__(self):
        return "<%s %r at 0x%0x>" % (type(self).__name__, self.name, id(self))

    __repr__ = __str__


Spider = call_grace_instance('spider', only_instance=True)
