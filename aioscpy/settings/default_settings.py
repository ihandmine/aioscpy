BOT_NAME = "aioscpy"

CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 0
RANDOMIZE_DOWNLOAD_DELAY = True

DOWNLOAD_DELAY = 0
DOWNLOAD_TIMEOUT = 20

# LOG CONFIG
LOG_LEVEL = "DEBUG"
LOG_FILE = False
LOG_FILENAME = f"{BOT_NAME}.log"
LOG_ENCODING = "utf-8"
LOG_ROTATION = "1 week"
LOG_RETENTION = "30 days"

DI_CONFIG = {
    "scheduler": "aioscpy.core.scheduler.memory.MemoryScheduler",
    "downloader": "aioscpy.core.downloader.Downloader",
    "item_processor": "aioscpy.middleware.ItemPipelineManager",
    "log_formatter": "aioscpy.logformatter.LogFormatter",
}
DI_CONFIG_CLS = {
    "request": "aioscpy.http.Request",
    "response": "aioscpy.http.TextResponse",
    "form_request": "aioscpy.http.FormRequest",
    "logger": "aioscpy.utils.log.logger",
    "log": "aioscpy.utils.log",
    "exceptions": "aioscpy.exceptions",
    "tools": "aioscpy.utils.tools",
}
DI_CREATE_CLS = {
    'crawler': 'aioscpy.crawler.Crawler',
    'crawler_process': 'aioscpy.crawler.CrawlerProcess',
    'engine': 'aioscpy.core.engine.ExecutionEngine',
    'spider': 'aioscpy.spider.Spider',
    'downloader_handler': 'aioscpy.core.downloader.http.AioHttpDownloadHandler',
    'downloader_middleware': 'aioscpy.middleware.DownloaderMiddlewareManager'
}

# message config
RABBITMQ_TCP = {
    "host": "172.16.8.147",
    # "port": 5672,
    # "username": "admin",
    # "password": "admin",
    # "key": "message:queue",
    # "max_priority": 100
}
QUEUE_KEY = '%(spider)s:requests'

REDIS_TCP = {
    "host": "172.16.8.147",
    "port": 6379,
    "password": "123456",
    "db": 15
}
