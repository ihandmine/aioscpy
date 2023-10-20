from aioscpy.crawler import call_grace_instance
from aioscpy.utils.tools import get_project_settings

"""start spider method one:
from cegex.baidu import BaiduSpider
from cegex.httpbin import HttpBinSpider

process = CrawlerProcess()
process.crawl(HttpBinSpider)
process.crawl(BaiduSpider)
process.start()
"""


def load_file_to_execute():
    process = call_grace_instance("crawler_process", get_project_settings())
    process.load_spider(path='./cegex', spider_like='httpbin')
    process.start()


def load_name_to_execute():
    process = call_grace_instance("crawler_process", get_project_settings())
    process.crawl('baidu', path="./cegex")
    process.start()


if __name__ == '__main__':
    load_name_to_execute()
