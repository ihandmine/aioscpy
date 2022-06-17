from contextlib import suppress

import re
import parsel
from w3lib.encoding import (html_body_declared_encoding, html_to_unicode,
                            http_content_type_encoding, resolve_encoding)
from w3lib.html import strip_html5_whitespace
from parsel import Selector

from aioscpy.http import Request
from aioscpy.http.response import Response
from aioscpy.utils.tools import to_unicode, memoizemethod_noargs, call_helper


class TextResponse(Response):

    _DEFAULT_ENCODING = 'ascii'

    def __init__(self, *args, **kwargs):
        self._encoding = kwargs.pop('encoding', None) or "utf-8"
        self._cached_benc = None
        self._cached_ubody = None
        self._cached_selector = None
        self.cookies = self._set_cookies(kwargs.pop("cookies", None))
        super(TextResponse, self).__init__(*args, **kwargs)

    @staticmethod
    def _set_cookies(cookies_raw):
        cookies = {}
        if cookies_raw is None:
            return cookies
        cookies_str = str(cookies_raw)
        for cookie in re.findall(r'Set-Cookie: (.*?)=(.*?); Domain', cookies_str, re.S):
            cookies[cookie[0]] = cookie[1]
        return cookies

    def _set_url(self, url):
        if isinstance(url, str):
            self._url = to_unicode(url, self.encoding)
        else:
            super(TextResponse, self)._set_url(url)

    def _set_body(self, body):
        self._body = b''  # used by encoding detection
        if isinstance(body, str):
            if self._encoding is None:
                raise TypeError('Cannot convert unicode body - %s has no encoding' %
                                type(self).__name__)
            self._body = body.encode(self._encoding)
        else:
            super(TextResponse, self)._set_body(body)

    def replace(self, *args, **kwargs):
        kwargs.setdefault('encoding', self.encoding)
        return Response.replace(self, *args, **kwargs)

    @property
    def encoding(self):
        return self._declared_encoding() or self._body_inferred_encoding()

    def _declared_encoding(self):
        return self._encoding or self._headers_encoding() \
            or self._body_declared_encoding()

    def body_as_unicode(self):
        """Return body as unicode"""
        return self.text

    @property
    def text(self):
        """ Body as unicode """
        # access self.encoding before _cached_ubody to make sure
        # _body_inferred_encoding is called
        benc = self.encoding
        if self._cached_ubody is None:
            charset = 'charset=%s' % benc
            self._cached_ubody = html_to_unicode(charset, self.body)[1]
        return self._cached_ubody

    @property
    async def json(self):
        return await call_helper(self._response.json)

    @memoizemethod_noargs
    def _headers_encoding(self):
        content_type = self.headers.get(b'Content-Type', b'')
        return http_content_type_encoding(to_unicode(content_type))

    def _body_inferred_encoding(self):
        if self._cached_benc is None:
            content_type = to_unicode(self.headers.get(b'Content-Type', b''))
            benc, ubody = html_to_unicode(content_type, self.body,
                                          auto_detect_fun=self._auto_detect_fun,
                                          default_encoding=self._DEFAULT_ENCODING)
            self._cached_benc = benc
            self._cached_ubody = ubody
        return self._cached_benc

    def _auto_detect_fun(self, text):
        for enc in (self._DEFAULT_ENCODING, 'utf-8', 'cp1252'):
            try:
                text.decode(enc)
            except UnicodeError:
                continue
            return resolve_encoding(enc)

    @memoizemethod_noargs
    def _body_declared_encoding(self):
        return html_body_declared_encoding(self.body)

    @property
    def selector(self):
        if self._cached_selector is None:
            text = self.text
            self._cached_selector = Selector(text)
        return self._cached_selector

    def xpath(self, query, **kwargs):
        return self.selector.xpath(query, **kwargs)

    def css(self, query):
        return self.selector.css(query)

    def follow(self, url, callback=None, method='GET', headers=None, body=None,
               cookies=None, meta=None, encoding=None, priority=0,
               dont_filter=False, errback=None, cb_kwargs=None, flags=None, **kwargs):
        if isinstance(url, parsel.Selector):
            url = _url_from_selector(url)
        elif isinstance(url, parsel.SelectorList):
            raise ValueError("SelectorList is not supported")
        encoding = self.encoding if encoding is None else encoding
        return super(TextResponse, self).follow(
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

    def follow_all(self, urls=None, callback=None, method='GET', headers=None, body=None,
                   cookies=None, meta=None, encoding=None, priority=0,
                   dont_filter=False, errback=None, cb_kwargs=None, flags=None,
                   css=None, xpath=None):
        arguments = [x for x in (urls, css, xpath) if x is not None]
        if len(arguments) != 1:
            raise ValueError(
                "Please supply exactly one of the following arguments: urls, css, xpath"
            )
        if not urls:
            if css:
                urls = self.css(css)
            if xpath:
                urls = self.xpath(xpath)
        if isinstance(urls, parsel.SelectorList):
            selectors = urls
            urls = []
            for sel in selectors:
                with suppress(_InvalidSelector):
                    urls.append(_url_from_selector(sel))
        return super(TextResponse, self).follow_all(
            urls=urls,
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


class _InvalidSelector(ValueError):
    """
    Raised when a URL cannot be obtained from a Selector
    """


def _url_from_selector(sel):
    # type: (parsel.Selector) -> str
    if isinstance(sel.root, str):
        # e.g. ::attr(href) result
        return strip_html5_whitespace(sel.root)
    if not hasattr(sel.root, 'tag'):
        raise _InvalidSelector("Unsupported selector: %s" % sel)
    if sel.root.tag not in ('a', 'link'):
        raise _InvalidSelector("Only <a> and <link> elements are supported; got <%s>" %
                               sel.root.tag)
    href = sel.root.get('href')
    if href is None:
        raise _InvalidSelector("<%s> element has no href attribute: %s" %
                               (sel.root.tag, sel))
    return strip_html5_whitespace(href)
