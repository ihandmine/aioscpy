

class Scheduler(object):

    def __init__(self, _queue_df):
        self.queue = _queue_df

    @classmethod
    def from_crawler(cls, crawler):
        raise NotImplementedError(
            '{} from_crawler method must define'.format(cls.__class__.__name__))

    async def enqueue_request(self, request):
        await self.queue.push(request)
        return True

    async def next_request(self):
        request = await self.queue.pop()
        return request

    async def open(self, start_requests):
        async for request in start_requests:
            await self.enqueue_request(request)

    async def close(self):
        await self.queue.close()

    def __len__(self):
        return self.queue.qsize()

    def has_pending_requests(self):
        return len(self) > 0
