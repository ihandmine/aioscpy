from aioscpy.utils.misc import load_object, create_instance


class MemoryScheduler(object):

    def __init__(self):
        pass

    @classmethod
    def from_crawler(cls, crawler):
        setting = crawler.setting
        _queue_cls = load_object(setting.get('SCHEDULER_PRIORITY_QUEUE'))
