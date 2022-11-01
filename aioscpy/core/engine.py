import asyncio
import traceback
import gc

from time import time

from aioscpy import signals, call_grace_instance


class Slot(object):

    def __init__(self, start_requests, close_if_idle, scheduler, crawler):
        self.closing = None
        self.inprogress = set()

        self.start_requests = start_requests
        self.close_if_idle = close_if_idle
        self.scheduler = scheduler
        self.crawler = crawler
        self.heartbeat = None
        self.closing_wait = None

    def add_request(self, request):
        self.inprogress.add(request)

    def remove_request(self, request):
        self.inprogress.discard(request)

    async def close(self):
        self.closing = True


class ExecutionEngine(object):

    def __init__(self, crawler, spider_closed_callback):
        self.start_time = time()
        self.crawler = crawler
        self.settings = crawler.settings
        self.slot = None
        self.spider = None
        self.scheduler = None
        self.running = False
        self._heart_beat = None
        self._task_beat = None
        self.signals = crawler.signals
        self.logformatter = crawler.load("log_formatter")
        self.scheduler = crawler.load("scheduler")
        self.downloader = call_grace_instance('downloader', crawler)
        self.scraper = call_grace_instance("scraper", crawler)
        self.call_helper = self.di.get("tools").call_helper
        self.lock = asyncio.Lock()
        self._spider_closed_callback = spider_closed_callback

    async def start(self, spider, start_requests=None):
        self.start_time = time()
        await self.signals.send_catch_log_coroutine(signal=signals.engine_started)
        self.running = True
        await self.open_spider(spider, start_requests, close_if_idle=True)

    async def stop(self):
        self.running = False
        # await self._close_all_spiders()
        await self.signals.send_catch_log_coroutine(signal=signals.engine_stopped)

    async def start_spider_request(self, spider):
        if self.slot.start_requests and not self._needs_backout():
            try:
                request = await self.slot.start_requests.__anext__()
            except StopAsyncIteration:
                self.slot.start_requests = None
            except Exception:
                self.slot.start_requests = None
                self.logger.error('Error while obtaining start requests',
                                    exc_info=True, extra={'spider': spider})
            else:
                await self.crawl(request, spider)

    def _needs_backout(self) -> bool:
        return (
            not self.running
            or self.slot.closing
            or self.downloader.needs_backout()
            or self.scraper.slot.needs_backout()
        )

    async def _handle_downloader_output(self, result, request, spider):
        try:
            if isinstance(result, self.di.get('request')):
                await self.crawl(result, spider)
                return
            if isinstance(result, self.di.get('response')):
                result.request = request
                logkws = self.logformatter.crawled(request, result, spider)
                level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
                if logkws is not None:
                    self.logger.log(level, message, **kwargs)
                await self.signals.send_catch_log(signals.response_received,
                                                  response=result, request=request, spider=spider)
        except Exception as e:
            self.logger.error(f"enqueue_scrape: {traceback.format_exc()}")
        finally:
            self.slot.remove_request(request)
        await self.scraper.enqueue_scrape(result, request)

    async def spider_is_idle(self, spider):
        if self.scraper.slot.is_idle():
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

        if await self.call_helper(self.slot.scheduler.has_pending_requests):
            # scheduler has pending requests
            return False

        return True

    @property
    def open_spiders(self):
        return (self.spider,) if self.spider else set()

    def has_capacity(self):
        return not bool(self.slot)

    async def crawl(self, request, spider):  # 将网址 请求加入队列
        if spider not in self.open_spiders:
            raise RuntimeError("Spider %r not opened when crawling: %s" % (spider.name, request))

        await self.signals.send_catch_log(signals.request_scheduled, request=request, spider=spider)
        if not await self.call_helper(self.slot.scheduler.enqueue_request, request):
            await self.signals.send_catch_log(signals.request_dropped, request=request, spider=spider)

    async def open_spider(self, spider, start_requests=None, close_if_idle=True):
        if not self.has_capacity():
            raise RuntimeError("No free spider slot when opening %r" % spider.name)
        self.logger.info("Spider opened({name})", **{"name": spider.name}, extra={'spider': spider})

        self.slot = Slot(start_requests, close_if_idle, self.scheduler, self.crawler)
        self.spider = spider
        await self.call_helper(self.scheduler.open, start_requests)
        await self.call_helper(self.downloader.open, spider, self)
        await self.call_helper(self.scraper.open_spider, spider)
        await self.call_helper(self.crawler.stats.open_spider, spider)
        await self.signals.send_catch_log_coroutine(signals.spider_opened, spider=spider)
        await self.start_spider_request(spider)
        if self.slot is None:
            self.logger.warning("Spider ({name}) to running not found task! please check task is be generated.",
                                **{"name": spider.name})
            return
        self._heart_beat = asyncio.create_task(self.heart_beat(5, spider, self.slot))
        self._task_beat = asyncio.create_task(self.task_beat())

    async def _close_all_spiders(self):
        dfds = [self.close_spider(s, reason='shutdown') for s in self.open_spiders]
        await asyncio.gather(*dfds)

    async def close_spider(self, spider, reason='cancelled'):
        """Close (cancel) spider and clear all its outstanding requests"""
        slot = self.slot
        if slot.closing:
            return slot.closing

        self.logger.info("Closing spider({name}) ({reason})",
                         **{'reason': reason, 'name': spider.name},
                         extra={'spider': spider})

        await slot.close()

        async def close_handler(callback, *args, errmsg='', **kwargs):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except (Exception, BaseException) as e:
                self.logger.error(
                    errmsg + ': {exc_info}',
                    exc_info=e,
                )

        await close_handler(self.downloader.close, errmsg='Downloader close failure')

        await close_handler(self.scraper.close_spider, spider, errmsg='Scraper close failure')

        await close_handler(slot.scheduler.close, slot, errmsg='Scheduler close failure')

        await close_handler(self.signals.send_catch_log_coroutine, signal=signals.spider_closed, spider=spider,
                            reason=reason, errmsg='Error while sending spider_close signal')

        await close_handler(self.crawler.stats.close_spider, spider, reason=reason, errmsg='Stats close failure')

        self.logger.info("Spider({name}) closed ({reason})", **
                         {'reason': reason, "name": spider.name}, extra={'spider': spider})

        await self._spider_closed_callback()
        if self._heart_beat:
            self._heart_beat.cancel()
        if self._task_beat:
            self._task_beat.cancel()

    async def _spider_idle(self, spider):
        res = await self.signals.send_catch_log(signals.spider_idle, spider=spider, dont_log=self.di.get("exceptions").DontCloseSpider)
        if any(isinstance(x, self.di.get("exceptions").DontCloseSpider) for _, x in res):
            return
        if await self.spider_is_idle(spider):
            await self.close_spider(spider, reason='finished')

    async def heart_beat(self, delay, spider, slot):
        while True:
            await asyncio.sleep(delay)
            if self.running and await self.spider_is_idle(spider) and slot.close_if_idle:
                await self._spider_idle(spider)
            co = '<logstats: %(spname)s> transferring: %(transfer)s, queue: %(queue)s, active: %(active)s, ingress: %(ingress)s, scraper-active: %(sactive)s, scraper-queue: %(squeue)s, scraper-size: %(size)s' % {
                'spname': spider.name,
                'transfer': len(self.downloader.slot.transferring),
                'queue': len(self.downloader.slot.queue),
                'active': len(self.downloader.active),
                'ingress': len(self.slot.inprogress),
                'sactive': len(self.scraper.slot.active),
                'squeue': len(self.scraper.slot.queue),
                'size': self.scraper.slot.active_size,
            }
            self.logger.debug(co)
            try:
                gc.collect()
            except:
                self.logger.warning(f'gc collect faild!')

    async def task_beat(self):
        local_lock = True
        while True:
            while local_lock and not self._needs_backout():
                local_lock = False
                for request in await self.slot.scheduler.async_next_request():
                    self.slot.add_request(request)
                    await self.downloader.fetch(request)
                local_lock = True
            await asyncio.sleep(1)
