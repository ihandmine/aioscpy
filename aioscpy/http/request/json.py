from aioscpy.http.request import Request


class JsonRequest(Request):
    valid_form_methods = ['POST']

    def __init__(self, *args, **kwargs):
        jsondata = kwargs.pop('jsondata', None)
        if jsondata and kwargs.get('method') is None:
            kwargs['method'] = 'POST'

        super(JsonRequest, self).__init__(*args, **kwargs)

        if jsondata:
            if self.method == 'POST':
                self.headers.setdefault(
                    b'Content-Type', [b'application/json'])
                self._set_json(jsondata)
