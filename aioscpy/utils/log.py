from __future__ import absolute_import, unicode_literals

import sys
import socket
import warnings
import aioscpy

from loguru import logger

from aioscpy.exceptions import ScrapyDeprecationWarning
from aioscpy.settings import Settings


def set_log_config(formatter: str, settings):
    _log_config = {
        "default": {
            "handlers": [
                {
                    "sink": sys.stdout,
                    "format": formatter,
                    "level": settings.get('LOG_LEVEL', "TRACE")
                }
            ],
            "extra": {
                "host": socket.gethostbyname(socket.gethostname()),
                'log_name': settings.get("BOT_NAME", 'default'),
                'type': 'None'
            },
            "levels": [
                dict(name="TRACE", icon="✏️", color="<cyan><bold>"),
                dict(name="DEBUG", icon="❄️", color="<blue><bold>"),
                dict(name="INFO", icon="♻️", color="<bold>"),
                dict(name="SUCCESS", icon="✔️", color="<green><bold>"),
                dict(name="WARNING", icon="⚠️", color="<yellow><bold>"),
                dict(name="ERROR", icon="❌️", color="<red><bold>"),
                dict(name="CRITICAL", icon="☠️", color="<RED><bold>"),
            ]
        }
    }
    if settings.get('LOG_FILE', False):
        _log_config['default']['handlers'].append({
            "sink": settings.get('LOG_FILENAME', __file__),
            "format": formatter,
            "level": settings.get('LOG_LEVEL', "DEBUG"),
            "rotation": settings.get("LOG_ROTATION", '1 week'),
            "retention": settings.get("LOG_RETENTION", '30 days'),
            'encoding': settings.get("LOG_ENCODING", "utf-8")
        })
    return _log_config


class LogFormatter(object):
    simple_formatter = '<green>{time:YYYY-MM-DD HH:mm:ss}</green> ' \
                       '[<cyan>{name}</cyan>] ' \
                       '<level>{level.icon}{level}</level>: ' \
                       '<level>{message}</level> '

    default_formatter = '<green>{time:YYYY-MM-DD HH:mm:ss,SSS}</green> | ' \
                        '[<cyan>{extra[log_name]}</cyan>] <cyan>{module}</cyan>:<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | ' \
                        '<red>{extra[host]}</red> | ' \
                        '<level>{level.icon}{level: <5}</level> | ' \
                        '<level>{level.no}</level> | ' \
                        '<level>{extra[type]}</level> | ' \
                        '<level>{message}</level> '

    kafka_formatter = '{time:YYYY-MM-DD HH:mm:ss,SSS}| ' \
                      '[{extra[log_name]}] {module}:{name}:{function}:{line} | ' \
                      '{extra[host]} | ' \
                      '{process} | ' \
                      '{thread} | ' \
                      '{level: <5} | ' \
                      '{level.no} | ' \
                      '{extra[type]}| ' \
                      '{message} '

    @classmethod
    def setter_log_handler(cls, log, callback=None):
        assert callable(callback), 'callback must be a callable object'
        log.add(callback, format=cls.kafka_formatter)

    @classmethod
    def get_logger(cls, log, name=None):
        settings = Settings()
        log_config = set_log_config(cls.simple_formatter, settings)
        config = log_config.pop('default', {})
        if name:
            config['extra']['log_name'] = name
        log.configure(**config)
        return log

    @staticmethod
    def format(spider, meta):
        if hasattr(spider, 'logging_keys'):
            logging_txt = []
            for key in spider.logging_keys:
                if meta.get(key, None) is not None:
                    logging_txt.append(u'{0}:{1} '.format(key, meta[key]))
            logging_txt.append('successfully')
            return ' '.join(logging_txt)


def logformatter_adapter(logkws):
    if not {'level', 'msg', 'args'} <= set(logkws):
        warnings.warn('Missing keys in LogFormatter method',
                      ScrapyDeprecationWarning)

    if 'format' in logkws:
        warnings.warn('`format` key in LogFormatter methods has been '
                      'deprecated, use `msg` instead',
                      ScrapyDeprecationWarning)

    level = logkws.get('level', 'INFO')
    message = logkws.get('format', logkws.get('msg'))
    args = logkws if not logkws.get('args') else logkws['args']

    return level, message, args


def std_log_aioscpy_info(settings):
    logger.info("aioscpy {version} started (bot: {bot})",
                **{'version': aioscpy.__version__, 'bot': settings['BOT_NAME']})


lof = LogFormatter

logger = lof.get_logger(logger)


