import logging
import pprint
from asyncio import iscoroutinefunction
from collections import defaultdict, deque

from aioscpy.exceptions import NotConfigured
from aioscpy.utils.misc import create_instance, load_object

logger = logging.getLogger(__name__)


class MiddlewareManager:
    """Base class for implementing middleware managers"""

    component_name = 'foo middleware'

    def __init__(self, *middlewares):
        self.middlewares = middlewares
        self.methods = defaultdict(deque)
        for mw in middlewares:
            self._add_middleware(mw)

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        raise NotImplementedError

    @classmethod
    def from_settings(cls, settings, crawler=None):
        mwlist = cls._get_mwlist_from_settings(settings)
        middlewares = []
        enabled = []
        for clspath in mwlist:
            try:
                mwcls = load_object(clspath)
                mw = create_instance(mwcls, settings, crawler)
                middlewares.append(mw)
                enabled.append(clspath)
            except NotConfigured as e:
                if e.args:
                    clsname = clspath.split('.')[-1]
                    logger.warning("Disabled %(clsname)s: %(eargs)s",
                                   {'clsname': clsname, 'eargs': e.args[0]},
                                   extra={'crawler': crawler})
        if enabled:
            logger.info("Enabled %(name)s %(componentname)ss:\n%(enabledlist)s",
                        {'componentname': cls.component_name,
                         'enabledlist': pprint.pformat(enabled),
                         'name': crawler.spider.name},
                        extra={'crawler': crawler})
        return cls(*middlewares)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings, crawler)

    def _add_middleware(self, mw):
        if hasattr(mw, 'open_spider'):
            self.methods['open_spider'].append(mw.open_spider)
        if hasattr(mw, 'close_spider'):
            self.methods['close_spider'].appendleft(mw.close_spider)

    async def _process_parallel(self, methodname, obj, *args):
        return await self.process_parallel(self.methods[methodname], obj, *args)

    async def _process_chain(self, methodname, obj, *args):
        return await self.process_chain(self.methods[methodname], obj, *args)

    async def _process_chain_both(self, cb_methodname, eb_methodname, obj, *args):
        return await self.process_chain_both(self.methods[cb_methodname],
                                             self.methods[eb_methodname], obj, *args)

    async def open_spider(self, spider):
        return await self._process_parallel('open_spider', spider)

    async def close_spider(self, spider):
        return await self._process_parallel('close_spider', spider)

    @staticmethod
    async def process_parallel(callbacks, input_, *a, **kw):
        for callback in callbacks:
            if iscoroutinefunction(callback):
                await callback(input_, *a, **kw)
            else:
                callback(input_, *a, **kw)

    @staticmethod
    async def process_chain(callbacks, input_, *a, **kw):
        for callback in callbacks:
            if iscoroutinefunction(callback):
                input_result = await callback(input_, *a, **kw)
            else:
                input_result = callback(input_, *a, **kw)
            if input_result is not None:
                input_ = input_result
        return input_

    @staticmethod
    async def process_chain_both(callbacks, errbacks, input_, *a, **kw):
        for cb, eb in zip(callbacks, errbacks):
            try:
                if iscoroutinefunction(cb):
                    input_ = await cb(input_, *a, **kw)
                else:
                    input_ = cb(input_, *a, **kw)
            except(Exception, BaseException) as e:
                if iscoroutinefunction(cb):
                    input_ = await eb(input_, *a, **kw)
                else:
                    input_ = eb(input_, *a, **kw)
            return input_
