BOT_NAME = "default_bot"

CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 0
RANDOMIZE_DOWNLOAD_DELAY = True

SCHEDULER = "aioscpy.core.scheduler.memory.MemoryScheduler"
SCHEDULER_PRIORITY_QUEUE = "aioscpy.queue.memory.memory_queue"
DOWNLOADER = 'aioscpy.core.downloader.Downloader'
ITEM_PROCESSOR = 'aioscpy.middleware.ItemPipelineManager'
DOWNLOAD_DELAY = 0
DOWNLOAD_TIMEOUT = 30

# LOG
LOG_ENABLED = True
# LOG_ENCODING = 'utf-8'
LOG_FORMATTER = 'aioscpy.logformatter.LogFormatter'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
# LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
# LOG_STDOUT = False
LOG_LEVEL = 'DEBUG'
LOG_FILE = True
LOG_FILENAME = "info.log"
# LOG_FILE_APPEND = True
# LOG_SHORT_NAMES = False

# message config
RABBITMQ_TCP = {
    'host': '172.16.8.147',
    # 'port': 5672,
    # 'username': 'admin',
    # 'password': 'admin',
    # 'key': 'message:queue',
    # 'max_priority': 100
}

REDIS_TCP = {
    'host': '172.16.8.147',
    'port': 6379,
    'password': '123456',
    'db': 15
}
