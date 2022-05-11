from aioscpy.queue.compat import COMPAT_TYPE

from aioscpy.queue.convert import request_from_dict, request_to_dict


class BaseQueue(object):

    __slots__ = ["server", "key", "serializer", "spider"]
    __compat__ = COMPAT_TYPE

    def __init__(self, server, spider=None, key=None, serializer=None):
        if serializer is None:
            serializer = self.__compat__[serializer or "json"]

        if not hasattr(serializer, 'loads'):
            raise TypeError("serializer does not implement 'loads' function: %r"
                            % serializer)
        if not hasattr(serializer, 'dumps'):
            raise TypeError("serializer does not implement 'dumps' function: %r"
                            % serializer)

        self.server = server
        self.key = key or 'sp:requests'
        self.serializer = serializer
        self.spider = spider

    def _encode_request(self, request) -> bytes:
        obj = request_to_dict(request, self.spider)
        return self.serializer.dumps(obj)

    def _decode_request(self, encoded_request: bytes) -> dict:
        obj = self.serializer.loads(encoded_request)
        return request_from_dict(obj, self.spider)
        # return obj

    def __len__(self):
        raise Exception('please use function len()')

    async def qsize(self):
        raise NotImplementedError

    async def push(self, request):
        raise NotImplementedError

    async def pop(self, timeout=0):
        raise NotImplementedError

    async def clear(self):
        await self.server.delete(self.key)

    async def close(self):
        if hasattr(self.server, "close"):
            await self.server.close()
