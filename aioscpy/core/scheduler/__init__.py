import asyncio


class Scheduler(object):

    def __init__(self, _queue_df, spider, stats):
        self.queue = _queue_df
        self.stats = stats
        self.spider = spider

    @classmethod
    def from_crawler(cls, crawler):
        raise NotImplementedError(
            '{} from_crawler method must define'.format(cls.__class__.__name__))

    async def enqueue_request(self, request):
        if self.stats:
            self.stats.inc_value('scheduler/enqueued/redis', spider=self.spider)
        await self.queue.push(request)
        return True

    async def async_next_request(self):
        _results = await self.queue.pop(count=100)
        self.stats.inc_value('scheduler/dequeued/redis', count=len(_results), spider=self.spider)
        return _results

    async def open(self, start_requests):
        if asyncio.iscoroutine(self.queue):
            self.queue = await self.queue
        async for request in start_requests:
            await self.enqueue_request(request)

    async def close(self, slot):
        if slot.inprogress:
            for request in slot.inprogress:
                await self.enqueue_request(request)
        await self.queue.close()

    def __len__(self):
        return self.queue.qsize()

    async def has_pending_requests(self):
        return len(self) > 0
