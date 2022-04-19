"""Helper functions for working with signals"""
import asyncio

from pydispatch.dispatcher import Anonymous, Any, disconnect, getAllReceivers, liveReceivers
from pydispatch.robustapply import robustApply
from aioscpy.exceptions import StopDownload
from aioscpy.utils.log import logger


class _IgnoredException(Exception):
    pass


async def robustApplyWrap(f, recv, *args, **kw):
    dont_log = kw.pop('dont_log', None)
    spider = kw.get('spider', None)
    try:
        result = f(recv, *args, **kw)
        if asyncio.iscoroutine(result):
            return await result
    except (Exception, BaseException) as exc:  # noqa: E722
        if dont_log is None or not isinstance(exc, dont_log):
            logger.error("Error caught on signal handler: {receiver}",
                         **{'receiver': recv},
                         exc_info=exc,
                         extra={'spider': spider})
        return exc


async def send_catch_log(signal=Any, sender=Anonymous, *arguments, **named):
    """Like pydispatcher.robust.sendRobust but it also logs errors and returns
    Failures instead of exceptions.
    """
    named['dont_log'] = (named.pop('dont_log', _IgnoredException), StopDownload)
    responses = []
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        result = await robustApplyWrap(robustApply, receiver, signal=signal, sender=sender, *arguments, **named)
        responses.append((receiver, result))
    return responses


async def send_catch_log_deferred(signal=Any, sender=Anonymous, *arguments, **named):
    """Like send_catch_log but supports returning deferreds on signal handlers.
    Returns a deferred that gets fired once all signal handlers deferreds were
    fired.
    """
    dfds = []
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        dfds.append(asyncio.create_task(
            robustApplyWrap(robustApply, receiver, signal=signal, sender=sender, *arguments, **named)))
    res = await asyncio.gather(*dfds)
    return res


def disconnect_all(signal=Any, sender=Any):
    """Disconnect all signal handlers. Useful for cleaning up after running
    tests
    """
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        disconnect(receiver, signal=signal, sender=sender)

