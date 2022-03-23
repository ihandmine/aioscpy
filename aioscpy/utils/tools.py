# _*_ coding: utf-8 _*_

import asyncio
from types import CoroutineType, GeneratorType, AsyncGeneratorType


async def call_helper(f, *args, **kwargs):
    if asyncio.iscoroutinefunction(f):
        return await f(*args, **kwargs)
    return f(*args, **kwargs)


async def async_generator_wrapper(wrapped):
    """将传入的对象变成AsyncGeneratorType类型"""
    if isinstance(wrapped, AsyncGeneratorType):
        return wrapped

    elif isinstance(wrapped, CoroutineType):
        async def anonymous(c):
            yield await c
        return anonymous(wrapped)

    elif isinstance(wrapped, GeneratorType):
        async def anonymous(c):
            for r in c:
                yield r
        return anonymous(wrapped)

    else:
        async def anonymous(c):
            yield c
        return anonymous(wrapped)


def get_project_settings():
    import os
    import pickle
    import warnings

    from scrapy.utils.conf import init_env
    from aioscrapy.settings import AioSettings
    from scrapy.exceptions import ScrapyDeprecationWarning

    ENVVAR = 'SCRAPY_SETTINGS_MODULE'

    if ENVVAR not in os.environ:
        project = os.environ.get('SCRAPY_PROJECT', 'default')
        init_env(project)
    settings = AioSettings()
    settings_module_path = os.environ.get(ENVVAR)
    if settings_module_path:
        settings.setmodule(settings_module_path, priority='project')

    pickled_settings = os.environ.get("SCRAPY_PICKLED_SETTINGS_TO_OVERRIDE")
    if pickled_settings:
        warnings.warn("Use of environment variable "
                      "'SCRAPY_PICKLED_SETTINGS_TO_OVERRIDE' "
                      "is deprecated.", ScrapyDeprecationWarning)
        settings.setdict(pickle.loads(pickled_settings), priority='project')

    scrapy_envvars = {k[7:]: v for k, v in os.environ.items() if
                      k.startswith('SCRAPY_')}
    valid_envvars = {
        'CHECK',
        'PICKLED_SETTINGS_TO_OVERRIDE',
        'PROJECT',
        'PYTHON_SHELL',
        'SETTINGS_MODULE',
    }
    setting_envvars = {k for k in scrapy_envvars if k not in valid_envvars}
    if setting_envvars:
        setting_envvar_list = ', '.join(sorted(setting_envvars))
        warnings.warn(
            'Use of environment variables prefixed with SCRAPY_ to override '
            'settings is deprecated. The following environment variables are '
            f'currently defined: {setting_envvar_list}',
            ScrapyDeprecationWarning
        )
    settings.setdict(scrapy_envvars, priority='project')

    return settings


def singleton(cls):
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton


def exec_js_func(js_file_path, func_name, func_params=None, cwd_path=None, cmd_path='node'):
    """
    调用node执行js文件
    :param js_file_path: js文件路径
    :param func_name: 要调用的js文件内的函数名称
    :param func_params: func的参数
    :param cwd_path: node_modules文件所在路径，如果不指定将使用全局的node_modules
    :param cmd_path: node的位置， 例如：r'D:\\path\to\node.exe'
    :return: func_name函数的执行结果
    """
    import execjs

    if func_params is None:
        func_params = []
    name = "MyNode"
    execjs.register(name, execjs._external_runtime.ExternalRuntime(
        name="Node.js (V8)",
        command=[cmd_path],
        encoding='UTF-8',
        runner_source=execjs._runner_sources.Node
    ))
    with open(js_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    js = ''.join(lines)
    js_context = execjs.get(name).compile(js, cwd=cwd_path)
    return js_context.call(func_name, *func_params)
