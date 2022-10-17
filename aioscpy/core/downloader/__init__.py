import asyncio
import random

from datetime import datetime
from collections import deque

from aioscpy import signals
from aioscpy import call_grace_instance


class Slot:
    """Downloader slot"""

    def __init__(self, concurrency, randomize_delay, delay=0):
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


class Downloader(object):
    DOWNLOAD_SLOT = 'download_slot'

    def __init__(self, crawler):
        self.settings = crawler.settings
        self.crawler = crawler
        self.slot = None
        self.active = set()
        self.call_helper = self.di.get("tools").call_helper
        self.handlers = call_grace_instance('downloader_handler', self.settings, crawler)
        self.total_concurrency = self.settings.getint('CONCURRENT_REQUESTS')
        self.domain_concurrency = self.settings.getint('CONCURRENT_REQUESTS_PER_DOMAIN')
        self.ip_concurrency = self.settings.getint('CONCURRENT_REQUESTS_PER_IP')
        self.randomize_delay = self.settings.getbool('RANDOMIZE_DOWNLOAD_DELAY')
        self.delay = self.settings.getfloat('DOWNLOAD_DELAY')
        self.middleware = call_grace_instance(self.di.get('downloader_middleware'), only_instance=True).from_crawler(crawler)
        self.process_queue_task = None
        self.engine = None

        crawler.signals.connect(self.close, signals.engine_stopped)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def open(self, spider, engine):
        conc = self.ip_concurrency if self.ip_concurrency else self.domain_concurrency
        self.slot = Slot(conc, self.randomize_delay, self.delay)
        self.engine = engine
        self.process_queue_task = asyncio.create_task(self._process_queue(spider, self.slot))

    async def fetch(self, request):
        self.active.add(request)
        self.slot.active.add(request)
        self.slot.queue.append(request)

    async def _process_queue(self, spider, slot):
        while True:
            await asyncio.sleep(0.1)
            while slot.queue and slot.free_transfer_slots() > 0:
                if slot.download_delay():
                    await asyncio.sleep(slot.download_delay())
                request = slot.queue.popleft()
                asyncio.create_task(self._download(slot, request, spider))
                slot.transferring.add(request)
                slot.active.remove(request)
                self.active.remove(request)

    async def _download(self, slot, request, spider):
        response = None
        response = await self.middleware.process_request(spider, request)
        process_request_method = getattr(spider, "process_request", None)
        if process_request_method:
            response = await self.call_helper(process_request_method, request)
        try:
            if response is None or isinstance(response, self.di.get('request')):
                request = response or request
                response = await self.handlers.download_request(request, spider)
        except (Exception, BaseException, asyncio.TimeoutError) as exc:
            response = await self.middleware.process_exception(spider, request, exc)
            process_exception_method = getattr(spider, "process_exception", None)
            if process_exception_method:
                response = await self.call_helper(process_exception_method, request, exc)
        else:
            try:
                response = await self.middleware.process_response(spider, request, response)
                process_response_method = getattr(spider, "process_response", None)
                if process_response_method:
                    response = await self.call_helper(process_response_method, request, response)
            except (Exception, BaseException) as exc:
                response = exc
        finally:
            slot.transferring.remove(request)
            if isinstance(response, self.di.get('response')):
                response.request = request
            await self.engine._handle_downloader_output(response, request, spider)

    async def close(self):
        try:
            if self.slot is not None:
                self.slot.close()
            await self.handlers.close()
            if self.process_queue_task:
                self.process_queue_task.cancel()
        except (asyncio.CancelledError, Exception, BaseException) as exc:
            pass

    def needs_backout(self):
        return len(self.active) >= self.total_concurrency
