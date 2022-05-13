from asyncio import Queue

from aioscpy.queue import BaseQueue


class PriorityQueue(BaseQueue):

    def __init__(self, server, spider, serializer="pickle"):
        super().__init__(server, spider)
        self.serializer = self.__compat__[serializer]

    def qsize(self) -> int:
        """Return the length of the queue"""
        return self.server.qsize()

    async def push(self, request):
        data = self._encode_request(request)
        await self.server.put(data)

    async def pop(self, timeout: int = 0) -> dict:
        _item = await self.server.get()
        return self._decode_request(_item)


def memory_queue(spider) -> PriorityQueue:
    server = Queue()
    return PriorityQueue(server=server, spider=spider)


spider_queue = memory_queue


"""
async def run():
    queue = memery_queue('message:queue')
    await queue.push({"url": "https://www.baidu.com/?kw=1", "task_id": '123'})
    print(await queue.pop())


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())

"""

