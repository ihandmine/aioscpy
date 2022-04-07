

SCHEDULER = "aioscpy.core.scheduler.memory.MemoryScheduler"
SCHEDULER_PRIORITY_QUEUE = "aioscpy.queue.memory.memory_queue"
DOWNLOADER = 'aioscpy.core.downloader.Downloader'
DOWNLOAD_HANDLERS_BASE = {
    'http': 'aioscpy.core.downloader.http.AioHttpDownloadHandler',
    'https': 'aioscpy.core.downloader.http.AioHttpDownloadHandler',
}
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
