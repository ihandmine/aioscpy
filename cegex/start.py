from aioscpy.crawler import CrawlerProcess
# from aioscpy.utils.project import get_project_settings


from baidu import BaiduSpider
from httpbin import HttpBinSpider


process = CrawlerProcess()

process.crawl(HttpBinSpider)
process.crawl(BaiduSpider)

process.start()

