from urllib.parse import urljoin, urlencode

from aioscpy.http.request import Request
from aioscpy.utils.tools import to_bytes, is_listlike


class JsonRequest(Request):
    valid_form_methods = ['GET', 'POST']

    def __init__(self, *args, **kwargs):
        formdata = kwargs.pop('formdata', None)
        if formdata and kwargs.get('method') is None:
            kwargs['method'] = 'POST'

        super(JsonRequest, self).__init__(*args, **kwargs)

        if formdata:
            if self.method == 'POST':
                self.headers.setdefault(
                    b'Content-Type', [b'application/json'])
                self._set_body(formdata)

