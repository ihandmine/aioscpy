import asyncio

from time import time

from aioscpy import signals


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

    def add_request(self, request):
        self.inprogress.add(request)

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
        self.itemproc = crawler.load("item_processor")
        self.downloader = crawler.load("downloader")
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
            # Will also close spiders and downloader
            await self.stop()
        elif self.open_spiders:
            # Will also close downloader
            await self._close_all_spiders()
        else:
            self.downloader.close()

    async def _next_request(self, spider):
        slot = self.slot
        if not slot:
            return

        while self.lock and not self._needs_backout(spider) and self.lock:
            self.lock = False
            try:
                if not await self.call_helper(slot.scheduler.has_pending_requests):
                    break
                request = await self.call_helper(slot.scheduler.next_request)
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
                # or self.scraper.slot.needs_backout()
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
        response = await self.call_spider(result, request, spider)
        await self.call_helper(self.handle_spider_output, response, request, response, spider)

    async def call_spider(self, result, request, spider):
        if isinstance(result, self.di.get('response')):
            callback = request.callback or spider._parse
            result.request = request
            return await self.call_helper(callback, result, **result.request.cb_kwargs)
        else:
            if request.errback is None:
                raise result
            # 下载中间件或下载结果出现错误,回调request中的errback函数
            return await self.call_helper(request.errback, result)

    async def handle_spider_output(self, result, request, response, spider):
        if not result:
            return

        while True:
            try:
                res = await result.__anext__()
            except StopAsyncIteration:
                break
            except Exception as e:
                raise Exception(f"handle spider output error, {e}")
            else:
                await self._process_spidermw_output(res, request, response, spider)
                # item = await self.itemproc.process_item(res, spider)
                # process_item_method = getattr(spider, 'process_item', None)
                # if process_item_method:
                #     await self.call_helper(process_item_method, item)

    async def _process_spidermw_output(self, output, request, response, spider):
        # async with self.concurrent_items_semaphore:
        if isinstance(output, self.di.get('request')):
            await self.crawler.engine.crawl(request=output, spider=spider)
        elif isinstance(output, dict):
            item = await self.itemproc.process_item(output, spider)
            process_item_method = getattr(spider, 'process_item', None)
            if process_item_method:
                await self.call_helper(process_item_method, item)
            await self._itemproc_finished(output, item, response, spider)
        elif output is None:
            pass
        else:
            typename = type(output).__name__
            self.logger.error(
                'Spider must return request, item, or None, got %(typename)r in %(request)s',
                {'request': request, 'typename': typename},
                extra={'spider': spider},
            )

    async def _itemproc_finished(self, output, item, response, spider):
        if isinstance(output, (Exception, BaseException)):
            if isinstance(output, self.di.get('exceptions').DropItem):
                logkws = self.logformatter.dropped(item, output, response, spider)
                if logkws is not None:
                    level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
                    self.logger.log(level, message, **kwargs)
                return await self.signals.send_catch_log_coroutine(
                    signal=signals.item_dropped, item=item, response=response,
                    spider=spider, exception=output)
            else:
                logkws = self.logformatter.item_error(item, output, response, spider)
                level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
                self.logger.log(level, message, **kwargs)
                return await self.signals.send_catch_log_coroutine(
                    signal=signals.item_error, item=item, response=response,
                    spider=spider, failure=output)
        else:
            logkws = self.logformatter.scraped(output, response, spider)
            if logkws is not None:
                level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
                self.logger.log(level, message, **kwargs)
            return await self.signals.send_catch_log_coroutine(
                signal=signals.item_scraped, item=output, response=response,
                spider=spider)

    async def spider_is_idle(self, spider):
        # if not self.scraper.slot.is_idle():
        #     # scraper is not idle
        #     return False

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
        """Does the engine have capacity to handle more spiders"""
        return not bool(self.slot)

    async def crawl(self, request, spider):  # 将网址 请求加入队列
        # await self.call_helper(self.slot.scheduler.enqueue_request, request)
        if spider not in self.open_spiders:
            raise RuntimeError("Spider %r not opened when crawling: %s" % (spider.name, request))

        await self.signals.send_catch_log(signals.request_scheduled, request=request, spider=spider)
        if not await self.call_helper(self.slot.scheduler.enqueue_request, request):
            await self.signals.send_catch_log(signals.request_dropped, request=request, spider=spider)

    async def open_spider(self, spider, start_requests=None, close_if_idle=True):
        if not self.has_capacity():
            raise RuntimeError("No free spider slot when opening %r" % spider.name)
        self.logger.info("Spider opened({name})", **{"name": spider.name}, extra={'spider': spider})

        # scheduler = await self.call_helper(self.scheduler_cls.from_crawler, self.crawler)
        self.slot = Slot(start_requests, close_if_idle, self.scheduler, self.crawler)
        self.spider = spider
        await self.call_helper(self.scheduler.open, start_requests)
        # await self.call_helper(self.scraper.open_spider, spider)
        # await self.call_helper(self.crawler.stats.open_spider, spider)
        await self.signals.send_catch_log_coroutine(signals.spider_opened, spider=spider)
        await self._next_request(spider)
        self.slot.heartbeat = asyncio.create_task(self.heart_beat(5, spider, self.slot))

    async def _close_all_spiders(self):
        dfds = [self.close_spider(s, reason='shutdown') for s in self.open_spiders]
        await asyncio.gather(*dfds)

    async def close_spider(self, spider, reason='cancelled'):
        """Close (cancel) spider and clear all its outstanding requests"""
        slot = self.slot
        if slot and slot.closing:
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

        await close_handler(slot.scheduler.close, errmsg='Scheduler close failure')

        await close_handler(self.signals.send_catch_log_coroutine, signal=signals.spider_closed, spider=spider,
                            reason=reason, errmsg='Error while sending spider_close signal')

        self.logger.info("Spider({name}) closed ({reason})", **{'reason': reason, "name": spider.name}, extra={'spider': spider})

        await close_handler(setattr, self, 'slot', None, errmsg='Error while unassigning slot')

        await close_handler(setattr, self, 'spider', None, errmsg='Error while unassigning spider')

        await self._spider_closed_callback()

    async def _spider_idle(self, spider):
        res = await self.signals.send_catch_log(signals.spider_idle, spider=spider, dont_log=self.di.get("exceptions").DontCloseSpider)
        if any(isinstance(x, self.di.get("exceptions").DontCloseSpider) for _, x in res):
            return
        # if await self.spider_is_idle(spider):
        await self.close_spider(spider, reason='finished')

    async def heart_beat(self, delay, spider, slot):
        while not slot.closing:
            await asyncio.sleep(delay)
            asyncio.create_task(self._next_request(spider))
