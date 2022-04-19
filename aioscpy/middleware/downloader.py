import logging
from asyncio import iscoroutinefunction

from scrapy.exceptions import _InvalidOutput
from scrapy.http import Request, Response
from scrapy.utils.conf import build_component_list

from .middleware import MiddlewareManager

logger = logging.getLogger(__name__)


class DownloaderMiddlewareManager(MiddlewareManager):
    component_name = 'downloader middleware'

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        return build_component_list(
            settings.getwithbase('DOWNLOADER_MIDDLEWARES'))

    def _add_middleware(self, mw):
        if hasattr(mw, 'process_request'):
            self.methods['process_request'].append(mw.process_request)
        if hasattr(mw, 'process_response'):
            self.methods['process_response'].appendleft(mw.process_response)
        if hasattr(mw, 'process_exception'):
            self.methods['process_exception'].appendleft(mw.process_exception)

    async def process_request(self, spider, request):
        for method in self.methods['process_request']:
            if iscoroutinefunction(method):
                response = await method(request=request, spider=spider)
            else:
                response = method(request=request, spider=spider)
            if response is not None and not isinstance(response, (Response, Request)):
                raise _InvalidOutput(
                    "Middleware %s.process_request must return None, Response or Request, got %s"
                    % (method.__self__.__class__.__name__, response.__class__.__name__)
                )
            if response:
                return response

    async def process_response(self, spider, request, response):
        if response is None:
            raise TypeError("Received None in process_response")
        elif isinstance(response, Request):
            return response

        for method in self.methods['process_response']:
            if iscoroutinefunction(method):
                response = await method(request=request, response=response, spider=spider)
            else:
                response = method(request=request, response=response, spider=spider)
            if not isinstance(response, (Response, Request)):
                raise _InvalidOutput(
                    "Middleware %s.process_response must return Response or Request, got %s"
                    % (method.__self__.__class__.__name__, type(response))
                )
            if isinstance(response, Request):
                return response
        return response

    async def process_exception(self, spider, request, exception):
        for method in self.methods['process_exception']:
            if iscoroutinefunction(method):
                response = await method(request=request, exception=exception, spider=spider)
            else:
                response = method(request=request, exception=exception, spider=spider)
            if response is not None and not isinstance(response, (Response, Request)):
                raise _InvalidOutput(
                    "Middleware %s.process_exception must return None, Response or Request, got %s"
                    % (method.__self__.__class__.__name__, type(response))
                )
            if response:
                return response
        return exception

