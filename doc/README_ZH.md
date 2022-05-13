

![aioscpy](./images/aioscpy.png)

### Aioscpy

基于asyncio及aio全家桶, 使用scrapy框架流程及标准的一个异步爬虫框架

[英文](../README.md)| 中文

### 概述

Aioscpy框架基于开源项目Scrapy & scrapy_redis。

Aioscpy是一个快速的高级web爬行和web抓取框架，用于抓取网站并从其页面提取结构化数据。

实现了动态变量注入和异步协程功能。

分布式爬行和抓取。

### 需求

- Python 3.7+
- Works on Linux, Windows, macOS, BSD

### 安装

快速安装方式:

```shell
pip install aioscpy
```

### 用法

创建项目爬虫:

```shell
aioscpy startproject project_quotes
```

```
cd project_quotes
aioscpy genspider quotes 
```

![tree](./images/tree.png)

quotes.py:

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

创建单个爬虫脚本:

```shell
aioscpy onespider single_quotes
```

single_quotes.py:

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
    quotes = QuotesSpider()
    quotes.start()
```

运行爬虫:

```shell
aioscpy crawl quotes
aioscpy runspider quotes.py
```

![run](./images/run.png)

start.py:

```python
from aioscpy import call_grace_instance
from aioscpy.utils.tools import get_project_settings


def load_file_to_execute():
    process = call_grace_instance("crawler_process", get_project_settings())
    process.load_spider(path='./spiders')
    process.start()


def load_name_to_execute():
    process = call_grace_instance("crawler_process", get_project_settings())
    process.crawl('[spider_name]')
    process.start()
```

更多命令:

```shell
aioscpy -h
```

### 准备

请向我通过issue的方式提出您的建议

## 感谢

[aiohttp](https://github.com/aio-libs/aiohttp/)

[scrapy](https://github.com/scrapy/scrapy)

[loguru](https://github.com/Delgan/loguru)
