from redis import ConnectionPool, StrictRedis

from queue import BaseQueue


class PriorityQueue(BaseQueue):
    def qsize(self) -> int:
        """Return the length of the queue"""
        return self.server.zcard(self.key)

    def push(self, request: dict):
        data = self._encode_request(request)
        score = -request.get('priority', 1)
        self.server.zadd(self.key, {data: score})

    def pop(self, timeout: int = 0) -> dict:
        pipe = self.server.pipeline()
        pipe.multi()
        pipe.zrange(self.key, 0, 0).zremrangebyrank(self.key, 0, 0)
        results, count = pipe.execute()
        if results:
            return self._decode_request(results[0])


class Redis:

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
        return params

    @property
    def format_url(self) -> str:
        """REDIS_URL = 'redis://:123456@172.16.8.147:6379/1'"""
        _format_url = f"redis://:{self.kwargs['password']}@{self.kwargs['host']}:{self.kwargs['port']}/{self.kwargs['db']}"\
            if not self.kwargs.get('redis_url') else self.kwargs['redis_url']
        return _format_url

    @property
    def get_redis_pool(self) -> StrictRedis:
        if not self.__redis_instance:
            pool = ConnectionPool(**self.kwargs)
            self.__redis_instance = StrictRedis(connection_pool=pool)

        return self.__redis_instance

    def close(self):
        if self.__redis_instance:
            self.__redis_instance.close()


def priority_queue(key: str, redis_tcp: dict) -> PriorityQueue:
    server = Redis(**redis_tcp).get_redis_pool
    return PriorityQueue(server=server, key=key)


spider_priority_queue = priority_queue

"""
def run():
    queue = redis_client('message:queue')
    # queue.push({"url": "https://www.baidu.com/?kw=1", "task_id": '123'})
    print(queue.pop())

run()
"""
