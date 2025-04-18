BOT_NAME = "aioscpy"

# Concurrency settings
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 0
CONCURRENT_ITEMS = 16

# Adaptive concurrency settings
ADAPTIVE_CONCURRENCY_ENABLED = False
ADAPTIVE_CONCURRENCY_TARGET_RESPONSE_TIME = 1.0  # seconds
ADAPTIVE_CONCURRENCY_MIN_REQUESTS = 8
ADAPTIVE_CONCURRENCY_MAX_REQUESTS = 32
ADAPTIVE_CONCURRENCY_WINDOW_SIZE = 20
ADAPTIVE_CONCURRENCY_ADJUSTMENT_INTERVAL = 10  # seconds

# Download settings
DOWNLOAD_DELAY = 0
DOWNLOAD_TIMEOUT = 20
RANDOMIZE_DOWNLOAD_DELAY = True

# Memory optimization settings
GC_ENABLED = True
GC_FREQUENCY = 10  # Run garbage collection every 10 heartbeats

# Task beat settings
TASK_BEAT_ACTIVE_SLEEP = 0.2  # Sleep when active (seconds)
TASK_BEAT_IDLE_SLEEP = 1.0    # Sleep when idle (seconds)
TASK_BEAT_BATCH_SIZE = 100    # Max requests per batch

# Handler and scheduler settings
# DOWNLOAD_HANDLER = "aioscpy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler"
DOWNLOAD_HANDLER = "aioscpy.core.downloader.handlers.httpx.HttpxDownloadHandler"
# DOWNLOAD_HANDLER = "aioscpy.core.downloader.handlers.requests.RequestsDownloadHandler"
# SCHEDULER = "aioscpy.core.scheduler.redis.RedisScheduler"
SCHEDULER = "aioscpy.core.scheduler.memory.MemoryScheduler"
REQUESTS_SESSION_STATS = False

SPIDER_IDLE = False

# LOG CONFIG
LOG_LEVEL = "DEBUG"
LOG_FILE = False
LOG_FILENAME = f"{BOT_NAME}.log"
LOG_ENCODING = "utf-8"
LOG_ROTATION = "1 week"
LOG_RETENTION = "30 days"

DI_CONFIG = {
    "scheduler": f"{SCHEDULER}",
    "log_formatter": "aioscpy.logformatter.LogFormatter",
    "extension": "aioscpy.middleware.ExtensionManager",

}
DI_CONFIG_CLS = {
    "request": "aioscpy.http.Request",
    "response": "aioscpy.http.TextResponse",
    "form_request": "aioscpy.http.FormRequest",
    "json_request": "aioscpy.http.JsonRequest",
    "logger": "aioscpy.utils.log.logger",
    "log": "aioscpy.utils.log",
    "exceptions": "aioscpy.exceptions",
    "tools": "aioscpy.utils.tools",
    'downloader_middleware': 'aioscpy.middleware.DownloaderMiddlewareManager',
    "item_processor": "aioscpy.middleware.ItemPipelineManager",
}
DI_CREATE_CLS = {
    'crawler': 'aioscpy.crawler.Crawler',
    'crawler_process': 'aioscpy.crawler.CrawlerProcess',
    'engine': 'aioscpy.core.engine.ExecutionEngine',
    'spider': 'aioscpy.spider.Spider',
    'downloader_handler': f'{DOWNLOAD_HANDLER}',
    'stats': 'aioscpy.libs.statscollectors.MemoryStatsCollector',
    'scraper': 'aioscpy.core.scraper.Scraper',
    "downloader": "aioscpy.core.downloader.Downloader",
}

# message config
# RABBITMQ_TCP = {
#     "host": "172.16.8.147",
#     # "port": 5672,
#     # "username": "admin",
#     # "password": "admin",
#     # "key": "message:queue",
#     # "max_priority": 100
# }
QUEUE_KEY = '%(spider)s:requests'

# REDIS_TCP = {
#     "host": "172.16.7.172",
#     "port": 6379,
#     "password": "123456",
#     "db": 15
# }
# REDIS_URI = "redis://:123456@172.16.7.172:6379/1"


EXTENSIONS_BASE = {
    'aioscpy.libs.extensions.corestats.CoreStats': 0,
    'aioscpy.libs.extensions.logstats.LogStats': 0,

}

DOWNLOADER_MIDDLEWARES_BASE = {
    # Engine side
    'aioscpy.middleware.adaptive_concurrency.AdaptiveConcurrencyMiddleware': 500,
    'aioscpy.libs.downloadermiddlewares.stats.DownloaderStats': 850,
    # Downloader side
}
DOWNLOADER_STATS = True

LOGSTATS_INTERVAL = 60.0
STATS_CLASS = 'aioscpy.libs.statscollectors.MemoryStatsCollector'
STATS_DUMP = True
SCRAPER_SLOT_MAX_ACTIVE_SIZE = 5000000

TLS_CIPHERS = False

