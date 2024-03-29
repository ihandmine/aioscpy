"""
Helper functions for serializing (and deserializing) requests.
"""
import inspect
import json

from aioscpy import call_grace_instance
from aioscpy.http import Request
from aioscpy.utils.tools import to_unicode
from aioscpy.inject import load_object
from anti_header import Headers


def request_to_dict(request, spider=None):
    """Convert Request object to a dict.

    If a spider is given, it will try to find out the name of the spider method
    used in the callback and store that as the callback.
    """
    cb = request.callback
    if callable(cb):
        cb = _find_method(spider, cb)
    eb = request.errback
    if callable(eb):
        eb = _find_method(spider, eb)
    d = {
        'url': to_unicode(request.url),  # urls should be safe (safe_string_url)
        'callback': cb,
        'errback': eb,
        'method': request.method,
        'headers': dict(request.headers),
        'body': request.body,
        'json': request.json,
        'cookies': request.cookies,
        'meta': request.meta,
        '_encoding': request._encoding,
        'priority': request.priority,
        'dont_filter': request.dont_filter,
        'flags': request.flags,
        'cb_kwargs': request.cb_kwargs,
    }
    _body = getattr(request, "body")
    _json = getattr(request, "json")
    if _body and isinstance(_body, dict) or _json and isinstance(_json, dict):
        base_cls = request.__class__.__bases__[0]
        d['_class'] = base_cls.__module__ + '.' + base_cls.__name__
    return d


def request_from_dict(d, spider=None):
    """Create Request object from a dict.

    If a spider is given, it will try to resolve the callbacks looking at the
    spider for methods with the same name.
    """
    cb = d.get('callback', 'parse')
    if cb and spider:
        cb = _get_method(spider, cb)
    eb = d.get('errback')
    if eb and spider:
        eb = _get_method(spider, eb)
    request_cls = load_object(d['_class']) if '_class' in d else Request

    _json, _body = None, None
    if request_cls.__name__ in ["FormRequest"]:
        if d.get('body') and isinstance(d.get('body'), dict):
            _body = d['body']
        elif d.get('body') and isinstance(d.get('body'), str):
            _body = json.loads(d['body'])
    elif request_cls.__name__ in ["JsonRequest"]:
        if d.get('json') and isinstance(d.get('json'), dict):
            _json = d['json']
        elif d.get('json') and isinstance(d.get('json'), str):
            _json = json.loads(d['json'])

    return call_grace_instance(
            request_cls,
            url=to_unicode(d['url']),
            callback=cb,
            errback=eb,
            method=d.get('method', 'GET'),
            headers=Headers(d.get('headers', {})),
            body=_body,
            json=_json,
            cookies=d.get('cookies'),
            meta=d.get('meta'),
            encoding=d.get('_encoding', 'utf-8'),
            priority=d.get('priority', 0),
            dont_filter=d.get('dont_filter', True),
            flags=d.get('flags'),
            cb_kwargs=d.get('cb_kwargs'),
    )


def _find_method(obj, func):
    # Only instance methods contain ``__func__``
    if obj and hasattr(func, '__func__'):
        members = inspect.getmembers(obj, predicate=inspect.ismethod)
        for name, obj_func in members:
            # We need to use __func__ to access the original
            # function object because instance method objects
            # are generated each time attribute is retrieved from
            # instance.
            #
            # Reference: The standard type hierarchy
            # https://docs.python.org/3/reference/datamodel.html
            if obj_func.__func__ is func.__func__:
                return name
    raise ValueError(f"Function {func} is not an instance method in: {obj}")


def _get_method(obj, name):
    name = str(name)
    try:
        return getattr(obj, name)
    except AttributeError:
        raise ValueError(f"Method {name!r} not found in: {obj}")
