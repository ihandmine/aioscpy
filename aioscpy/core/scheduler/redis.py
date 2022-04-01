from aioscpy.utils.misc import load_object, create_instance
from aioscpy.core.scheduler import Scheduler


class RedisScheduler(Scheduler):

    @classmethod
    def from_crawler(cls, crawler):
        setting = crawler.setting
        _queue_cls = load_object(setting.get('SCHEDULER_PRIORITY_QUEUE'))
        _queue_key = setting.get('SCHEDULER_QUEUE_KEY')
        _queue_tcp = setting.get('SCHEDULER_QUEUE_TCP')
        _queue = create_instance(_queue_cls, _queue_key, _queue_tcp)
        return cls(_queue)
