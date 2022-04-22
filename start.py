from aioscpy.crawler import CrawlerProcess

"""start spider method one:
from cegex.baidu import BaiduSpider
from cegex.httpbin import HttpBinSpider

process = CrawlerProcess()
process.crawl(HttpBinSpider)
process.crawl(BaiduSpider)
process.start()
"""


process = CrawlerProcess()
process.load_spider('./cegex')
process.start()

