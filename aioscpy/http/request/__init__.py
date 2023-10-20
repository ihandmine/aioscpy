from w3lib.url import safe_url_string


class Request(object):

    def __init__(self, url,
                 callback=None,
                 method='GET',
                 headers=None,
                 body=None,
                 json=None,
                 cookies=None,
                 meta=None,
                 encoding='utf-8',
                 priority=0,
                 dont_filter=False,
                 errback=None, flags=None, cb_kwargs=None):
        self._encoding = encoding
        self.method = str(method).upper()
        self._set_url(url)
        self._set_body(body)
        self._set_json(json)

        assert isinstance(priority, int), "Request priority not an integer: %r" % priority
        self.priority = priority

        if callback is not None and not callable(callback):
            raise TypeError('callback must be a callable, got %s' %
                            type(callback).__name__)
        if errback is not None and not callable(errback):
            raise TypeError('errback must be a callable, got %s' %
                            type(errback).__name__)
        self.callback = callback
        self.errback = errback

        self.cookies = cookies or {}
        self.headers = headers or {}
        self.dont_filter = dont_filter

        self._meta = dict(meta) if meta else None
        self._cb_kwargs = dict(cb_kwargs) if cb_kwargs else None
        self.flags = [] if flags is None else list(flags)

    @property
    def cb_kwargs(self):
        if self._cb_kwargs is None:
            self._cb_kwargs = {}
        return self._cb_kwargs

    @property
    def meta(self):
        if self._meta is None:
            self._meta = {}
        return self._meta

    def get(self, key, default):
        return self.meta.get(key, default)

    def _get_url(self):
        return self._url

    def _set_url(self, url):
        if not isinstance(url, str):
            raise TypeError(
                'Request url must be str or unicode, got %s:' % type(url).__name__)

        s = safe_url_string(url, self.encoding)
        self._url = s

        if ('://' not in self._url) and (not self._url.startswith('data:')):
            raise ValueError('Missing scheme in request url: %s' % self._url)

    url = property(_get_url, _set_url)

    def _get_body(self):
        return self._body

    def _set_body(self, body):
        self._body = body or None

    body = property(_get_body, _set_body)

    def _get_json(self):
        return self._json
    
    def _set_json(self, json):
        self._json = json or None

    json = property(_get_json, _set_json)

    @property
    def encoding(self):
        return self._encoding

    def __str__(self):
        return "<%s %s>" % (self.method, self.url)

    __repr__ = __str__

    def copy(self):
        """Return a copy of this Request"""
        return self.replace()

    def replace(self, *args, **kwargs):
        """Create a new Request with the same attributes except for those
        given new values.
        """
        for x in ['url', 'method', 'headers', 'body', 'cookies', 'meta', 'flags',
                  'encoding', 'priority', 'dont_filter', 'callback', 'errback', 'cb_kwargs']:
            kwargs.setdefault(x, getattr(self, x))
        cls = kwargs.pop('cls', self.__class__)
        return cls(*args, **kwargs)
