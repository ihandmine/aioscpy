import pickle
import json


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
        return json.dumps(obj)


COMPAT_TYPE = {
    "pickle": PickleCompat,
    "json": JsonCompat
}

__all__ = [
    COMPAT_TYPE,
]
