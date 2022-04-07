"""
Spider Middleware manager

See documentation in docs/topics/spider-middleware.rst
"""
from itertools import islice
from types import AsyncGeneratorType

from scrapy.exceptions import _InvalidOutput
from scrapy.utils.conf import build_component_list

from aioscpy.utils.tools import async_generator_wrapper
from aioscpy.utils.tools import call_helper
from .middleware import MiddlewareManager


def _isiterable(possible_iterator):
    return hasattr(possible_iterator, '__iter__')


def _is_async_generator(possible_iterator):
    return isinstance(possible_iterator, AsyncGeneratorType)


def _fname(f):
    return "{}.{}".format(
        f.__self__.__class__.__name__,
        f.__func__.__name__
    )


class SpiderMiddlewareManager(MiddlewareManager):
    component_name = 'spider middleware'

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        return build_component_list(settings.getwithbase('SPIDER_MIDDLEWARES'))

    def _add_middleware(self, mw):
        super(SpiderMiddlewareManager, self)._add_middleware(mw)
        if hasattr(mw, 'process_spider_input'):
            self.methods['process_spider_input'].append(mw.process_spider_input)
        if hasattr(mw, 'process_start_requests'):
            self.methods['process_start_requests'].appendleft(mw.process_start_requests)
        process_spider_output = getattr(mw, 'process_spider_output', None)
        self.methods['process_spider_output'].appendleft(process_spider_output)
        process_spider_exception = getattr(mw, 'process_spider_exception', None)
        self.methods['process_spider_exception'].appendleft(process_spider_exception)

    async def scrape_response(self, scrape_func, response, request, spider):

        async def process_spider_input(response):
            for method in self.methods['process_spider_input']:
                try:
                    result = await call_helper(method, response=response, spider=spider)
                    if result is not None:
                        msg = "Middleware {} must return None or raise an exception, got {}"
                        raise _InvalidOutput(msg.format(_fname(method), type(result)))
                except _InvalidOutput:
                    raise
                except Exception as exception:
                    iterable_or_exception = await call_helper(scrape_func, exception, request, spider)
                    if iterable_or_exception is exception:
                        raise iterable_or_exception
                    return iterable_or_exception
            return await call_helper(scrape_func, response, request, spider)

        async def _evaluate_iterable(maybe_async_gen, exception_processor_index):
            try:
                # 将所有非AsyncGeneratorType变成AsyncGeneratorType对象
                async_gen = await async_generator_wrapper(maybe_async_gen)
                async for r in async_gen:
                    yield r
            except Exception as ex:
                exception_result = await process_spider_exception(ex, exception_processor_index)
                if isinstance(exception_result, (Exception, BaseException)):
                    raise exception_result
                async for r in _evaluate_iterable(exception_result, exception_processor_index):
                    yield r

        async def process_spider_exception(exception, start_index=0):
            # don't handle _InvalidOutput exception
            if isinstance(exception, _InvalidOutput):
                raise exception
            method_list = islice(self.methods['process_spider_exception'], start_index, None)
            for method_index, method in enumerate(method_list, start=start_index):
                if method is None:
                    continue
                result = await call_helper(method, response=response, exception=exception, spider=spider)
                if _is_async_generator(result) or _isiterable(result):
                    # stop exception handling by handing control over to the
                    # process_spider_output chain if an iterable has been returned
                    return await process_spider_output(result, method_index + 1)
                elif result is None:
                    continue
                else:
                    msg = "Middleware {} must return None or an iterable, got {}"
                    raise _InvalidOutput(msg.format(_fname(method), type(result)))
            raise exception

        async def process_spider_output(result, start_index=0):
            # items in this iterable do not need to go through the process_spider_output
            # chain, they went through it already from the process_spider_exception method

            method_list = islice(self.methods['process_spider_output'], start_index, None)
            for method_index, method in enumerate(method_list, start=start_index):
                if method is None:
                    continue
                try:
                    # might fail directly if the output value is not a generator
                    result = await call_helper(method, response=response, result=result, spider=spider)
                except Exception as ex:
                    exception_result = await process_spider_exception(ex, method_index + 1)
                    if isinstance(exception_result, (Exception, BaseException)):
                        raise
                    return exception_result
                if _is_async_generator(result) or _isiterable(result):
                    result = _evaluate_iterable(result, method_index + 1)
                else:
                    msg = "Middleware {} must return an iterable, got {}"
                    raise _InvalidOutput(msg.format(_fname(method), type(result)))

            return result

        async def process_callback_output(result):
            result = _evaluate_iterable(result, 0)
            return await process_spider_output(result)

        try:
            iterable = await process_spider_input(response)
        except (Exception, BaseException) as exc:
            result = await process_spider_exception(exc)
        else:
            result = await process_callback_output(iterable)
        return result

    async def process_start_requests(self, start_requests, spider):
        return await self._process_chain('process_start_requests', start_requests, spider)
