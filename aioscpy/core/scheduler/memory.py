from aioscpy.utils.misc import load_object
from aioscpy.core.scheduler import Scheduler


class MemoryScheduler(Scheduler):

    @classmethod
    def from_crawler(cls, crawler):
        setting = crawler.settings
        _queue = load_object(setting.get('SCHEDULER_PRIORITY_QUEUE'))
        return cls(_queue_df=_queue)
