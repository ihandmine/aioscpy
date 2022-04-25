from aioscpy.core.scheduler import Scheduler
from aioscpy.queue.memory import memory_queue


class MemoryScheduler(Scheduler):

    @classmethod
    def from_crawler(cls, crawler):
        return cls(_queue_df=memory_queue())
