import logging
import pprint
import warnings
import asyncio
import sys

from aioscpy.spider import Spider
from aioscpy.settings import overridden_settings
from aioscpy.exceptions import ScrapyDeprecationWarning
from aioscpy.utils.tools import async_generator_wrapper
from aioscpy.core.engine import ExecutionEngine
from aioscpy.settings import Settings

logger = logging.getLogger(__name__)


class Crawler:

    def __init__(self, spidercls, *args, settings=None, **kwargs):

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
        if self.crawling:
            self.crawling = False
            await self.engine.stop()


class CrawlerProcess:

    def __init__(self, settings=None, install_root_handler=True):
        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)
        self.settings = settings
        self._crawlers = set()
        self._active = set()
        self.bootstrap_failed = False

    def crawl(self, crawler_or_spidercls, *args, **kwargs):
        crawler = self.create_crawler(crawler_or_spidercls, *args, **kwargs)
        self.crawlers.add(crawler)
        return crawler

    def crawl_soon(self, crawler_or_spidercls, *args, **kwargs):
        crawler = self.crawl(crawler_or_spidercls, *args, **kwargs)
        self.active_crawler(crawler)

    def create_crawler(self, crawler_or_spidercls, *args, **kwargs):
        if isinstance(crawler_or_spidercls, Crawler):
            return crawler_or_spidercls
        settings = kwargs.pop('settings', self.settings)
        return Crawler(crawler_or_spidercls, *args, settings=settings, **kwargs)

    def active_crawler(self, crawler):
        task = asyncio.create_task(crawler.crawl())
        self._active.add(task)

        def _done(result):
            self.crawlers.discard(crawler)
            self._active.discard(task)
            self.bootstrap_failed |= not getattr(crawler, 'spider', None)
            return result

        task.add_done_callback(_done)

    async def stop(self):
        return await asyncio.gather(*[c.stop() for c in list(self.crawlers)])

    async def run(self):
        for crawler in self.crawlers:
            self.active_crawler(crawler)
        while self._active:
            await asyncio.gather(*self._active)

    async def _graceful_stop_reactor(self):
        await self.stop()

    async def _stop_reactor(self):
        asyncio.get_event_loop().stop()

    def _signal_shutdown(self, signum, _):
        asyncio.create_task(self._graceful_stop_reactor())

    def _signal_kill(self, signum, _):
        asyncio.create_task(self._stop_reactor())

    def start(self):
        if not sys.platform.startswith('win'):
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except ImportError:
                pass
        asyncio.run(self.run())
