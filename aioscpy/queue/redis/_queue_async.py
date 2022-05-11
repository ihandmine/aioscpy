from aioredis import Redis, BlockingConnectionPool

from aioscpy.queue import BaseQueue


class PriorityQueue(BaseQueue):
    def __init__(self, server, spider, key=None, serializer="pickle"):
        super().__init__(server, spider, key)
        self.serializer = self.__compat__[serializer]

    async def qsize(self) -> int:
        return await self.server.zcard(self.key)

    async def push(self, request):
        data = self._encode_request(request)
        score = -request.get('priority', 1)
        await self.server.zadd(self.key, {data: score})

    async def pop(self, timeout: int = 0) -> dict:
        async with self.server.pipeline(transaction=True) as pipe:
            results, count = await (
                pipe.zrange(self.key, 0, 0)
                    .zremrangebyrank(self.key, 0, 0)
                    .execute()
            )
        if results:
            return self._decode_request(results[0])


class AsyncRedis:
    __redis_instance = None

    def __init__(self, *args, **kwargs):
        self.args = args
        if not kwargs:
            self.kwargs = self.validator(kwargs)
        self.kwargs = kwargs

    @staticmethod
    def validator(params: dict) -> dict:
        params.setdefault('host', '127.0.0.1')
        params.setdefault('port', 6379)
        params.setdefault('db', 1)
        params.setdefault('password', 'admin')
        return params

    @property
    async def get_redis_pool(self) -> Redis:
        if not self.__redis_instance:
            url = self.kwargs.pop('url', None)
            if url:
                connection_pool = BlockingConnectionPool.from_url(url, **self.kwargs)
            else:
                connection_pool = BlockingConnectionPool(**self.kwargs)
            self.__redis_instance = Redis(connection_pool=connection_pool)
        return self.__redis_instance

    async def close(self):
        if self.__redis_instance:
            await self.__redis_instance.close()


async def aio_priority_queue(key: str, redis_tcp, spider) -> PriorityQueue:
    if isinstance(redis_tcp, str):
        redis_tcp = {'url': redis_tcp}
    server = await AsyncRedis(**redis_tcp).get_redis_pool
    return PriorityQueue(server=server, spider=spider, key=key, serializer='json')


spider_aio_priority_queue = aio_priority_queue

"""
# unit test example
async def run():
    REDIS_TCP = {
                "host": "172.16.7.172",
                "port": 6379,
                "password": "123456",
                "db": 15
            }
    queue = await aio_priority_queue('message:queue', REDIS_TCP)
    # await queue.push({"url": "https://www.baidu.com/?kw=1", "task_id": '123'})
    print(await queue.pop())


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
"""

