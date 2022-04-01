from aioscpy.utils.misc import load_object, create_instance


class Scheduler(object):

    def __init__(self, queue):
        self.queue = queue

    @classmethod
    def from_crawler(cls, crawler):
        raise NotImplementedError(
            '{} from_crawler method must define'.format(cls.__class__.__name__))

    def enqueue_request(self, request):
        self.queue.push(request)
        return True

    def next_request(self):
        request = self.queue.pop()
        return request

    def __len__(self):
        return self.queue.qsize()

    def has_pending_requests(self):
        return len(self) > 0
