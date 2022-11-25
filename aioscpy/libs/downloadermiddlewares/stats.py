from urllib.parse import urlunparse

from aioscpy.exceptions import NotConfigured
from aioscpy.utils.tools import to_bytes
from aioscpy.utils.othtypes import urlparse_cached


def global_object_name(obj):
    return f"{obj.__module__}.{obj.__name__}"


def request_httprepr(request: "Request") -> bytes:
    """Return the raw HTTP representation (as bytes) of the given request.
    This is provided only for reference since it's not the actual stream of
    bytes that will be send when performing the request (that's controlled
    by Twisted).
    """
    parsed = urlparse_cached(request)
    path = urlunparse(('', '', parsed.path or '/', parsed.params, parsed.query, ''))
    s = to_bytes(request.method) + b" " + to_bytes(path) + b" HTTP/1.1\r\n"
    s += b"Host: " + to_bytes(parsed.hostname or b'') + b"\r\n"
    if request.headers:
        s += request.headers.to_string() + b"\r\n"
    s += b"\r\n"
    s += str(request.body).encode() if isinstance(request.body, dict) else request.body
    return s


def get_header_size(headers):
    size = 0
    for key, value in headers.items():
        if isinstance(value, (list, tuple)):
            for v in value:
                size += len(b": ") + len(key) + len(v)
    return size + len(b'\r\n') * (len(headers.keys()) - 1)


class DownloaderStats:

    def __init__(self, stats):
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('DOWNLOADER_STATS'):
            raise NotConfigured
        return cls(crawler.stats)

    def process_request(self, request, spider):
        self.stats.inc_value('downloader/request_count', spider=spider)
        self.stats.inc_value(f'downloader/request_method_count/{request.method}', spider=spider)
        reqlen = len(request_httprepr(request))
        self.stats.inc_value('downloader/request_bytes', reqlen, spider=spider)

    def process_response(self, request, response, spider):
        self.stats.inc_value('downloader/response_count', spider=spider)
        self.stats.inc_value(f'downloader/response_status_count/{response.status}', spider=spider)
        reslen = len(response.body) + get_header_size(response.headers) + 4
        # response.body + b"\r\n"+ response.header + b"\r\n" + response.status
        self.stats.inc_value('downloader/response_bytes', reslen, spider=spider)
        return response

    def process_exception(self, request, exception, spider):
        ex_class = global_object_name(exception.__class__)
        self.stats.inc_value('downloader/exception_count', spider=spider)
        self.stats.inc_value(f'downloader/exception_type_count/{ex_class}', spider=spider)
