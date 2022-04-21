BOT_NAME = "default_bot"

CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 0
RANDOMIZE_DOWNLOAD_DELAY = True

DOWNLOAD_DELAY = 0
DOWNLOAD_TIMEOUT = 20

# LOG CONFIG
LOG_LEVEL = "DEBUG"
LOG_FILE = True
LOG_FILENAME = f"{BOT_NAME}.log"
LOG_ENCODING = "utf-8"
LOG_ROTATION = "1 week"
LOG_RETENTION = "30 days"

DI_CONFIG = {
    "scheduler_priority_queue": "aioscpy.queue.memory.memory_queue",
    "scheduler": "aioscpy.core.scheduler.memory.MemoryScheduler",
    "downloader": "aioscpy.core.downloader.Downloader",
    "item_processor": "aioscpy.middleware.ItemPipelineManager",
    "log_formatter": "aioscpy.logformatter.LogFormatter",
}
DI_CONFIG_CLS = {
    "request": "aioscpy.http.Request",
    "response": "aioscpy.http.TextResponse",
    "form_request": "aioscpy.http.FormRequest"
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

REDIS_TCP = {
    "host": "172.16.8.147",
    "port": 6379,
    "password": "123456",
    "db": 15
}
