import logging
import pprint
import warnings
import asyncio
import sys

from aioscpy import Spider
from aioscpy.settings import overridden_settings
from scrapy.exceptions import ScrapyDeprecationWarning
from aioscpy.utils.tools import async_generator_wrapper
from aioscpy.core.engine import ExecutionEngine
from aioscpy.settings import Settings

logger = logging.getLogger(__name__)


class Crawler:

    def __init__(self, spidercls, *args, settings=None, **kwargs):
        if isinstance(spidercls, Spider):
            raise ValueError(
                'The spidercls argument must be a class, not an object')

        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)

        self.spidercls = spidercls
        self.settings = settings.copy()
        self.spidercls.update_settings(self.settings)

        d = dict(overridden_settings(self.settings))
        logger.info("Overridden settings:\n%(settings)s",
                    {'settings': pprint.pformat(d)})

        self.settings.freeze()
        self.crawling = False
        self.spider = self._create_spider(*args, **kwargs)
        self.engine = None

    async def crawl(self):
        if self.crawling:
            raise RuntimeError("Crawling already taking place")
        self.crawling = True

        try:
            self.engine = self._create_engine()
            start_requests = await async_generator_wrapper(self.spider.start_requests())
            await self.engine.start(self.spider, start_requests)
        except Exception as e:
            logger.exception(e)
            self.crawling = False
            if self.engine is not None:
                await self.engine.close()
            raise e

    def _create_spider(self, *args, **kwargs):
        return self.spidercls.from_crawler(self, *args, **kwargs)

    def _create_engine(self):
        return ExecutionEngine(self, self.stop)

    async def stop(self):
        """Starts a graceful stop of the crawler and returns a deferred that is
        fired when the crawler is stopped."""
        if self.crawling:
            self.crawling = False
            await self.engine.stop()


class CrawlerRunner:

    crawlers = property(
        lambda self: self._crawlers,
        doc="Set of :class:`crawlers <scrapy.crawler.Crawler>` started by "
            ":meth:`crawl` and managed by this class."
    )

    def __init__(self, settings=None):
        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)
        self.settings = settings
        self.spider_loader = self._get_spider_loader(settings)
        self._crawlers = set()
        self._active = set()
        self.bootstrap_failed = False

    @property
    def spiders(self):
        warnings.warn("CrawlerRunner.spiders attribute is renamed to "
                      "CrawlerRunner.spider_loader.",
                      category=ScrapyDeprecationWarning, stacklevel=2)
        return self.spider_loader

    def crawl(self, crawler_or_spidercls, *args, **kwargs):
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                'The crawler_or_spidercls argument cannot be a spider object, '
                'it must be a spider class (or a Crawler object)')
        crawler = self.create_crawler(crawler_or_spidercls, *args, **kwargs)
        self.crawlers.add(crawler)
        return crawler

    def crawl_soon(self, crawler_or_spidercls, *args, **kwargs):
        crawler = self.crawl(crawler_or_spidercls, *args, **kwargs)
        self.active_crawler(crawler)

    def active_crawler(self, crawler):
        task = asyncio.create_task(crawler.crawl())
        self._active.add(task)

        def _done(result):
            self.crawlers.discard(crawler)
            self._active.discard(task)
            self.bootstrap_failed |= not getattr(crawler, 'spider', None)
            return result

        task.add_done_callback(_done)

    def create_crawler(self, crawler_or_spidercls, *args, **kwargs):
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                'The crawler_or_spidercls argument cannot be a spider object, '
                'it must be a spider class (or a Crawler object)')
        if isinstance(crawler_or_spidercls, Crawler):
            return crawler_or_spidercls
        return self._create_crawler(crawler_or_spidercls, *args, **kwargs)

    def _create_crawler(self, spidercls, *args, **kwargs):
        if isinstance(spidercls, str):
            spidercls = self.spider_loader.load(spidercls)
        settings = kwargs.pop('settings', self.settings)
        return Crawler(spidercls, *args, settings=settings, **kwargs)

    async def stop(self):
        return await asyncio.gather(*[c.stop() for c in list(self.crawlers)])


class CrawlerProcess(CrawlerRunner):

    def __init__(self, settings=None, install_root_handler=True):
        super().__init__(settings)

    def _signal_shutdown(self, signum, _):
        asyncio.create_task(self._graceful_stop_reactor())

    def _signal_kill(self, signum, _):
        asyncio.create_task(self._stop_reactor())

    async def run(self):
        for crawler in self.crawlers:
            self.active_crawler(crawler)
        while self._active:
            await asyncio.gather(*self._active)

    def start(self):
        if not sys.platform.startswith('win'):
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except ImportError:
                pass
        asyncio.run(self.run())

    async def _graceful_stop_reactor(self):
        await self.stop()

    async def _stop_reactor(self):
        asyncio.get_event_loop().stop()
