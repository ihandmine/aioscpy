import pprint
import asyncio
import signal

from aioscpy.settings import overridden_settings
from aioscpy.settings import Settings
from aioscpy.signalmanager import SignalManager
from aioscpy.utils.ossignal import install_shutdown_handlers, signal_names
from aioscpy.inject import DependencyInjection
from aioscpy import call_grace_instance


class Crawler(object):

    def __init__(self, spidercls, *args, settings=None, **kwargs):

        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)

        self.spidercls = spidercls
        self.settings = settings.copy()
        self.spidercls.update_settings(self.settings)
        self.signals = SignalManager(self)

        if d := dict(overridden_settings(self.settings)):
            self.logger.info("Overridden settings {spider}:\n{settings}",
                        **{'settings': pprint.pformat(d), "spider": spidercls.__name__})

        self.settings.freeze()
        self.crawling = False
        self.spider = self._create_spider(*args, **kwargs)
        self.engine = None
        self.stats = call_grace_instance('stats', self)
        self.DI = self._create_dependency()
        self.extensions = self.load('extension')
        self._close_wait = None

    async def crawl(self):
        if self.crawling:
            raise RuntimeError("Crawling already taking place")
        self.crawling = True

        try:
            await self.DI.inject_runner()
            self.engine = self._create_engine()
            start_requests = await self.di.get("tools").async_generator_wrapper(self.spider.start_requests())
            await self.engine.start(self.spider, start_requests)
            await self.di.get("tools").task_await(self, "_close_wait")
        except Exception as e:
            self.logger.exception(e)
            self.crawling = False
            if self.engine is not None:
                await self.engine.close()
            raise e

    def load(self, key):
        return self.DI.load(key)

    def _create_spider(self, *args, **kwargs):
        return self.spidercls.from_crawler(self, *args, **kwargs)

    def _create_engine(self):
        return call_grace_instance('engine', self, self.stop)

    def _create_dependency(self):
        return DependencyInjection(self.settings, self)

    async def stop(self):
        if self.crawling:
            self.crawling = False
            await self.engine.stop()
        self._close_wait = True


class CrawlerProcess(object):
    crawlers = property(
        lambda self: self._crawlers,
        doc="Set of :class:`crawlers <aioscpy.crawler.Crawler>`"
    )

    def __init__(self, settings=None, install_root_handler=True):
        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)
        self.settings = settings
        self._crawlers = set()
        self._active = set()
        self.bootstrap_failed = False
        self._group = []
        install_shutdown_handlers(self._signal_shutdown)
        self.di.get("log").std_log_aioscpy_info(settings)

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
        if isinstance(crawler_or_spidercls, str):
            crawler_or_spidercls = self.load_spider(spider_key=crawler_or_spidercls)
        settings = kwargs.pop('settings', self.settings)
        return call_grace_instance("crawler", crawler_or_spidercls, *args, settings=settings, **kwargs)

    def active_crawler(self, crawler):
        task = asyncio.create_task(crawler.crawl())
        self._active.add(task)

        def _done(result):
            self.crawlers.discard(crawler)
            self._active.discard(task)
            self.bootstrap_failed |= not getattr(crawler, 'spider', None)
            return result

        task.add_done_callback(_done)

    def load_spider(self, path=None, spider_key: str = None):
        if path is None:
            path = ''.join(['./', self.settings.get("NEWSPIDER_MODULE", "spiders")])
        spiders_cls = DependencyInjection.load_all_spider(path)

        if spider_key is not None:
            if spiders_cls.get(spider_key):
                return spiders_cls[spider_key]
            else:
                raise KeyError(f"Spider not found: {spider_key}")
        for name, spider_cls in spiders_cls.items():
            self.crawl(spider_cls)
            self.logger.debug("Loading spider({name}) from {path}", **{"name": name, "path": path})

    async def stop(self):
        return await asyncio.gather(*[c.stop() for c in list(self.crawlers)])

    async def run(self):
        for crawler in self.crawlers:
            self.active_crawler(crawler)
        while self._active:
            self._group.append(await asyncio.gather(*self._active, return_exceptions=True))

    async def _graceful_stop_reactor(self):
        await self.stop()

    async def _force_stop_reactor(self):
        for task in self._active:
            task.cancel()
        for group in self._group:
            group.cancel()
        current_task = asyncio.all_tasks()
        for ct in current_task:
            ct.cancel()
        await asyncio.sleep(1)
        asyncio.get_running_loop().stop()

    def _signal_shutdown(self, signum, _):
        install_shutdown_handlers(self._signal_kill)
        signame = signal_names[signum]
        self.logger.info("Received {signame}, shutting down gracefully. Send again to force ",
                    **{'signame': signame})
        asyncio.create_task(self._graceful_stop_reactor())

    def _signal_kill(self, signum, _):
        install_shutdown_handlers(signal.SIG_IGN)
        signame = signal_names[signum]
        self.logger.info('Received {signame} twice, forcing unclean shutdown',
                    **{'signame': signame})
        asyncio.create_task(self._force_stop_reactor())

    def start(self):
        self.di.get("tools").install_event_loop_tips()
        try:
            asyncio.run(self.run())
        except asyncio.CancelledError:
            pass
