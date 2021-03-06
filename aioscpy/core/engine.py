import asyncio

from time import time

from aioscpy import signals, call_grace_instance


class Slot(object):

    def __init__(self, start_requests, close_if_idle, scheduler, crawler):
        self.closing = None
        self.inprogress = set()  # requests in progress

        self.start_requests = start_requests
        self.doing_start_requests = False
        self.close_if_idle = close_if_idle
        self.scheduler = scheduler
        self.crawler = crawler
        self.heartbeat = None
        self.closing_wait = None
        self.scrape = set()
        self.closing_lock = None

    def add_request(self, request):
        self.inprogress.add(request)

    def scrape_buffer_space(self, result, emit=None):
        if isinstance(result, dict):
            result = str(result)
        if emit is None:
            self.scrape.add(result)
        else:
            self.scrape.remove(result)

    def remove_request(self, request):
        self.inprogress.remove(request)
        self._maybe_fire_closing()

    async def close(self):
        self._maybe_fire_closing()
        await self.crawler.di.get("tools").task_await(self, "closing_wait")

    def _maybe_fire_closing(self):
        if not self.inprogress:
            if self.heartbeat:
                self.heartbeat.cancel()
            self.closing_wait = True


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
        self.signals = crawler.signals
        self.logformatter = crawler.load("log_formatter")
        self.scheduler = crawler.load("scheduler")
        self.downloader = crawler.load("downloader")
        self.scraper = call_grace_instance("scraper", crawler, self)
        self.call_helper = self.di.get("tools").call_helper
        self._spider_closed_callback = spider_closed_callback

    async def start(self, spider, start_requests=None):
        self.start_time = time()
        await self.signals.send_catch_log_coroutine(signal=signals.engine_started)
        self.running = True
        await self.open_spider(spider, start_requests, close_if_idle=True)

    async def stop(self):
        self.running = False
        await self._close_all_spiders()
        await self.signals.send_catch_log_coroutine(signal=signals.engine_stopped)

    async def close(self):

        if self.running:
            await self.stop()
        elif self.open_spiders:
            await self._close_all_spiders()
        else:
            self.downloader.close()

    async def _next_request(self, spider) -> None:
        slot = self.slot
        if not slot:
            return

        while not self._needs_backout(spider):
            if not await self.call_helper(slot.scheduler.has_pending_requests):
                break
            request = await self.call_helper(slot.scheduler.next_request)
            slot.add_request(request)
            await self.downloader.fetch(request, spider, self._handle_downloader_output)

        if slot.start_requests and not self._needs_backout(spider) and not slot.doing_start_requests:
            slot.doing_start_requests = True
            try:
                request = await slot.start_requests.__anext__()
            except StopAsyncIteration:
                slot.start_requests = None
            except Exception:
                slot.start_requests = None
                self.logger.error('Error while obtaining start requests',
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
        finally:
            self.slot.remove_request(request)
            asyncio.create_task(self._next_request(self.spider))
        await self.scraper.enqueue_scrape(result, request, spider)

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

    async def crawl(self, request, spider):  # ????????? ??????????????????
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
        await self.call_helper(self.scraper.open_spider, spider)
        await self.call_helper(self.crawler.stats.open_spider, spider)
        await self.signals.send_catch_log_coroutine(signals.spider_opened, spider=spider)
        await self._next_request(spider)
        if self.slot is None:
            self.logger.warning("Spider ({name}) to running not found task! please check task is be generated.",
                                **{"name": spider.name})
            return
        self.slot.heartbeat = asyncio.create_task(self.heart_beat(0.2, spider, self.slot))

    async def _close_all_spiders(self):
        dfds = [self.close_spider(s, reason='shutdown') for s in self.open_spiders]
        await asyncio.gather(*dfds)

    async def close_spider(self, spider, reason='cancelled'):
        """Close (cancel) spider and clear all its outstanding requests"""
        slot = self.slot
        if slot and slot.closing or slot.closing_lock:
            return slot.closing

        slot.closing_lock = True

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

        self.logger.info("Spider({name}) closed ({reason})", **{'reason': reason, "name": spider.name}, extra={'spider': spider})

        # await close_handler(setattr, self, 'slot', None, errmsg='Error while unassigning slot')

        # await close_handler(setattr, self, 'spider', None, errmsg='Error while unassigning spider')

        await self._spider_closed_callback()

    async def _spider_idle(self, spider):
        res = await self.signals.send_catch_log(signals.spider_idle, spider=spider, dont_log=self.di.get("exceptions").DontCloseSpider)
        if any(isinstance(x, self.di.get("exceptions").DontCloseSpider) for _, x in res):
            return
        if await self.spider_is_idle(spider):
            await self.close_spider(spider, reason='finished')

    async def heart_beat(self, delay, spider, slot):
        while not slot.closing:
            await asyncio.sleep(delay)
            asyncio.create_task(self._next_request(spider))
