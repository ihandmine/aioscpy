from aioscpy.utils.misc import load_object, create_instance


class Scheduler(object):

    def __init__(self):
        pass

    @classmethod
    def from_crawler(cls, crawler):
        setting = crawler.setting
        _queue_cls = load_object(setting.get('SCHEDULER_PRIORITY_QUEUE'))
        _key = setting.get('SCHEDULER_QUEUE_KEY')
        _
        _queue = create_instance(_queue_cls, )


    def enqueue_request(self, request):
        self.queue.push(request)
        return True

    def next_request(self):
        request = self.queue.pop()
        return request

    def has_pending_requests(self):
        return len(self) > 0
