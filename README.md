

![aioscpy](./doc/images/aioscpy.png)

# Aioscpy

A powerful, high-performance asynchronous web crawling and scraping framework built on Python's asyncio ecosystem.

English | [中文](./doc/README_ZH.md)

## Overview

Aioscpy is a fast high-level web crawling and web scraping framework, used to crawl websites and extract structured data from their pages. It draws inspiration from Scrapy and scrapy_redis but is designed from the ground up to leverage the full power of asynchronous programming.

### Key Features

- **Fully Asynchronous**: Built on Python's asyncio for high-performance concurrent operations
- **Scrapy-like API**: Familiar API for those coming from Scrapy
- **Distributed Crawling**: Support for distributed crawling using Redis
- **Multiple HTTP Backends**: Support for aiohttp, httpx, and requests
- **Dynamic Variable Injection**: Powerful dependency injection system
- **Flexible Middleware System**: Customizable request/response processing pipeline
- **Robust Item Processing**: Pipeline for processing scraped items

## Requirements

- Python 3.8+
- Works on Linux, Windows, macOS, BSD

## Installation

### Basic Installation

```shell
pip install aioscpy
```

### With All Dependencies

```shell
pip install aioscpy[all]
```

### With Specific HTTP Backends

```shell
pip install aioscpy[aiohttp,httpx]
```

### Latest Version from GitHub

```shell
pip install git+https://github.com/ihandmine/aioscpy
```

## Quick Start

### Creating a New Project

```shell
aioscpy startproject myproject
cd myproject
```

### Creating a Spider

```shell
aioscpy genspider myspider
```

This will create a basic spider in the `spiders` directory.

![tree](./doc/images/tree.png)

### Example Spider

```python
from aioscpy.spider import Spider


class QuotesSpider(Spider):
    name = 'quotes'
    custom_settings = {
        "SPIDER_IDLE": False
    }
    start_urls = [
        'https://quotes.toscrape.com/tag/humor/',
    ]

    async def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)
```

### Creating a Single Spider Script

```shell
aioscpy onespider single_quotes
```

### Advanced Spider Example

```python
from aioscpy.spider import Spider
from anti_header import Header
from pprint import pprint, pformat


class SingleQuotesSpider(Spider):
    name = 'single_quotes'
    custom_settings = {
        "SPIDER_IDLE": False
    }
    start_urls = [
        'https://quotes.toscrape.com/',
    ]

    async def process_request(self, request):
        request.headers = Header(url=request.url, platform='windows', connection=True).random
        return request

    async def process_response(self, request, response):
        if response.status in [404, 503]:
            return request
        return response

    async def process_exception(self, request, exc):
        raise exc

    async def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)

    async def process_item(self, item):
        self.logger.info("{item}", **{'item': pformat(item)})


if __name__ == '__main__':
    quotes = SingleQuotesSpider()
    quotes.start()
```

### Running Spiders

```shell
# Run a spider from a project
aioscpy crawl quotes

# Run a single spider script
aioscpy runspider quotes.py
```

![run](./doc/images/run.png)

### Running from Python Code

```python
from aioscpy.crawler import call_grace_instance
from aioscpy.utils.tools import get_project_settings

# Method 1: Load all spiders from a directory
def load_spiders_from_directory():
    process = call_grace_instance("crawler_process", get_project_settings())
    process.load_spider(path='./spiders')
    process.start()

# Method 2: Run a specific spider by name
def run_specific_spider():
    process = call_grace_instance("crawler_process", get_project_settings())
    process.crawl('myspider')
    process.start()

if __name__ == '__main__':
    run_specific_spider()
```

## Configuration

Aioscpy can be configured through the `settings.py` file in your project. Here are the most important settings:

### Concurrency Settings

```python
# Maximum number of concurrent items being processed
CONCURRENT_ITEMS = 100

# Maximum number of concurrent requests
CONCURRENT_REQUESTS = 16

# Maximum number of concurrent requests per domain
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# Maximum number of concurrent requests per IP
CONCURRENT_REQUESTS_PER_IP = 0
```

### Download Settings

```python
# Delay between requests (in seconds)
DOWNLOAD_DELAY = 0

# Timeout for requests (in seconds)
DOWNLOAD_TIMEOUT = 20

# Whether to randomize the download delay
RANDOMIZE_DOWNLOAD_DELAY = True

# HTTP backend to use
DOWNLOAD_HANDLER = "aioscpy.core.downloader.handlers.httpx.HttpxDownloadHandler"
# Other options:
# DOWNLOAD_HANDLER = "aioscpy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler"
# DOWNLOAD_HANDLER = "aioscpy.core.downloader.handlers.requests.RequestsDownloadHandler"
```

### Scheduler Settings

```python
# Scheduler to use (memory-based or Redis-based)
SCHEDULER = "aioscpy.core.scheduler.memory.MemoryScheduler"
# For distributed crawling:
# SCHEDULER = "aioscpy.core.scheduler.redis.RedisScheduler"

# Redis connection settings (for Redis scheduler)
REDIS_URI = "redis://localhost:6379"
QUEUE_KEY = "%(spider)s:queue"
```

## Response API

Aioscpy provides a rich API for working with responses:

### Extracting Data

```python
# Using CSS selectors
title = response.css('title::text').get()
all_links = response.css('a::attr(href)').getall()

# Using XPath
title = response.xpath('//title/text()').get()
all_links = response.xpath('//a/@href').getall()
```

### Following Links

```python
# Follow a link
yield response.follow('next-page.html', self.parse)

# Follow a link with a callback
yield response.follow('details.html', self.parse_details)

# Follow all links matching a CSS selector
yield from response.follow_all(css='a.product::attr(href)', callback=self.parse_product)
```

## More Commands

```shell
aioscpy -h
```

## Distributed Crawling

To enable distributed crawling with Redis:

1. Configure Redis in settings:

```python
SCHEDULER = "aioscpy.core.scheduler.redis.RedisScheduler"
REDIS_URI = "redis://localhost:6379"
QUEUE_KEY = "%(spider)s:queue"
```

2. Run multiple instances of your spider on different machines, all connecting to the same Redis server.

## Contributing

Please submit your suggestions to the owner by creating an issue.

## Thanks

[aiohttp](https://github.com/aio-libs/aiohttp/)

[scrapy](https://github.com/scrapy/scrapy)

[loguru](https://github.com/Delgan/loguru)

[httpx](https://github.com/encode/httpx)
