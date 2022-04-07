from aioscpy.utils.misc import load_object, create_instance
from aioscpy.core.scheduler import Scheduler


class MemoryScheduler(Scheduler):

    @classmethod
    def from_crawler(cls, crawler):
        setting = crawler.setting
        _queue_cls = load_object(setting.get('SCHEDULER_PRIORITY_QUEUE'))
        _queue = create_instance(_queue_cls, setting, crawler)
        return cls(_queue)
