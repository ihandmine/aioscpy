from aioscpy.crawler import call_grace_instance

"""start spider method one:
from cegex.baidu import BaiduSpider
from cegex.httpbin import HttpBinSpider

process = CrawlerProcess()
process.crawl(HttpBinSpider)
process.crawl(BaiduSpider)
process.start()
"""


process = call_grace_instance("crawler_process")
process.load_spider('./cegex')
process.start()

