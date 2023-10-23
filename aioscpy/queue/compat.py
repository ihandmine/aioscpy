import pickle
import json

from aioscpy.utils.tools import to_unicode


def _request_byte2str(obj):
    _encoding = obj.get('_encoding', 'utf-8')
    if isinstance(obj['body'], bytes):
        _body = obj['body'].decode(_encoding)
    elif isinstance(obj['body'], dict):
        _body = json.dumps(obj['body'])
    else:
        _body = obj['body']
    _headers = {}
    for k, v in obj['headers'].items():
        if isinstance(k, bytes) or isinstance(v, bytes):
            _headers.update({to_unicode(k, encoding=_encoding): to_unicode(b','.join(v), encoding=_encoding)})
        else:
            _headers.update({k: v})
    obj.update({
        'body': _body,
        'headers': _headers
    })
    return obj


class PickleCompat:

    @staticmethod
    def loads(s: bytes) -> dict:
        return pickle.loads(s)

    @staticmethod
    def dumps(obj) -> bytes:
        return pickle.dumps(obj, protocol=-1)


class JsonCompat:

    @staticmethod
    def loads(s: bytes) -> dict:
        return json.loads(s)

    @staticmethod
    def dumps(obj) -> str:
        return json.dumps(_request_byte2str(obj))


COMPAT_TYPE = {
    "pickle": PickleCompat,
    "json": JsonCompat
}

__all__ = [
    COMPAT_TYPE,
]
