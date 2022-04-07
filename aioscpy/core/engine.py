import asyncio
import logging
from time import time


from aioscpy.exceptions import DontCloseSpider
from aioscpy.http import Response
from aioscpy.core.scraper import Scraper
from aioscpy.http.request import Request
from aioscpy.utils.misc import load_object
from aioscpy.utils.tools import call_helper


logger = logging.getLogger(__name__)


class Slot:

    def __init__(self, start_requests, close_if_idle, scheduler):
        self.closing = None
        self.inprogress = set()  # requests in progress

        self.start_requests = start_requests
        self.doing_start_requests = False
        self.close_if_idle = close_if_idle
        self.scheduler = scheduler
        self.heartbeat = None

    def add_request(self, request):
        self.inprogress.add(request)

    def remove_request(self, request):
        self.inprogress.remove(request)
        self._maybe_fire_closing()

    async def close(self):
        self.closing = asyncio.Future()
        self._maybe_fire_closing()
        await self.closing

    def _maybe_fire_closing(self):
        if self.closing and not self.inprogress:
            if self.heartbeat:
                self.heartbeat.cancel()
            self.closing.set_result(None)


class ExecutionEngine(object):

    def __init__(self, crawler, spider_closed_callback):
        self.lock = True
        self.start_time = time()
        self.crawler = crawler
        self.settings = crawler.settings
        self.slot = None
        self.spider = None
        self.scheduler = None
        self.running = False
        self.paused = False
        self.scheduler_cls = load_object(self.settings['SCHEDULER'])
        downloader_cls = load_object(self.settings['DOWNLOADER'])
        self.downloader = downloader_cls(crawler)
        self.scraper = Scraper(crawler)
        self._spider_closed_callback = spider_closed_callback

    async def start(self, spider, start_requests=None):
        self.start_time = time()
        self.running = True
        self._closewait = asyncio.Future()
        await self.open_spider(spider, start_requests, close_if_idle=True)
        await self._closewait

    async def stop(self):
        self.running = False
        await self._close_all_spiders()
        self._closewait.set_result(None)

    async def close(self):

        if self.running:
            # Will also close spiders and downloader
            await self.stop()
        elif self.open_spiders:
            # Will also close downloader
            await self._close_all_spiders()
        else:
            self.downloader.close()

    def pause(self):
        """Pause the execution engine"""
        self.paused = True

    def unpause(self):
        """Resume the execution engine"""
        self.paused = False

    async def _next_request(self, spider):
        slot = self.slot
        if not slot:
            return

        if self.paused:
            return

        while self.lock and not self._needs_backout(spider) and self.lock:
            self.lock = False
            try:
                request = await call_helper(slot.scheduler.next_request)
                if not request:
                    break
                slot.add_request(request)
                await self.downloader.fetch(request, spider, self._handle_downloader_output)
            finally:
                self.lock = True

        if slot.start_requests and not self._needs_backout(spider) and not slot.doing_start_requests:
            slot.doing_start_requests = True
            try:
                request = await slot.start_requests.__anext__()
            except StopAsyncIteration:
                slot.start_requests = None
            except Exception:
                slot.start_requests = None
                logger.error('Error while obtaining start requests',
                             exc_info=True, extra={'spider': spider})
            else:
                await self.crawl(request, spider)
            finally:
                slot.doing_start_requests = False

        if self.running and await self.spider_is_idle(spider) and slot.close_if_idle:
            await self._spider_idle(spider)

    def _needs_backout(self, spider):
        return (
                not self.running
                or self.slot.closing
                or self.downloader.needs_backout()
                or self.scraper.slot.needs_backout()
        )

    async def _handle_downloader_output(self, result, request, spider):
        try:
            if isinstance(result, Request):
                await self.crawl(result, spider)
                return
        finally:
            self.slot.remove_request(request)
            asyncio.create_task(self._next_request(self.spider))
        await self.scraper.enqueue_scrape(result, request, spider)

    async def spider_is_idle(self, spider):
        if not self.scraper.slot.is_idle():
            # scraper is not idle
            return False

        if self.downloader.active:
            # downloader has pending requests
            return False

        if self.slot.start_requests is not None:
            # not all start requests are handled
            return False

        if self.slot.inprogress:
            # not all start requests are handled
            return False

        if await call_helper(self.slot.scheduler.has_pending_requests):
            # scheduler has pending requests
            return False

        return True

    @property
    def open_spiders(self):
        return (self.spider,) if self.spider else set()

    def has_capacity(self):
        """Does the engine have capacity to handle more spiders"""
        return not bool(self.slot)

    async def crawl(self, request, spider):  # 将网址 请求加入队列
        await call_helper(self.slot.scheduler.enqueue_request, request)

    async def open_spider(self, spider, start_requests=None, close_if_idle=True):
        scheduler = await call_helper(self.scheduler_cls.from_crawler, self.crawler)
        start_requests = await call_helper(self.scraper.spidermw.process_start_requests, start_requests, spider)
        self.slot = Slot(start_requests, close_if_idle, scheduler)
        self.spider = spider
        await call_helper(scheduler.open, spider)
        await call_helper(self.scraper.open_spider, spider)
        await call_helper(self.crawler.stats.open_spider, spider)
        await self._next_request(spider)
        self.slot.heartbeat = asyncio.create_task(self.heart_beat(5, spider, self.slot))

    async def _close_all_spiders(self):
        dfds = [self.close_spider(s, reason='shutdown') for s in self.open_spiders]
        await asyncio.gather(*dfds)

    async def close_spider(self, spider, reason='cancelled'):
        """Close (cancel) spider and clear all its outstanding requests"""

        slot = self.slot
        if slot.closing:
            return slot.closing
        logger.info("Closing spider (%(reason)s)",
                    {'reason': reason},
                    extra={'spider': spider})

        await slot.close()

        async def close_handler(callback, *args, errmsg='', **kwargs):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except (Exception, BaseException) as e:
                logger.error(
                    errmsg,
                    exc_info=e,
                    extra={'spider': spider}
                )

        await close_handler(self.downloader.close, errmsg='Downloader close failure')

        await close_handler(self.scraper.close_spider, spider, errmsg='Scraper close failure')

        await close_handler(self.slot.scheduler.close, reason, errmsg='Scheduler close failure')

        await close_handler(self.crawler.stats.close_spider, spider, reason=reason, errmsg='Stats close failure')

        logger.info("Spider closed (%(reason)s)", {'reason': reason}, extra={'spider': spider})

        await close_handler(setattr, self, 'slot', None, errmsg='Error while unassigning slot')

        await close_handler(setattr, self, 'spider', None, errmsg='Error while unassigning spider')

        await self._spider_closed_callback()

    async def _spider_idle(self, spider):
        if await self.spider_is_idle(spider):
            await self.close_spider(spider, reason='finished')

    async def heart_beat(self, delay, spider, slot):
        while not slot.closing:
            await asyncio.sleep(delay)
            asyncio.create_task(self._next_request(spider))
