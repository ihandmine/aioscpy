from aioscpy.queue.compat import COMPAT_TYPE


class BaseQueue(object):

    __slots__ = ["server", "key", "serializer"]

    def __init__(self, server, key=None, serializer=None):
        if serializer is None:
            serializer = COMPAT_TYPE[serializer or "json"]

        if not hasattr(serializer, 'loads'):
            raise TypeError("serializer does not implement 'loads' function: %r"
                            % serializer)
        if not hasattr(serializer, 'dumps'):
            raise TypeError("serializer '%s' does not implement 'dumps' function: %r"
                            % serializer)

        self.server = server
        self.key = key or 'sp:requests'
        self.serializer = serializer

    def _encode_request(self, request: dict) -> bytes:
        return self.serializer.dumps(request)

    def _decode_request(self, encoded_request: bytes) -> dict:
        obj = self.serializer.loads(encoded_request)
        return obj

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
