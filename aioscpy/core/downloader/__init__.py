import asyncio
import random
from collections import deque
from datetime import datetime
from time import time

# from scrapy.resolver import dnscache
# from scrapy.utils.httpobj import urlparse_cached

from aioscpy.http import Request, Response
from aioscpy.middleware import DownloaderMiddlewareManager
from aioscpy.core.downloader.http import AioHttpDownloadHandler


class Slot:
    """Downloader slot"""

    def __init__(self, concurrency, delay, randomize_delay):
        self.concurrency = concurrency
        self.delay = delay
        self.randomize_delay = randomize_delay

        self.active = set()
        self.queue = deque()
        self.transferring = set()
        self.lastseen = 0
        self.delay_run = False

    def free_transfer_slots(self):
        return self.concurrency - len(self.transferring)

    def download_delay(self):
        if self.randomize_delay:
            return random.uniform(0.5 * self.delay, 1.5 * self.delay)
        return self.delay

    def close(self):
        self.delay_run = True

    def __repr__(self):
        cls_name = self.__class__.__name__
        return "%s(concurrency=%r, delay=%0.2f, randomize_delay=%r)" % (
            cls_name, self.concurrency, self.delay, self.randomize_delay)

    def __str__(self):
        return (
                "<downloader.Slot concurrency=%r delay=%0.2f randomize_delay=%r "
                "len(active)=%d len(queue)=%d len(transferring)=%d lastseen=%s>" % (
                    self.concurrency, self.delay, self.randomize_delay,
                    len(self.active), len(self.queue), len(self.transferring),
                    datetime.fromtimestamp(self.lastseen).isoformat()
                )
        )


def _get_concurrency_delay(concurrency, spider, settings):
    delay = settings.getfloat('DOWNLOAD_DELAY')
    if hasattr(spider, 'download_delay'):
        delay = spider.download_delay

    if hasattr(spider, 'max_concurrent_requests'):
        concurrency = spider.max_concurrent_requests

    return concurrency, delay


class Downloader:
    DOWNLOAD_SLOT = 'download_slot'

    def __init__(self, crawler):
        self.settings = crawler.settings
        # self.signals = crawler.signals
        self.slots = {}
        self.active = set()
        self.handlers = AioHttpDownloadHandler(self.settings)
        self.total_concurrency = self.settings.getint('CONCURRENT_REQUESTS')
        self.domain_concurrency = self.settings.getint('CONCURRENT_REQUESTS_PER_DOMAIN')
        self.ip_concurrency = self.settings.getint('CONCURRENT_REQUESTS_PER_IP')
        self.randomize_delay = self.settings.getbool('RANDOMIZE_DOWNLOAD_DELAY')
        self.middleware = DownloaderMiddlewareManager.from_crawler(crawler)
        self._slot_gc_loop = True
        asyncio.create_task(self._slot_gc(60))

    async def fetch(self, request, spider, _handle_downloader_output):
        self.active.add(request)
        # key, slot = self._get_slot(request, spider)
        # request.meta[self.DOWNLOAD_SLOT] = key
        conc = self.ip_concurrency if self.ip_concurrency else self.domain_concurrency
        conc, delay = _get_concurrency_delay(conc, spider, self.settings)
        slot = Slot(conc, delay, self.randomize_delay)

        slot.active.add(request)
        slot.queue.append((request, _handle_downloader_output))
        asyncio.create_task(self._process_queue(spider, slot))

    async def _process_queue(self, spider, slot):
        if slot.delay_run:
            return

        # Delay queue processing if a download_delay is configured
        now = time()
        delay = slot.download_delay()
        if delay:
            penalty = delay - now + slot.lastseen
            if penalty > 0:
                slot.delay_run = True
                await asyncio.sleep(penalty)
                slot.delay_run = False
                asyncio.create_task(self._process_queue(spider, slot))
                return

        # Process enqueued requests if there are free slots to transfer for this slot
        while slot.queue and slot.free_transfer_slots() > 0:
            slot.lastseen = now
            request, _handle_downloader_output = slot.queue.popleft()
            asyncio.create_task(self._download(slot, request, spider, _handle_downloader_output))
            # prevent burst if inter-request delays were configured
            if delay:
                asyncio.create_task(self._process_queue(spider, slot))
                break

    async def _download(self, slot, request, spider, _handle_downloader_output):
        slot.transferring.add(request)
        response = None
        try:
            response = await self.middleware.process_request(spider, request)
            if response is None or isinstance(response, Request):
                request = response or request
                response = await self.handlers.download_request(request, spider)
        except (Exception, BaseException) as exc:
            response = await self.middleware.process_exception(spider, request, exc)
        else:
            try:
                response = await self.middleware.process_response(spider, request, response)
            except (Exception, BaseException) as exc:
                response = exc
        finally:
            slot.transferring.remove(request)
            slot.active.remove(request)
            self.active.remove(request)
            asyncio.create_task(self._process_queue(spider, slot))
            if isinstance(response, Response):
                response.request = request
            asyncio.create_task(_handle_downloader_output(response, request, spider))

    def close(self):
        self._slot_gc_loop = False
        for slot in self.slots.values():
            slot.close()

    async def _slot_gc(self, age=60):
        mintime = time() - age
        for key, slot in list(self.slots.items()):
            if not slot.active and slot.lastseen + slot.delay < mintime:
                self.slots.pop(key).close()
        await asyncio.sleep(age)
        if self._slot_gc_loop:
            asyncio.create_task(self._slot_gc())

    def needs_backout(self):
        return len(self.active) >= self.total_concurrency

    # def _get_slot(self, request, spider):
    #     # key = self._get_slot_key(request, spider)
    #     if key not in self.slots:
    #         conc = self.ip_concurrency if self.ip_concurrency else self.domain_concurrency
    #         conc, delay = _get_concurrency_delay(conc, spider, self.settings)
    #         self.slots[key] = Slot(conc, delay, self.randomize_delay)
    #
    #     return key, self.slots[key]

    # def _get_slot_key(self, request, spider):
    #     if self.DOWNLOAD_SLOT in request.meta:
    #         return request.meta[self.DOWNLOAD_SLOT]
    #
    #     key = urlparse_cached(request).hostname or ''
    #     if self.ip_concurrency:
    #         key = dnscache.get(key, key)
    #
    #     return key
