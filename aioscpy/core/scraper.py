import asyncio
import traceback
import functools

from collections import deque

from aioscpy import signals, call_grace_instance


class Slot:
    MIN_RESPONSE_SIZE = 1024

    def __init__(self, max_active_size=5000):
        self.max_active_size = max_active_size
        self.queue = deque()
        self.active = set()
        self.active_size = 0
        self.itemproc_size = 0
        self.closing_future = None
        self.closing_lock = True

    def add_response_request(self, response, request):
        self.queue.append((response, request))
        self.active.add(request)
        if hasattr(response, 'body'):
            self.active_size += max(len(response.body), self.MIN_RESPONSE_SIZE)

    def next_response_request_deferred(self):
        response, request = self.queue.popleft()
        return response, request

    def finish_response(self, request, response):
        if request in self.active:
            self.active.remove(request)
        # self.logger.warning(f'start finish response active del: {self.active_size}, active: {len(self.active)}, response: {len(response.body)}')
        if hasattr(response, 'body'):
            self.active_size -= max(len(response.body), self.MIN_RESPONSE_SIZE)
        request, response = None, None        

    def is_idle(self):
        return self.queue or self.active

    def needs_backout(self):
        return self.active_size > self.max_active_size


class Scraper:

    def __init__(self, crawler, engine):
        self.slot = None
        self.itemproc = call_grace_instance(self.di.get('item_processor'), only_instance=True).from_crawler(crawler)
        self.crawler = crawler
        self.signals = crawler.signals
        self.logformatter = crawler.load("log_formatter")
        self.call_helper = self.di.get("tools").call_helper
        self.engine = engine
        self.concurrent_items_semaphore = asyncio.Semaphore(crawler.settings.getint('CONCURRENT_ITEMS', 100))
        self.task_scrape_next = None

    async def open_spider(self, spider):
        self.slot = call_grace_instance(Slot, self.crawler.settings.getint('SCRAPER_SLOT_MAX_ACTIVE_SIZE', 500000))
        await self.itemproc.open_spider(spider)
        self.task_scrape_next = asyncio.create_task(self._scrape_next(spider, self.slot))

    async def close_spider(self, spider):
        slot = self.slot
        await self.itemproc.close_spider(spider)
        if self.task_scrape_next is not None:
            self.task_scrape_next.cancel()
        self._check_if_closing(spider, slot)

    def is_idle(self):
        return not self.slot

    def _check_if_closing(self, spider, slot):
        if not slot.closing_future and slot.is_idle() and slot.closing_lock:
            slot.closing_lock = False

    async def enqueue_scrape(self, response, request):
        slot = self.slot
        slot.add_response_request(response, request)

    async def _scrape_next(self, spider, slot):
        local_lock = True
        while True:
            while local_lock and slot.queue:
                local_lock = False
                response, request = slot.next_response_request_deferred()
                future = asyncio.create_task(self._scrape(response, request, spider))
                # future.add_done_callback(functools.partial(self.slot.finish_response, request, response))
                local_lock = True
            await asyncio.sleep(2)

    async def _scrape(self, result, request, spider):
        if not isinstance(result, (self.di.get('response'), Exception, BaseException)):
            raise TypeError(f"Incorrect type: expected Response or Failure, got {type(result)}: {result!r}")
        try:
            response = await self._scrape2(result, request, spider)  # returns spider's processed output
            await self.handle_spider_output(response, request, result, spider)
        except (Exception, BaseException) as e:
            await self.handle_spider_error(e, request, result, spider)
        return request, result

    async def _scrape2(self, result, request, spider):
        try:
            return await self.call_spider(result, request, spider)
        except (Exception, BaseException) as e:
            await self._log_download_errors(e, result, request, spider)

    async def call_spider(self, result, request, spider):
        if isinstance(result, self.di.get('response')):
            callback = request.callback or spider._parse
            result.request = request
            return await self.call_helper(callback, result, **result.request.cb_kwargs)
        else:
            if request.errback is None:
                raise result
            return await self.call_helper(request.errback, result)

    async def handle_spider_error(self, exc, request, response, spider):
        if isinstance(exc, self.di.get('exceptions').CloseSpider):
            asyncio.create_task(self.crawler.engine.close_spider(spider, exc.reason or 'cancelled'))
            return
        logkws = self.logformatter.spider_error(exc, request, response, spider)
        level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
        if type(exc).__name__ not in ['CancelledError']:
            self.logger.log(level, message, exception=True, depth=2, **kwargs)
            self.logger.error(f"handle_spider_error: {traceback.format_exc()}")
        await self.signals.send_catch_log(
            signal=signals.spider_error,
            failure=exc, response=response,
            spider=spider
        )
        self.crawler.stats.inc_value(
            "spider_exceptions/%s" % exc.__class__.__name__,
            spider=spider
        )

    async def handle_spider_output(self, result, request, response, spider):
        if not result:
            return

        while True:
            try:
                res = await result.__anext__()
            except StopAsyncIteration:
                break
            except Exception as e:
                await self.handle_spider_error(e, request, response, spider)
            else:
                await self._process_spidermw_output(res, request, response, spider)

    async def _process_spidermw_output(self, output, request, response, spider):
        async with self.concurrent_items_semaphore:
            if isinstance(output, self.di.get('request')):
                await self.crawler.engine.crawl(request=output, spider=spider)
            elif isinstance(output, dict):
                try:
                    self.slot.itemproc_size += 1
                    item = await self.itemproc.process_item(output, spider)
                    process_item_method = getattr(spider, 'process_item', None)
                    if process_item_method:
                        item = await self.call_helper(process_item_method, item)
                except Exception as e:
                    self.logger.error(f"process_spidermw_output: {traceback.format_exc()}")
                await self._itemproc_finished(output, item, request, response, spider)
                self.slot.finish_response(request, response)
            elif output is None:
                pass
            else:
                typename = type(output).__name__
                self.logger.error(
                    'Spider must return request, item, or None, got %(typename)r in %(request)s',
                    {'request': request, 'typename': typename},
                    extra={'spider': spider},
                )

    async def _log_download_errors(self, spider_exception, download_exception, request, spider):
        if isinstance(download_exception, (Exception, BaseException)) \
                and not isinstance(download_exception, self.di.get('exceptions').IgnoreRequest):
            logkws = self.logformatter.download_error(download_exception, request, spider)
            level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
            if type(download_exception).__name__ not in ['CancelledError']:
                self.logger.log(level, message, **kwargs)
                self.logger.error(traceback.format_exc())

        if spider_exception is not download_exception:
            raise spider_exception

    async def _itemproc_finished(self, output, item, request, response, spider):
        self.slot.itemproc_size -= 1
        if isinstance(output, (Exception, BaseException)):
            if isinstance(output, self.di.get('exceptions').DropItem):
                logkws = self.logformatter.dropped(item, output, response, spider)
                if logkws is not None:
                    level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
                    if type(output).__name__ not in ['CancelledError']:
                        self.logger.log(level, message, **kwargs)
                        self.logger.error(traceback.format_exc())
                await self.signals.send_catch_log_coroutine(
                    signal=signals.item_dropped, item=item, response=response,
                    spider=spider, exception=output)
            else:
                logkws = self.logformatter.item_error(item, output, response, spider)
                level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
                if type(output).__name__ not in ['CancelledError']:
                    self.logger.log(level, message, **kwargs)
                    self.logger.error(traceback.format_exc())
                await self.signals.send_catch_log_coroutine(
                    signal=signals.item_error, item=item, response=response,
                    spider=spider, failure=output)
        else:
            logkws = self.logformatter.scraped(output, response, spider)
            if logkws is not None:
                level, message, kwargs = self.di.get("log").logformatter_adapter(logkws)
                self.logger.log(level, message, **kwargs)
            await self.signals.send_catch_log_coroutine(
                signal=signals.item_scraped, item=output, response=response,
                spider=spider)
