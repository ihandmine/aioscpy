import aioredis

from aioredis import Redis

from queue import BaseQueue


class PriorityQueue(BaseQueue):
    async def qsize(self) -> int:
        return await self.server.zcard(self.key)

    async def push(self, request: dict):
        data = self._encode_request(request)
        score = -request.get('priority', 1)
        await self.server.zadd(self.key, score, data)

    async def pop(self, timeout: int = 0) -> dict:
        pipe = self.server.multi_exec()
        pipe.zrange(self.key, 0, 0)
        pipe.zremrangebyrank(self.key, 0, 0)
        results, count = await pipe.execute()
        if results: 
            return self._decode_request(results[0])


class AsyncRedis:
    __redis_instance = None

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = self.validator(kwargs)

    @staticmethod
    def validator(params: dict) -> dict:
        params.setdefault('host', '127.0.0.1')
        params.setdefault('port', 6379)
        params.setdefault('db', 1)
        params.setdefault('password', 'admin')
        params['address'] = (params.pop('host'), params.pop('port'))
        return params

    @property
    async def get_redis_pool(self) -> Redis:
        if not self.__redis_instance:
            self.__redis_instance = await aioredis.create_redis_pool(*self.args, **self.kwargs)
        return self.__redis_instance

    async def close(self):
        if self.__redis_instance:
            self.__redis_instance.close()
            await self.__redis_instance.wait_closed()


async def aio_priority_queue(key: str, redis_tcp: dict) -> PriorityQueue:
    server = await AsyncRedis(**redis_tcp).get_redis_pool
    return PriorityQueue(server=server, key=key)


spider_aio_priority_queue = aio_priority_queue

"""
# unit test example
async def run():
    queue = await redis_client('message:queue')
    # await queue.push({"url": "https://www.baidu.com/?kw=1", "task_id": '123'})
    print(await queue.pop())


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())

"""

