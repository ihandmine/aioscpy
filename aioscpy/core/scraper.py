"""This module implements the Scraper component which parses responses and
extracts information from them"""
import asyncio
import logging
from collections import deque

from aioscpy.middleware import SpiderMiddlewareManager
from aioscpy.http import Response
from aioscpy.utils.tools import call_helper
from aioscpy.utils.misc import load_object

logger = logging.getLogger(__name__)


class Slot:
    """Scraper slot (one per running spider)"""

    MIN_RESPONSE_SIZE = 1024

    def __init__(self, max_active_size=5000000):
        self.max_active_size = max_active_size
        self.queue = deque()
        self.active = set()
        self.active_size = 0
        self.itemproc_size = 0
        self.closing_future = None
        self.closing_lock = True

    def add_response_request(self, response, request):
        self.queue.append((response, request))
        if isinstance(response, Response):
            self.active_size += max(len(response.body), self.MIN_RESPONSE_SIZE)
        else:
            self.active_size += self.MIN_RESPONSE_SIZE

    def next_response_request_deferred(self):
        response, request = self.queue.popleft()
        self.active.add(request)
        return response, request

    def finish_response(self, response, request):
        self.active.remove(request)
        if isinstance(response, Response):
            self.active_size -= max(len(response.body), self.MIN_RESPONSE_SIZE)
        else:
            self.active_size -= self.MIN_RESPONSE_SIZE

    def is_idle(self):
        return not (self.queue or self.active)

    def needs_backout(self):
        return self.active_size > self.max_active_size


class Scraper:

    def __init__(self, crawler):
        self.slot = None
        self.spidermw = SpiderMiddlewareManager.from_crawler(crawler)
        itemproc_cls = load_object(crawler.settings['ITEM_PROCESSOR'])
        self.itemproc = itemproc_cls.from_crawler(crawler)
        self.crawler = crawler
        self.signals = crawler.signals
        self.logformatter = crawler.logformatter
        self.concurrent_items_semaphore = asyncio.Semaphore(crawler.settings.getint('CONCURRENT_ITEMS'))

    async def open_spider(self, spider):
        """Open the given spider for scraping and allocate resources for it"""
        self.slot = Slot(self.crawler.settings.getint('SCRAPER_SLOT_MAX_ACTIVE_SIZE'))
        await self.itemproc.open_spider(spider)

    async def close_spider(self, spider):
        """Close a spider being scraped and release its resources"""
        slot = self.slot
        slot.closing_future = asyncio.Future()
        await self.itemproc.close_spider(spider)
        self._check_if_closing(spider, slot)
        await slot.closing_future

    def is_idle(self):
        """Return True if there isn't any more spiders to process"""
        return not self.slot

    def _check_if_closing(self, spider, slot):
        if slot.closing_future and slot.is_idle() and slot.closing_lock:
            slot.closing_future.set_result(spider)
            slot.closing_lock = False

    async def enqueue_scrape(self, response, request, spider):
        slot = self.slot
        # 将结果缓存到slot中
        slot.add_response_request(response, request)
        try:
            # 处理响应结果
            await self._scrape_next(spider, slot)
        except (Exception, BaseException) as e:
            logger.error('Scraper bug processing %(request)s',
                         {'request': request},
                         exc_info=response,
                         extra={'spider': spider})
        finally:
            # 将slot中的缓存结果删除
            slot.finish_response(response, request)
            # 检测slot还有未处理的任务
            self._check_if_closing(spider, slot)
            # 继续处理slot缓存中的任务
            asyncio.create_task(self._scrape_next(spider, slot))

    async def _scrape_next(self, spider, slot):
        while slot.queue:
            response, request = slot.next_response_request_deferred()
            await self._scrape(response, request, spider)

    async def _scrape(self, result, request, spider):
        """
        Handle the downloaded response or failure through the spider callback/errback
        """
        if not isinstance(result, (Response, Exception, BaseException)):
            raise TypeError(f"Incorrect type: expected Response or Failure, got {type(result)}: {result!r}")
        try:
            response = await self._scrape2(result, request, spider)  # returns spider's processed output
        except (Exception, BaseException) as e:
            await self.handle_spider_error(e, request, result, spider)
        else:
            await self.handle_spider_output(response, request, result, spider)

    async def _scrape2(self, result, request, spider):
        """
        Handle the different cases of request's result been a Response or a Failure
        """
        if isinstance(result, Response):
            # 将Response丢给爬虫中间件处理, 处理结果将将给self.call_spider处理
            return await self.spidermw.scrape_response(self.call_spider, result, request, spider)
        else:
            try:
                # 处理下载错误或经过下载中间件时出现的错误
                return await self.call_spider(result, request, spider)
            except (Exception, BaseException) as e:
                await self._log_download_errors(e, result, request, spider)

    async def call_spider(self, result, request, spider):
        if isinstance(result, Response):
            # 将Response丢给spider的解析函数
            callback = request.callback or spider._parse
            warn_on_generator_with_return_value(spider, callback)
            result.request = request
            # 将parse解析出的结果,变成可迭代对象
            return await call_helper(callback, result, **result.request.cb_kwargs)
        else:
            if request.errback is None:
                raise result
            # 下载中间件或下载结果出现错误,回调request中的errback函数
            warn_on_generator_with_return_value(spider, request.errback)
            return await call_helper(request.errback, result)

    async def handle_spider_error(self, exc, request, response, spider):
        if isinstance(exc, CloseSpider):
            asyncio.create_task(self.crawler.engine.close_spider(spider, exc.reason or 'cancelled'))
            return
        logkws = self.logformatter.spider_error(exc, request, response, spider)
        logger.log(
            *logformatter_adapter(logkws),
            exc_info=exc,
            extra={'spider': spider}
        )
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
        """Process each Request/Item (given in the output parameter) returned
        from the given spider
        """
        async with self.concurrent_items_semaphore:
            if isinstance(output, Request):
                await self.crawler.engine.crawl(request=output, spider=spider)
            elif is_item(output):
                self.slot.itemproc_size += 1
                item = await self.itemproc.process_item(output, spider)
                process_item_method = getattr(spider, 'process_item', None)
                if process_item_method:
                    await call_helper(process_item_method, item)
                await self._itemproc_finished(output, item, response, spider)
            elif output is None:
                pass
            else:
                typename = type(output).__name__
                logger.error(
                    'Spider must return request, item, or None, got %(typename)r in %(request)s',
                    {'request': request, 'typename': typename},
                    extra={'spider': spider},
                )

    async def _log_download_errors(self, spider_exception, download_exception, request, spider):
        """
        处理并记录错误
        :param spider_exception: 将download_exception丢给request.errback处理时,触发的新错误
        :param download_exception: 下载过程发生的错误,或中间件中发生的错误
        :param request:
        :param spider:
        :return:
        """
        if isinstance(download_exception, (Exception, BaseException)) \
                and not isinstance(download_exception, IgnoreRequest):
            logkws = self.logformatter.download_error(download_exception, request, spider)
            logger.log(
                *logformatter_adapter(logkws),
                extra={'spider': spider},
                exc_info=download_exception,
            )

        if spider_exception is not download_exception:
            raise spider_exception

    async def _itemproc_finished(self, output, item, response, spider):
        """ItemProcessor finished for the given ``item`` and returned ``output``
        """
        self.slot.itemproc_size -= 1
        if isinstance(output, (Exception, BaseException)):
            if isinstance(output, DropItem):
                logkws = self.logformatter.dropped(item, output, response, spider)
                if logkws is not None:
                    logger.log(*logformatter_adapter(logkws), extra={'spider': spider})
                return await self.signals.send_catch_log_deferred(
                    signal=signals.item_dropped, item=item, response=response,
                    spider=spider, exception=output)
            else:
                logkws = self.logformatter.item_error(item, output, response, spider)
                logger.log(*logformatter_adapter(logkws), extra={'spider': spider},
                           exc_info=output)
                return await self.signals.send_catch_log_deferred(
                    signal=signals.item_error, item=item, response=response,
                    spider=spider, failure=output)
        else:
            logkws = self.logformatter.scraped(output, response, spider)
            if logkws is not None:
                logger.log(*logformatter_adapter(logkws), extra={'spider': spider})
            return await self.signals.send_catch_log_deferred(
                signal=signals.item_scraped, item=output, response=response,
                spider=spider)
