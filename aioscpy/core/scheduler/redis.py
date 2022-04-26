from aioscpy.core.scheduler import Scheduler
from aioscpy.queue.redis import aio_priority_queue


class RedisScheduler(Scheduler):

    @classmethod
    def from_crawler(cls, crawler):
        redis_tcp = crawler.settings.get('REDIS_TCP')
        queue_key = crawler.settings.get('QUEUE_KEY') % crawler.spider.name
        return cls(_queue_df=aio_priority_queue(queue_key, redis_tcp))
