from typing import Generator
from urllib.parse import urljoin

from aioscpy.http.request import Request
from aioscpy.http.request.form import FormRequest
from aioscpy import call_grace_instance
from aioscpy.utils.tools import obsolete_setter


class Response(object):

    def __init__(self, url, status=200, headers=None, body=b'', flags=None, request=None, certificate=None, _response=None):
        self.headers = headers or {}
        self.status = int(status)
        self._set_body(body)
        self._set_url(url)
        self.request = request
        self.flags = [] if flags is None else list(flags)
        self.certificate = certificate
        self._response = _response

    @property
    def cb_kwargs(self):
        try:
            return self.request.cb_kwargs
        except AttributeError:
            raise AttributeError(
                "Response.cb_kwargs not available, this response "
                "is not tied to any request"
            )

    @property
    def meta(self):
        try:
            return self.request.meta
        except AttributeError:
            raise AttributeError(
                "Response.meta not available, this response "
                "is not tied to any request"
            )

    def _get_url(self):
        return self._url

    def _set_url(self, url):
        if isinstance(url, str):
            self._url = url
        else:
            raise TypeError('%s url must be str, got %s:' %
                            (type(self).__name__, type(url).__name__))

    url = property(_get_url, obsolete_setter(_set_url, 'url'))

    def _get_body(self):
        return self._body

    def _set_body(self, body):
        if body is None:
            self._body = b''
        elif not isinstance(body, bytes):
            raise TypeError(
                "Response body must be bytes. "
                "If you want to pass unicode body use TextResponse "
                "or HtmlResponse.")
        else:
            self._body = body

    body = property(_get_body, obsolete_setter(_set_body, 'body'))

    def __str__(self):
        return "<%d %s>" % (self.status, self.url)

    __repr__ = __str__

    def copy(self):
        """Return a copy of this Response"""
        return self.replace()

    def replace(self, *args, **kwargs):
        """Create a new Response with the same attributes except for those
        given new values.
        """
        for x in ['url', 'status', 'headers', 'body', 'request', 'flags', 'certificate']:
            kwargs.setdefault(x, getattr(self, x))
        cls = kwargs.pop('cls', self.__class__)
        return cls(*args, **kwargs)

    def urljoin(self, url: str) -> str:
        """Join this Response's url with a possible relative url to form an
        absolute interpretation of the latter."""
        return urljoin(self.url, url)

    @property
    def text(self):
        """For subclasses of TextResponse, this will return the body
        as str
        """
        raise AttributeError("Response content isn't text")

    def css(self, *a, **kw):
        """Shortcut method implemented only by responses whose content
        is text (subclasses of TextResponse).
        """
        # raise NotSupported("Response content isn't text")
        raise NotImplementedError

    def xpath(self, *a, **kw):
        """Shortcut method implemented only by responses whose content
        is text (subclasses of TextResponse).
        """
        # raise NotSupported("Response content isn't text")
        raise NotImplementedError

    def follow(self, url, callback=None, method='GET', formdata=None, headers=None, body=None,
               cookies=None, meta=None, encoding='utf-8', priority=0,
               dont_filter=False, errback=None, cb_kwargs=None, flags=None, **kwargs) -> Request:

        url = self.urljoin(url)
        method_request = Request
        if method == "POST":
            method_request = FormRequest
            kwargs['formdata'] = formdata

        return call_grace_instance(
               method_request,
               url=url,
               callback=callback,
               method=method,
               headers=headers,
               body=body,
               cookies=cookies,
               meta=meta,
               encoding=encoding,
               priority=priority,
               dont_filter=dont_filter,
               errback=errback,
               cb_kwargs=cb_kwargs,
               flags=flags,
               **kwargs
           )

    def follow_all(self, urls, callback=None, method='GET', headers=None, body=None,
                   cookies=None, meta=None, encoding='utf-8', priority=0,
                   dont_filter=False, errback=None, cb_kwargs=None, flags=None) -> Generator:
        if not hasattr(urls, '__iter__'):
            raise TypeError("'urls' argument must be an iterable")
        return (
            self.follow(
                url=url,
                callback=callback,
                method=method,
                headers=headers,
                body=body,
                cookies=cookies,
                meta=meta,
                encoding=encoding,
                priority=priority,
                dont_filter=dont_filter,
                errback=errback,
                cb_kwargs=cb_kwargs,
                flags=flags,
            )
            for url in urls
        )
