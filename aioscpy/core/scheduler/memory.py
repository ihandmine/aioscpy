from aioscpy.core.scheduler import Scheduler


class MemoryScheduler(Scheduler):

    @classmethod
    def from_crawler(cls, crawler):
        _queue = crawler.load("scheduler_priority_queue")
        return cls(_queue_df=_queue)
