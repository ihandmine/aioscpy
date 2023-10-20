from aioscpy.http.request import Request


class FormRequest(Request):
    valid_form_methods = ['POST']

    def __init__(self, *args, **kwargs):
        formdata = kwargs.pop('formdata', None)
        if formdata and kwargs.get('method') is None:
            kwargs['method'] = 'POST'

        super(FormRequest, self).__init__(*args, **kwargs)

        if formdata:
            if self.method == 'POST':
                self.headers.setdefault(
                    b'Content-Type', [b'application/x-www-form-urlencoded'])
                self._set_body(formdata)
